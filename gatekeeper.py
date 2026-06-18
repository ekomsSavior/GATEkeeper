#!/usr/bin/env python3
"""
GATEkeeper - Browser interaction + network recon for authorized testing.

Features:
- Interactive prompts or CLI arguments
- Cookie loading
- Custom headers
- Wait selector support
- Request/response/failure/console capture
- Optional response body dumping
- Technology fingerprinting
- Security header analysis
- JSON report generation
"""

import argparse
import asyncio
import hashlib
import json
import random
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


MAX_POST_CHARS = 5000
MAX_BODY_BYTES = 10 * 1024 * 1024


INTERESTING_TERMS = [
    "auth", "login", "logout", "oauth", "saml", "sso", "callback",
    "token", "jwt", "session", "csrf", "xsrf", "api", "graphql",
    "admin", "dashboard", "internal", "gateway", "redirect",
    "collect", "track", "analytics", "chronos", "dune", "ct"
]


TECH_SIGNATURES = {
    "Cloudflare": ["cf-ray", "cf-cache-status", "__cf_bm", "cloudflare"],
    "Akamai": ["akamai", "akamaighost", "ak_bmsc"],
    "Fastly": ["fastly", "x-served-by", "x-cache-hits"],
    "Nginx": ["nginx"],
    "Apache": ["apache"],
    "IIS": ["microsoft-iis", "asp.net"],
    "React": ["react", "__react", "react-dom"],
    "Next.js": ["next.js", "_next/static", "x-nextjs"],
    "Vue": ["vue", "__vue"],
    "Angular": ["angular", "ng-version"],
    "jQuery": ["jquery"],
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "Drupal": ["drupal"],
    "Google Tag Manager": ["googletagmanager.com", "gtm.js"],
    "Google Analytics": ["google-analytics.com", "gtag/js", "analytics.google.com"],
    "Microsoft Clarity": ["clarity.ms"],
}


SECURITY_HEADERS = [
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
    "cross-origin-opener-policy",
    "cross-origin-resource-policy",
    "cross-origin-embedder-policy",
]


