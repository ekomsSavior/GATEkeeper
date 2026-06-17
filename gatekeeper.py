#!/usr/bin/env python3
"""
Gatekeeper - Interactive browser automation for authorized testing.

- Simulates user interaction
- Captures requests, responses, redirects, console logs, request failures
- Saves final HTML and screenshot
- Handles binary/compressed POST bodies safely
"""

import asyncio
import base64
import json
import random
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


MAX_POST_CHARS = 5000


class GatekeeperBanger:
    def __init__(
        self,
        target_url: str,
        output_dir: Path,
        headless: bool = False,
        timeout: int = 60000,
        interaction_duration: int = 45,
    ):
        self.target_url = target_url
        self.output_dir = output_dir
        self.headless = headless
        self.timeout = timeout
        self.interaction_duration = interaction_duration

        self.captured_requests = []
        self.captured_responses = []
        self.failed_requests = []
        self.console_logs = []
        self.url_changes = []

        self.final_html = None
        self.final_url = None

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.capture_file = self.output_dir / "network_capture.json"
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
                    "--disable-web-security",
                    "--ignore-certificate-errors",
                ],
            )

            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/134.0.0.0 Safari/537.36"
                ),
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "DNT": "1",
                },
                java_script_enabled=True,
                ignore_https_errors=True,
            )

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
                await page.goto(self.target_url, wait_until="domcontentloaded", timeout=self.timeout)
            except PlaywrightTimeoutError:
                print("[!] Initial DOM load timeout, continuing anyway...")
            except Exception as e:
                print(f"[!] Initial navigation error, continuing anyway: {type(e).__name__}: {e}")

            await self.safe_wait(page, 2000)

            print(f"[*] Starting user interaction simulation for {self.interaction_duration} seconds...")

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

    async def simulate_interactions(self, page):
        try:
            for _ in range(30):
                x = random.randint(100, 1600)
                y = random.randint(100, 900)
                await page.mouse.move(x, y, steps=random.randint(3, 8))
                await self.safe_wait(page, random.randint(150, 450))

            await self.safe_click(page, "body", 300, 300)
            await self.safe_wait(page, 1000)

            for scroll in range(0, 1200, 100):
                await self.safe_eval(page, f"window.scrollTo(0, {scroll})")
                await self.safe_wait(page, 120)

            for scroll in range(1200, 0, -100):
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

        except Exception as e:
            print(f"[!] Response capture error ignored: {type(e).__name__}: {e}")

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

        redirects = [r for r in self.captured_responses if r["status"] in (301, 302, 303, 307, 308)]

        if redirects:
            print(f"\n[!] Redirect responses detected: {len(redirects)}")
            for r in redirects:
                location = r["headers"].get("location", "N/A")
                print(f"  {r['status']} {r['url'][:100]} -> {location}")
        else:
            print("\n[+] No HTTP redirect responses captured.")

        interesting_terms = [
            "/chronos",
            "/ct",
            "/dune",
            "redirect",
            "login",
            "auth",
            "token",
            "session",
            "sso",
            "oauth",
            "saml",
            "callback",
            "collect",
            "track",
            "analytics",
        ]

        found = {}

        for req in self.captured_requests:
            url_lower = req["url"].lower()
            for term in interesting_terms:
                if term.lower() in url_lower:
                    found.setdefault(term, 0)
                    found[term] += 1

        if found:
            print("\n[+] Interesting URL terms captured:")
            for term, count in sorted(found.items()):
                print(f"  {term}: {count}")
        else:
            print("\n[-] No configured interesting URL terms captured.")

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


async def main():
    print("=" * 60)
    print("Gatekeeper - Interactive Browser Automation")
    print("Authorized testing only. Captures browser network activity.")
    print("=" * 60)

    target_url = input("\nEnter target URL (e.g., https://example.com): ").strip()

    if not target_url:
        print("[!] No URL provided. Exiting.")
        sys.exit(1)

    if not target_url.startswith(("http://", "https://")):
        target_url = "http://" + target_url

    domain_name = sanitize_domain_name(target_url)
    default_output = f"./{domain_name}_bang"

    output_dir_input = input(f"Output directory (default: {default_output}): ").strip()
    output_dir = Path(output_dir_input) if output_dir_input else Path(default_output)

    headless_input = input("Run in headless mode? (y/N): ").strip().lower()
    headless = headless_input == "y"

    duration_input = input("Interaction duration in seconds (default: 45): ").strip()

    try:
        interaction_duration = int(duration_input) if duration_input else 45
    except ValueError:
        interaction_duration = 45
        print("[!] Invalid number, using 45 seconds.")

    print("\n[*] Starting browser...")

    banger = GatekeeperBanger(
        target_url=target_url,
        output_dir=output_dir,
        headless=headless,
        timeout=60000,
        interaction_duration=interaction_duration,
    )

    await banger.run()

    print(f"\n[+] Script finished. Results saved in: {output_dir}")


if __name__ == "__main__":
    asyncio.run(main())
