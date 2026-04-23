#!/usr/bin/env python3
"""
Gatekeeper-Simulates extensive user interaction to try to force a hidden redirect,
captures all network traffic, and saves final HTML.
"""

import asyncio
import json
import sys
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError


class GatekeeperBanger:
    def __init__(self, target_url: str, output_dir: Path, headless: bool = False, timeout: int = 60000, interaction_duration: int = 30):
        self.target_url = target_url
        self.output_dir = output_dir
        self.headless = headless
        self.timeout = timeout          # overall page timeout (ms)
        self.interaction_duration = interaction_duration  # seconds to simulate interactions
        self.captured_requests = []
        self.captured_responses = []
        self.console_logs = []
        self.final_html = None
        self.final_url = None

        # Create output directory and define file paths
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.capture_file = self.output_dir / "network_capture.json"
        self.html_file = self.output_dir / "final_page.html"
        self.screenshot_file = self.output_dir / "final_screenshot.png"
        self.console_log_file = self.output_dir / "console_log.txt"

    async def run(self):
        async with async_playwright() as p:
            # Launch browser with realistic options
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ]
            )
            # Create context with realistic viewport and locale
            context = await browser.new_context(
                viewport={"width": 1920, "height": 1080},
                locale="en-US",
                timezone_id="America/New_York",
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
                extra_http_headers={
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Upgrade-Insecure-Requests": "1",
                }
            )
            # Add stealth script to hide automation
            await context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
                Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
                Object.defineProperty(navigator, 'languages', { get: () => ['en-US','en'] });
                window.chrome = { runtime: {} };
            """)
            
            page = await context.new_page()
            
            # Set up event listeners
            page.on("request", self._on_request)
            page.on("response", self._on_response)
            page.on("console", self._on_console)
            
            print(f"[*] Navigating to {self.target_url}")
            try:
                await page.goto(self.target_url, wait_until="networkidle", timeout=self.timeout)
            except PlaywrightTimeoutError:
                print("[!] Initial load timeout, but continuing...")
            
            # Wait a bit for page to settle
            await page.wait_for_timeout(2000)
            
            print(f"[*] Starting user interaction simulation for {self.interaction_duration} seconds...")
            
            # 1. Random mouse movements
            for i in range(30):
                x = 100 + (hash(str(i)) % 1500)
                y = 100 + (hash(str(i+100)) % 800)
                await page.mouse.move(x, y, steps=5)
                await page.wait_for_timeout(200 + (hash(str(i)) % 300))
            
            # 2. Click on the center of the page (where spinner likely is)
            await page.click("body", position={"x": 300, "y": 300}, force=True)
            await page.wait_for_timeout(1000)
            
            # 3. Simulate scrolling
            for scroll in range(0, 500, 50):
                await page.evaluate(f"window.scrollTo(0, {scroll})")
                await page.wait_for_timeout(100)
            for scroll in range(500, 0, -50):
                await page.evaluate(f"window.scrollTo(0, {scroll})")
                await page.wait_for_timeout(100)
            
            # 4. Press keys
            await page.keyboard.press("ArrowDown")
            await page.wait_for_timeout(200)
            await page.keyboard.press("ArrowUp")
            await page.wait_for_timeout(200)
            await page.keyboard.press("Enter")
            
            # 5. Resize window
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.wait_for_timeout(500)
            await page.set_viewport_size({"width": 1920, "height": 1080})
            
            # 6. Wait and watch for any navigation
            start_time = datetime.now()
            last_url = page.url
            no_change_count = 0
            
            while (datetime.now() - start_time).seconds < self.interaction_duration:
                await page.wait_for_timeout(2000)
                current_url = page.url
                if current_url != last_url:
                    print(f"[*] URL changed: {last_url} -> {current_url}")
                    last_url = current_url
                    no_change_count = 0
                else:
                    no_change_count += 1
                    if no_change_count > 5:
                        # Trigger a click on the body again just in case
                        await page.click("body", position={"x": 500, "y": 500}, force=True)
                        no_change_count = 0
            
            # Capture final state
            self.final_url = page.url
            self.final_html = await page.content()
            
            # Take screenshot
            await page.screenshot(path=str(self.screenshot_file), full_page=True)
            
            await browser.close()
            
            self._save_results()
            self._print_summary()
    
    def _on_request(self, request):
        req_data = {
            "url": request.url,
            "method": request.method,
            "headers": dict(request.headers),
            "post_data": request.post_data if request.method == "POST" else None,
            "timestamp": datetime.now().isoformat()
        }
        self.captured_requests.append(req_data)
        print(f"  [req] {request.method} {request.url[:100]}")
    
    def _on_response(self, response):
        resp_data = {
            "url": response.url,
            "status": response.status,
            "headers": dict(response.headers),
            "timestamp": datetime.now().isoformat()
        }
        self.captured_responses.append(resp_data)
        print(f"  [res] {response.status} {response.url[:100]}")
    
    def _on_console(self, msg):
        log_entry = f"[{msg.type}] {msg.text}"
        self.console_logs.append(log_entry)
        print(f"  [console] {log_entry}")
    
    def _save_results(self):
        # Save network capture
        capture = {
            "timestamp": datetime.now().isoformat(),
            "target": self.target_url,
            "final_url": self.final_url,
            "requests": self.captured_requests,
            "responses": self.captured_responses,
            "console_logs": self.console_logs
        }
        with open(self.capture_file, "w") as f:
            json.dump(capture, f, indent=2)
        print(f"[*] Network capture saved to {self.capture_file}")
        
        # Save HTML
        if self.final_html:
            with open(self.html_file, "w", encoding="utf-8") as f:
                f.write(self.final_html)
            print(f"[*] Final HTML saved to {self.html_file}")
        
        # Save console log separately
        if self.console_logs:
            with open(self.console_log_file, "w") as f:
                f.write("\n".join(self.console_logs))
            print(f"[*] Console log saved to {self.console_log_file}")
        
        print(f"[*] Screenshot saved to {self.screenshot_file}")
    
    def _print_summary(self):
        print("\n" + "="*60)
        print("GATEKEEPER BANGER SUMMARY")
        print("="*60)
        print(f"Initial URL: {self.target_url}")
        print(f"Final URL: {self.final_url}")
        print(f"Total requests captured: {len(self.captured_requests)}")
        print(f"Total responses captured: {len(self.captured_responses)}")
        print(f"Console messages: {len(self.console_logs)}")
        
        # Look for redirects
        redirects = [r for r in self.captured_responses if r["status"] in (301, 302, 307, 308)]
        if redirects:
            print(f"\n[!] Redirects detected: {len(redirects)}")
            for r in redirects:
                location = r["headers"].get("location", "N/A")
                print(f"  {r['status']} -> {location}")
        else:
            print("\n[+] No redirects were captured.")
        
        # Look for specific API endpoints (like /chronos)
        target_paths = ["/chronos", "/ct", "/dune"]
        found = []
        for req in self.captured_requests:
            for path in target_paths:
                if path in req["url"]:
                    found.append(path)
        if found:
            print(f"\n[+] Captured requests containing: {', '.join(set(found))}")
        else:
            print("\n[-] No specific API endpoints (like /chronos) were captured.")
        
        # Check if final page still contains typical loading indicators
        if self.final_html and ("spinner" in self.final_html.lower() or "loading" in self.final_html.lower() or "We're getting things ready" in self.final_html):
            print("\n[!] Final page still contains loading spinner – no real content loaded.")
        elif self.final_html:
            print("\n[+] Final page appears to have changed (no spinner detected).")
        else:
            print("\n[-] No final HTML captured.")


def sanitize_domain_name(url: str) -> str:
    """Extract domain from URL and return a safe directory name."""
    parsed = urlparse(url if '://' in url else f'http://{url}')
    domain = parsed.netloc or parsed.path.split('/')[0]
    # Remove any non-alphanumeric characters except dot and dash
    domain = re.sub(r'[^a-zA-Z0-9.-]', '_', domain)
    return domain


async def main():
    print("="*60)
    print("Gatekeeper Banger - Interactive Browser Automation")
    print("Simulates user interaction to force hidden redirects and captures network traffic.")
    print("="*60)
    
    # Get target URL
    target_url = input("\nEnter target URL (e.g., http://example.com): ").strip()
    if not target_url:
        print("[!] No URL provided. Exiting.")
        sys.exit(1)
    if not target_url.startswith(('http://', 'https://')):
        target_url = 'http://' + target_url
    
    # Determine output directory
    domain_name = sanitize_domain_name(target_url)
    default_output = f"./{domain_name}_bang"
    output_dir_input = input(f"Output directory (default: {default_output}): ").strip()
    if output_dir_input:
        output_dir = Path(output_dir_input)
    else:
        output_dir = Path(default_output)
    
    # Headless mode?
    headless_input = input("Run in headless mode? (y/N): ").strip().lower()
    headless = headless_input == 'y'
    
    # Interaction duration (seconds)
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
        interaction_duration=interaction_duration
    )
    await banger.run()
    
    print("\n[+] Script finished. Results saved in:", output_dir)


if __name__ == "__main__":
    asyncio.run(main())