class GatekeeperBanger:
    def __init__(
        self,
        target_url: str,
        output_dir: Path,
        headless: bool = False,
        timeout: int = 60000,
        interaction_duration: int = 45,
        cookies_file: Path | None = None,
        custom_headers: dict | None = None,
        user_agent: str | None = None,
        wait_selector: str | None = None,
        save_bodies: bool = False,
        report: bool = False,
    ):
        self.target_url = target_url
        self.output_dir = output_dir
        self.headless = headless
        self.timeout = timeout
        self.interaction_duration = interaction_duration
        self.cookies_file = cookies_file
        self.custom_headers = custom_headers or {}
        self.user_agent = user_agent
        self.wait_selector = wait_selector
        self.save_bodies = save_bodies
        self.report = report

        self.captured_requests = []
        self.captured_responses = []
        self.failed_requests = []
        self.console_logs = []
        self.url_changes = []
        self.saved_bodies = []

        self.final_html = None
        self.final_url = None
        self.main_response_headers = {}

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.bodies_dir = self.output_dir / "response_bodies"
        if self.save_bodies:
            self.bodies_dir.mkdir(parents=True, exist_ok=True)

        self.capture_file = self.output_dir / "network_capture.json"
        self.report_file = self.output_dir / "report.json"
        self.html_file = self.output_dir / "final_page.html"
        self.screenshot_file = self.output_dir / "final_screenshot.png"
        self.console_log_file = self.output_dir / "console_log.txt"

    async def run(self):
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--ignore-certificate-errors",
                ],
            )

            default_headers = {
                "Accept-Language": "en-US,en;q=0.9",
                "DNT": "1",
            }
            default_headers.update(self.custom_headers)

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                user_agent=self.user_agent or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Safari/537.36"
                ),
                extra_http_headers=default_headers,
                java_script_enabled=True,
                ignore_https_errors=True,
            )

            await self.load_cookies(context)

            await context.add_init_script(
                """
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
                window.chrome = { runtime: {} };
                """
            )

            page = await context.new_page()

            page.on("request", self._on_request)
            page.on("response", self._on_response)
            page.on("requestfailed", self._on_request_failed)
            page.on("console", self._on_console)

            print(f"[*] Navigating to {self.target_url}")

            try:
                main_response = await page.goto(
                    self.target_url,
                    wait_until="domcontentloaded",
                    timeout=self.timeout,
                )
                if main_response:
                    self.main_response_headers = dict(main_response.headers)
            except PlaywrightTimeoutError:
                print("[!] Initial DOM load timeout, continuing anyway...")
            except Exception as e:
                print(f"[!] Initial navigation error, continuing anyway: {type(e).__name__}: {e}")

            if self.wait_selector:
                print(f"[*] Waiting for selector: {self.wait_selector}")
                try:
                    await page.wait_for_selector(self.wait_selector, timeout=self.timeout)
                    print("[+] Selector appeared.")
                except PlaywrightTimeoutError:
                    print("[!] Selector wait timed out, continuing anyway.")
                except Exception as e:
                    print(f"[!] Selector wait failed: {type(e).__name__}: {e}")

            await self.safe_wait(page, 2000)

            print(f"[*] Starting interaction simulation for {self.interaction_duration} seconds...")
            await self.simulate_interactions(page)

            self.final_url = page.url

            try:
                self.final_html = await page.content()
            except Exception as e:
                print(f"[!] Could not capture final HTML: {type(e).__name__}: {e}")

            try:
                await page.screenshot(path=str(self.screenshot_file), full_page=True)
            except Exception as e:
                print(f"[!] Screenshot failed: {type(e).__name__}: {e}")

            await browser.close()

            self._save_results()
            self._print_summary()

    async def load_cookies(self, context):
        if not self.cookies_file:
            return

        try:
            with open(self.cookies_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            if not isinstance(cookies, list):
                print("[!] Cookie file must be a JSON array of cookie objects.")
                return

            await context.add_cookies(cookies)
            print(f"[+] Loaded {len(cookies)} cookies from {self.cookies_file}")

        except Exception as e:
            print(f"[!] Failed to load cookies: {type(e).__name__}: {e}")

    async def simulate_interactions(self, page):
        try:
            for _ in range(30):
                x = random.randint(100, 1600)
                y = random.randint(100, 900)
                await page.mouse.move(x, y, steps=random.randint(3, 8))
                await self.safe_wait(page, random.randint(150, 450))

            await self.safe_click(page, "body", 300, 300)
            await self.safe_wait(page, 1000)

            for scroll in range(0, 1600, 100):
                await self.safe_eval(page, f"window.scrollTo(0, {scroll})")
                await self.safe_wait(page, 120)

            for scroll in range(1600, 0, -100):
                await self.safe_eval(page, f"window.scrollTo(0, {scroll})")
                await self.safe_wait(page, 120)

            for key in ["ArrowDown", "ArrowDown", "ArrowUp", "Tab", "Enter", "Escape"]:
                try:
                    await page.keyboard.press(key)
                except Exception:
                    pass
                await self.safe_wait(page, 200)

            try:
                await page.set_viewport_size({"width": 1280, "height": 800})
                await self.safe_wait(page, 500)
                await page.set_viewport_size({"width": 1920, "height": 1080})
            except Exception:
                pass

            start_time = datetime.now()
            last_url = page.url
            no_change_count = 0

            while (datetime.now() - start_time).seconds < self.interaction_duration:
                await self.safe_wait(page, 2000)

                current_url = page.url
                if current_url != last_url:
                    print(f"[*] URL changed: {last_url} -> {current_url}")
                    self.url_changes.append(
                        {
                            "from": last_url,
                            "to": current_url,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    last_url = current_url
                    no_change_count = 0
                else:
                    no_change_count += 1

                if no_change_count > 4:
                    await self.safe_click(page, "body", 500, 500)
                    await self.safe_eval(page, "window.dispatchEvent(new Event('mousemove'))")
                    no_change_count = 0

        except Exception as e:
            print(f"[!] Interaction loop error, continuing to save results: {type(e).__name__}: {e}")

    async def safe_wait(self, page, ms: int):
        try:
            await page.wait_for_timeout(ms)
        except Exception:
            pass

    async def safe_click(self, page, selector: str, x: int, y: int):
        try:
            await page.click(selector, position={"x": x, "y": y}, force=True, timeout=5000)
        except Exception as e:
            print(f"[!] Click failed: {type(e).__name__}: {e}")

    async def safe_eval(self, page, script: str):
        try:
            await page.evaluate(script)
        except Exception:
            pass

    def safe_post_data(self, request):
        if request.method != "POST":
            return None

        try:
            data = request.post_data
            if data is None:
                return None

            if len(data) > MAX_POST_CHARS:
                return data[:MAX_POST_CHARS] + f"... [truncated {len(data) - MAX_POST_CHARS} chars]"

            return data

        except UnicodeDecodeError as e:
            return f"[binary/compressed POST body unreadable as UTF-8: {e}]"

        except Exception as e:
            return f"[POST body unavailable: {type(e).__name__}: {e}]"

    def _on_request(self, request):
        try:
            req_data = {
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "headers": dict(request.headers),
                "post_data": self.safe_post_data(request),
                "timestamp": datetime.now().isoformat(),
            }

            self.captured_requests.append(req_data)
            print(f"  [req] {request.method} {request.url[:140]}")

        except Exception as e:
            print(f"[!] Request capture error ignored: {type(e).__name__}: {e}")

    def _on_response(self, response):
        try:
            resp_data = {
                "url": response.url,
                "status": response.status,
                "headers": dict(response.headers),
                "timestamp": datetime.now().isoformat(),
            }

            self.captured_responses.append(resp_data)
            print(f"  [res] {response.status} {response.url[:140]}")

            if self.save_bodies:
                asyncio.create_task(self.save_response_body(response))

        except Exception as e:
            print(f"[!] Response capture error ignored: {type(e).__name__}: {e}")

    async def save_response_body(self, response):
        try:
            content_type = response.headers.get("content-type", "").lower()
            body = await response.body()

            if not body:
                return

            if len(body) > MAX_BODY_BYTES:
                return

            parsed = urlparse(response.url)
            path = parsed.path or "/"
            suffix = self.guess_extension(content_type, path)

            raw_name = f"{response.status}_{response.request.method}_{response.url}"
            digest = hashlib.sha256(raw_name.encode("utf-8", errors="ignore")).hexdigest()[:16]
            filename = f"resp_{digest}{suffix}"
            file_path = self.bodies_dir / filename

            with open(file_path, "wb") as f:
                f.write(body)

            self.saved_bodies.append(
                {
                    "url": response.url,
                    "status": response.status,
                    "content_type": content_type,
                    "size": len(body),
                    "file": str(file_path),
                    "timestamp": datetime.now().isoformat(),
                }
            )

        except Exception:
            pass

    def guess_extension(self, content_type: str, path: str) -> str:
        path_lower = path.lower()

        for ext in [".js", ".css", ".json", ".html", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".xml", ".txt"]:
            if path_lower.endswith(ext):
                return ext

        if "javascript" in content_type:
            return ".js"
        if "css" in content_type:
            return ".css"
        if "json" in content_type:
            return ".json"
        if "html" in content_type:
            return ".html"
        if "png" in content_type:
            return ".png"
        if "jpeg" in content_type or "jpg" in content_type:
            return ".jpg"
        if "svg" in content_type:
            return ".svg"
        if "xml" in content_type:
            return ".xml"
        if "text" in content_type:
            return ".txt"

        return ".bin"

    def _on_request_failed(self, request):
        try:
            failure = request.failure or {}
            fail_data = {
                "url": request.url,
                "method": request.method,
                "resource_type": request.resource_type,
                "failure": failure,
                "timestamp": datetime.now().isoformat(),
            }

            self.failed_requests.append(fail_data)
            print(f"  [fail] {request.method} {request.url[:120]} {failure}")

        except Exception as e:
            print(f"[!] Failed-request capture error ignored: {type(e).__name__}: {e}")

    def _on_console(self, msg):
        try:
            log_entry = f"[{msg.type}] {msg.text}"
            self.console_logs.append(log_entry)
            print(f"  [console] {log_entry[:180]}")
        except Exception:
            pass

    def detect_technologies(self):
        haystack_parts = []

        if self.final_html:
            haystack_parts.append(self.final_html)

        for req in self.captured_requests:
            haystack_parts.append(req.get("url", ""))
            haystack_parts.append(json.dumps(req.get("headers", {}), default=str))

        for resp in self.captured_responses:
            haystack_parts.append(resp.get("url", ""))
            haystack_parts.append(json.dumps(resp.get("headers", {}), default=str))

        haystack = "\n".join(haystack_parts).lower()
        detected = []

        for tech, signatures in TECH_SIGNATURES.items():
            if any(sig.lower() in haystack for sig in signatures):
                detected.append(tech)

        return sorted(set(detected))

    def analyze_security_headers(self):
        headers = {k.lower(): v for k, v in self.main_response_headers.items()}
        result = {}

        for header in SECURITY_HEADERS:
            result[header] = {
                "present": header in headers,
                "value": headers.get(header),
            }

        return result

    def find_interesting_endpoints(self):
        matches = []

        for req in self.captured_requests:
            url = req.get("url", "")
            url_lower = url.lower()

            hit_terms = [term for term in INTERESTING_TERMS if term in url_lower]

            if hit_terms:
                matches.append(
                    {
                        "method": req.get("method"),
                        "url": url,
                        "resource_type": req.get("resource_type"),
                        "terms": sorted(set(hit_terms)),
                    }
                )

        return matches

    def build_report(self):
        status_counter = Counter(r["status"] for r in self.captured_responses)
        resource_counter = Counter(r["resource_type"] for r in self.captured_requests)

        endpoints = defaultdict(int)
        for req in self.captured_requests:
            endpoints[(req["method"], req["url"])] += 1

        top_endpoints = [
            {"method": method, "url": url, "count": count}
            for (method, url), count in sorted(endpoints.items(), key=lambda x: x[1], reverse=True)[:50]
        ]

        redirects = [
            {
                "status": r["status"],
                "url": r["url"],
                "location": r["headers"].get("location", "N/A"),
            }
            for r in self.captured_responses
            if r["status"] in (301, 302, 303, 307, 308)
        ]

        return {
            "generated_at": datetime.now().isoformat(),
            "target": self.target_url,
            "final_url": self.final_url,
            "summary": {
                "total_requests": len(self.captured_requests),
                "total_responses": len(self.captured_responses),
                "failed_requests": len(self.failed_requests),
                "console_messages": len(self.console_logs),
                "url_changes": len(self.url_changes),
                "redirects_detected": len(redirects),
                "response_bodies_saved": len(self.saved_bodies),
            },
            "status_codes": dict(status_counter),
            "resource_types": dict(resource_counter),
            "technologies": self.detect_technologies(),
            "security_headers": self.analyze_security_headers(),
            "redirects": redirects,
            "interesting_endpoints": self.find_interesting_endpoints(),
            "top_endpoints": top_endpoints,
            "url_changes": self.url_changes,
            "saved_bodies": self.saved_bodies,
        }

    def _save_results(self):
        capture = {
            "timestamp": datetime.now().isoformat(),
            "target": self.target_url,
            "final_url": self.final_url,
            "url_changes": self.url_changes,
            "requests": self.captured_requests,
            "responses": self.captured_responses,
            "failed_requests": self.failed_requests,
            "console_logs": self.console_logs,
            "saved_bodies": self.saved_bodies,
        }

        with open(self.capture_file, "w", encoding="utf-8") as f:
            json.dump(capture, f, indent=2, ensure_ascii=False)

        print(f"[*] Network capture saved to {self.capture_file}")

        if self.final_html:
            with open(self.html_file, "w", encoding="utf-8") as f:
                f.write(self.final_html)
            print(f"[*] Final HTML saved to {self.html_file}")

        if self.console_logs:
            with open(self.console_log_file, "w", encoding="utf-8") as f:
                f.write("\n".join(self.console_logs))
            print(f"[*] Console log saved to {self.console_log_file}")

        if self.report:
            report_data = self.build_report()
            with open(self.report_file, "w", encoding="utf-8") as f:
                json.dump(report_data, f, indent=2, ensure_ascii=False)
            print(f"[*] Report saved to {self.report_file}")

        print(f"[*] Screenshot path: {self.screenshot_file}")

    def _print_summary(self):
        print("\n" + "=" * 60)
        print("GATEKEEPER SUMMARY")
        print("=" * 60)

        print(f"Initial URL: {self.target_url}")
        print(f"Final URL:   {self.final_url}")
        print(f"Requests:    {len(self.captured_requests)}")
        print(f"Responses:   {len(self.captured_responses)}")
        print(f"Failures:    {len(self.failed_requests)}")
        print(f"Console:     {len(self.console_logs)}")
        print(f"URL changes: {len(self.url_changes)}")
        print(f"Bodies saved:{len(self.saved_bodies)}")

        redirects = [r for r in self.captured_responses if r["status"] in (301, 302, 303, 307, 308)]

        if redirects:
            print(f"\n[!] Redirect responses detected: {len(redirects)}")
            for r in redirects[:20]:
                location = r["headers"].get("location", "N/A")
                print(f"  {r['status']} {r['url'][:100]} -> {location}")
        else:
            print("\n[+] No HTTP redirect responses captured.")

        interesting = self.find_interesting_endpoints()
        if interesting:
            print(f"\n[+] Interesting endpoints detected: {len(interesting)}")
            for item in interesting[:20]:
                print(f"  {item['method']} {item['url'][:120]} [{', '.join(item['terms'])}]")
        else:
            print("\n[-] No configured interesting endpoint terms captured.")

        technologies = self.detect_technologies()
        if technologies:
            print("\n[+] Detected technologies:")
            for tech in technologies:
                print(f"  - {tech}")

        security = self.analyze_security_headers()
        missing = [h for h, v in security.items() if not v["present"]]

        if missing:
            print("\n[!] Missing common security headers:")
            for header in missing:
                print(f"  - {header}")

        if self.final_html:
            html_lower = self.final_html.lower()
            loading_words = ["spinner", "loading", "getting things ready"]

            if any(word in html_lower for word in loading_words):
                print("\n[!] Final page may still contain loading indicators.")
            else:
                print("\n[+] Final HTML captured and does not obviously look stuck on a spinner.")
        else:
            print("\n[-] No final HTML captured.")


def sanitize_domain_name(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    domain = parsed.netloc or parsed.path.split("/")[0]
    domain = re.sub(r"[^a-zA-Z0-9.-]", "_", domain)
    return domain or "gatekeeper_output"


def parse_header(header_values):
    headers = {}

    for item in header_values or []:
        if ":" not in item:
            print(f"[!] Ignoring malformed header: {item}")
            continue

        name, value = item.split(":", 1)
        name = name.strip()
        value = value.strip()

        if name:
            headers[name] = value

    return headers


def build_parser():
    parser = argparse.ArgumentParser(
        description="GATEkeeper - Browser interaction and network recon for authorized testing."
    )

    parser.add_argument("url", nargs="?", help="Target URL")
    parser.add_argument("-o", "--output", help="Output directory")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--duration", type=int, default=None, help="Interaction duration in seconds")
    parser.add_argument("--timeout", type=int, default=60000, help="Navigation timeout in milliseconds")
    parser.add_argument("--cookies", type=Path, help="Load Playwright cookies from JSON file")
    parser.add_argument("--header", action="append", help='Custom header, example: --header "Authorization: Bearer TOKEN"')
    parser.add_argument("--user-agent", help="Override User-Agent")
    parser.add_argument("--wait-selector", help="Wait for CSS selector before interactions")
    parser.add_argument("--save-bodies", action="store_true", help="Save response bodies to disk")
    parser.add_argument("--report", action="store_true", help="Generate report.json")
    parser.add_argument("--non-interactive", action="store_true", help="Do not prompt for missing values")

    return parser


async def main():
    parser = build_parser()
    args = parser.parse_args()

    print("=" * 60)
    print("GATEkeeper - Interactive Browser Automation")
    print("Authorized testing only. Captures browser network activity.")
    print("=" * 60)

    target_url = args.url

    if not target_url and not args.non_interactive:
        target_url = input("\nEnter target URL (e.g., https://example.com): ").strip()

    if not target_url:
        print("[!] No URL provided. Exiting.")
        sys.exit(1)

    if not target_url.startswith(("http://", "https://")):
        target_url = "http://" + target_url

    domain_name = sanitize_domain_name(target_url)
    default_output = f"./{domain_name}_bang"

    output_dir = Path(args.output) if args.output else None

    if output_dir is None and not args.non_interactive:
        output_dir_input = input(f"Output directory (default: {default_output}): ").strip()
        output_dir = Path(output_dir_input) if output_dir_input else Path(default_output)

    if output_dir is None:
        output_dir = Path(default_output)

    headless = args.headless

    if not args.headless and not args.non_interactive:
        headless_input = input("Run in headless mode? (y/N): ").strip().lower()
        headless = headless_input == "y"

    interaction_duration = args.duration

    if interaction_duration is None and not args.non_interactive:
        duration_input = input("Interaction duration in seconds (default: 45): ").strip()

        try:
            interaction_duration = int(duration_input) if duration_input else 45
        except ValueError:
            interaction_duration = 45
            print("[!] Invalid number, using 45 seconds.")

    if interaction_duration is None:
        interaction_duration = 45

    custom_headers = parse_header(args.header)

    print("\n[*] Starting browser...")

    banger = GatekeeperBanger(
        target_url=target_url,
        output_dir=output_dir,
        headless=headless,
        timeout=args.timeout,
        interaction_duration=interaction_duration,
        cookies_file=args.cookies,
        custom_headers=custom_headers,
        user_agent=args.user_agent,
        wait_selector=args.wait_selector,
        save_bodies=args.save_bodies,
        report=args.report,
    )

    await banger.run()

    print(f"\n[+] Script finished. Results saved in: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
