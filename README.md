<div align="center">
GATEkeeper by: ek0mssavior.dev
</div>

<div align="center">

**Advanced Browser Automation for Gatekeeper Bypass & Network Recon**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Options](#options) • [Output](#output) • [Disclaimer](#disclaimer)

</div>

---

## Overview

GATEkeeper is a reconnaissance tool that launches a Chromium browser, simulates human like interaction (mouse movements, scrolling, key presses), and captures all network traffic to force hidden redirects or reveal behind‑the‑scenes content.

The tool stores every request/response, saves response bodies, generates a structured JSON report, and can even create HAR traces. It works out of the box on most modern web applications, including those protected by anti‑bot mechanisms.

---

## Features

- Fully interactive or headless browser automation
- Bypasses Cloudflare challenges and other JavaScript‑based gatekeepers
- Simulates realistic user behaviour (random mouse moves, smooth scrolling, key presses, window resizing)
- Captures all network requests and responses (XHR, fetch, documents, images, etc.)
- Optional saving of every response body (CSS, JS, JSON, images) for offline analysis
- Generates a detailed JSON report with detected technologies, security headers, endpoints, and console errors
- Loads custom cookies and headers for authenticated testing
- Supports HAR trace export (HTTP Archive format)
- Playwright Stealth integration for enhanced anti‑detection
- Waits for specific DOM elements before starting the interaction phase
- Fully configurable via command‑line arguments or interactive prompts

---

## Installation

### Requirements

- Python 3.8+
- [Playwright](https://playwright.dev/python/)

### Steps

```bash
# Clone the repository
git clone https://github.com/ekomsSavior/GATEkeeper.git
cd GATEkeeper

# Install required Python package
pip install playwright --break-system-packages

# Install Chromium browser (required)
playwright install chromium

# (Optional) Install playwright-stealth for better anti‑detection
pip install playwright-stealth --break-system-packages
```

No additional setup is required.

---

## Usage

You can run GATEkeeper in two modes: **interactive** (prompts for input) or **command‑line** (all arguments provided).

### Interactive Mode

```bash
python3 gatekeeper.py
```

You will be asked for the target URL, output directory, headless mode, and interaction duration.

### Command‑Line Mode

```bash
python3 gatekeeper.py https://target.com --headless --duration 60 --save-bodies --report --stealth
```

### Examples

#### Basic scan with default settings
```bash
python3 gatekeeper.py https://example.com
```

#### Headless scan with report and response body saving
```bash
python3 gatekeeper.py https://example.com --headless --save-bodies --report
```

#### Authenticated scan (load cookies and custom headers)
```bash
python3 gatekeeper.py https://example.com/dashboard --cookies session.json --header "Authorization: Bearer eyJhbGci..."
```

#### Wait for login success before interacting
```bash
python3 gatekeeper.py https://example.com --wait-selector "#welcome-message"
```

---

## Options

| Argument | Description |
|----------|-------------|
| `url` | Target URL (optional, will prompt if omitted) |
| `--headless` | Run browser in headless mode (no GUI) |
| `--duration N` | Interaction duration in seconds (default: 45) |
| `--save-bodies` | Save all response bodies to disk |
| `--report` | Generate a structured JSON report |
| `--cookies FILE` | Load cookies from a JSON file (format: list of cookie objects) |
| `--user-agent STRING` | Override the default User‑Agent |
| `--header "Name: Value"` | Add custom HTTP header (can be used multiple times) |
| `--wait-selector CSS` | Wait for a DOM element to appear before starting interactions |
| `--har` | Save a HAR (HTTP Archive) trace file |
| `--stealth` | Use playwright‑stealth (if installed) for better anti‑detection |

---

## Output

All results are stored in a directory named after the target domain (e.g., `target.com_bang/`). The directory contains:

| File | Description |
|------|-------------|
| `network_capture.json` | Full log of all requests and responses |
| `final_page.html` | The final DOM after all interactions |
| `final_screenshot.png` | Full‑page screenshot of the final state |
| `console_log.txt` | JavaScript console messages (errors, warnings, logs) |
| `report.json` | (if `--report` used) Structured summary with endpoints, technologies, security headers |
| `trace.har` | (if `--har` used) HTTP Archive file for import into analysis tools |
| `resp_*.*` | (if `--save-bodies` used) Individual response bodies (CSS, JS, JSON, images, etc.) |

### Sample Report Snippet

```json
{
  "target": "https://example.com",
  "summary": {
    "total_requests": 134,
    "redirects_detected": 2,
    "technologies": ["Cloudflare", "Nginx", "React"]
  },
  "endpoints": [
    {"method": "GET", "url": "https://example.com/api/users", "count": 3},
    {"method": "POST", "url": "https://example.com/api/login", "count": 1}
  ],
  "security_headers": {
    "Strict-Transport-Security": true,
    "Content-Security-Policy": false
  }
}
```

---

## Cookie File Format

The cookie file must be a JSON array of cookie objects as accepted by Playwright. Example:

```json
[
  {
    "name": "sessionid",
    "value": "abc123",
    "domain": "example.com",
    "path": "/",
    "httpOnly": true,
    "secure": true,
    "sameSite": "Lax"
  }
]
```

You can export cookies from your browser using extensions like "EditThisCookie" or by running a script with Playwright itself.

---

## How It Works

1. Launches a Chromium browser with realistic viewport and user‑agent.
2. Injects stealth scripts to hide automation fingerprints.
3. Navigates to the target URL and waits for the initial page to load.
4. Optionally waits for a user‑specified CSS selector.
5. Simulates 45 seconds (configurable) of human‑like activity:
   - Random mouse movements across the viewport.
   - Click on the page body.
   - Smooth scrolling up and down.
   - Arrow key presses.
   - Window resizing.
   - Periodic re‑clicking if no URL change occurs.
6. Captures every network request/response and console message.
7. After the interaction period, saves the final page, screenshot, and all captured data.
8. (Optional) Writes a structured report and HAR trace.

The goal is to trigger any gatekeeper logic that only redirects or loads real content after genuine user behaviour.

---

## Limitations

- Does not bypass sophisticated bot detection that relies on WebGL fingerprinting, audio context, or behavioural analysis beyond mouse/keyboard simulation.
- Some gatekeepers may require longer interaction periods or specific sequences of actions (e.g., solving a CAPTCHA). This tool does not include CAPTCHA solving.
- Use of `--stealth` requires installation of `playwright-stealth` and may still be detected by advanced anti‑bot systems.

---

## Disclaimer

This tool is intended for **authorized security testing and research only**. The user is solely responsible for compliance with all applicable laws and regulations. Unauthorised use against websites without explicit permission is illegal. The author assumes no liability for misuse.

---

<div align="center">

**Happy Hacking – Break the Gatekeepers**

</div>
