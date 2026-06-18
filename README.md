# GATEkeeper

<div align="center">

**GATEkeeper by ek0mssavior.dev**

**Advanced Browser Automation for Gatekeeper Testing & Network Recon**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Options](#options) • [Output](#output) • [Disclaimer](#disclaimer)

</div>

---

## Overview

GATEkeeper is a Playwright-powered reconnaissance tool for authorized web application testing.

It launches a Chromium browser, simulates human-like interaction, captures browser network activity, tracks redirects and URL changes, logs console messages, saves the final rendered page, and optionally dumps response bodies for offline analysis.

GATEkeeper is useful for testing applications where content, redirects, API calls, or client-side behavior only appear after JavaScript execution, user interaction, authentication, or delayed page activity.

---

## Features

* Interactive prompt mode or command-line mode
* Headless or visible Chromium browser automation
* Simulated human-like interaction:

  * Mouse movement
  * Page clicks
  * Scrolling
  * Keyboard events
  * Viewport resizing
* Captures network requests and responses
* Captures failed requests
* Captures JavaScript console messages
* Tracks URL changes and redirect responses
* Handles binary/compressed POST bodies safely
* Loads cookies for authenticated testing
* Supports custom HTTP headers
* Supports custom User-Agent strings
* Waits for a specific CSS selector before interaction
* Optional response body dumping
* Basic technology fingerprinting
* Basic security header analysis
* Structured `report.json` generation

---

## Installation

### Requirements

* Python 3.10+
* Playwright

### Clone the Repository

```bash
git clone https://github.com/ekomsSavior/GATEkeeper.git
cd GATEkeeper
```

### Install Playwright

```bash
pip install playwright --break-system-packages
```

### Install Chromium

```bash
python3 -m playwright install chromium
```

If Playwright reports missing browser dependencies, run:

```bash
python3 -m playwright install-deps chromium
python3 -m playwright install chromium
```

---

## Usage

GATEkeeper supports both interactive mode and command-line mode.

### Interactive Mode

```bash
python3 gatekeeper.py
```

You will be prompted for:

* Target URL
* Output directory
* Headless mode
* Interaction duration

---

## Command-Line Mode

### Basic Scan

```bash
python3 gatekeeper.py https://example.com
```

### Headless Scan

```bash
python3 gatekeeper.py https://example.com --headless
```

### Longer Interaction Window

```bash
python3 gatekeeper.py https://example.com --duration 90
```

### Save Response Bodies and Generate Report

```bash
python3 gatekeeper.py https://example.com --headless --duration 60 --save-bodies --report
```

### Authenticated Testing with Cookies

```bash
python3 gatekeeper.py https://example.com/dashboard --cookies cookies.json --report
```

### Add Custom Headers

```bash
python3 gatekeeper.py https://example.com/dashboard \
  --header "Authorization: Bearer TOKEN_HERE" \
  --header "X-Test-Mode: authorized"
```

### Custom User-Agent

```bash
python3 gatekeeper.py https://example.com --user-agent "Mozilla/5.0 CustomTestAgent"
```

### Wait for a DOM Element Before Interacting

```bash
python3 gatekeeper.py https://example.com/dashboard --wait-selector "#dashboard"
```

### Non-Interactive Mode

```bash
python3 gatekeeper.py https://example.com --non-interactive --headless --report
```

---

## Options

| Argument                 | Description                                                 |
| ------------------------ | ----------------------------------------------------------- |
| `url`                    | Target URL. Optional if using interactive mode.             |
| `-o`, `--output DIR`     | Output directory. Defaults to `<domain>_bang/`.             |
| `--headless`             | Run Chromium without a visible browser window.              |
| `--duration N`           | Interaction duration in seconds. Default: `45`.             |
| `--timeout N`            | Navigation timeout in milliseconds. Default: `60000`.       |
| `--cookies FILE`         | Load cookies from a Playwright-compatible JSON cookie file. |
| `--header "Name: Value"` | Add a custom HTTP header. Can be used multiple times.       |
| `--user-agent STRING`    | Override the default User-Agent.                            |
| `--wait-selector CSS`    | Wait for a CSS selector before starting interaction.        |
| `--save-bodies`          | Save response bodies to disk.                               |
| `--report`               | Generate `report.json`.                                     |
| `--non-interactive`      | Do not prompt for missing values.                           |

---

## Output

By default, results are saved in a directory named after the target domain.

Example:

```text
example.com_bang/
```

Generated files:

| File / Directory       | Description                                                          |
| ---------------------- | -------------------------------------------------------------------- |
| `network_capture.json` | Full request, response, failure, URL change, and console log capture |
| `final_page.html`      | Final rendered DOM after interaction                                 |
| `final_screenshot.png` | Full-page screenshot                                                 |
| `console_log.txt`      | JavaScript console messages                                          |
| `report.json`          | Structured report generated with `--report`                          |
| `response_bodies/`     | Saved response bodies generated with `--save-bodies`                 |

---

## Report Contents

When `--report` is used, GATEkeeper generates `report.json` with:

* Target URL
* Final URL
* Total requests
* Total responses
* Failed request count
* Console message count
* URL changes
* Redirects
* Status code summary
* Resource type summary
* Interesting endpoint matches
* Basic detected technologies
* Common security header analysis
* Saved response body metadata

Example:

```json
{
  "target": "https://example.com",
  "final_url": "https://example.com/dashboard",
  "summary": {
    "total_requests": 134,
    "total_responses": 129,
    "failed_requests": 5,
    "redirects_detected": 2,
    "response_bodies_saved": 48
  },
  "technologies": [
    "Cloudflare",
    "React",
    "Google Analytics"
  ],
  "security_headers": {
    "strict-transport-security": {
      "present": true,
      "value": "max-age=31536000"
    },
    "content-security-policy": {
      "present": false,
      "value": null
    }
  }
}
```

---

## Cookie File Format

The cookie file must be a JSON array of cookie objects accepted by Playwright.

Example:

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

---

## How It Works

1. Launches a Chromium browser with a realistic viewport and User-Agent.
2. Optionally loads cookies and custom headers.
3. Navigates to the target URL.
4. Optionally waits for a CSS selector.
5. Simulates browser interaction:

   * Mouse movement
   * Clicks
   * Scrolling
   * Keyboard input
   * Viewport resizing
6. Captures requests, responses, failed requests, redirects, URL changes, and console logs.
7. Saves final HTML and screenshot.
8. Optionally saves response bodies.
9. Optionally generates a structured report.

---

## Limitations

GATEkeeper does not include:

* CAPTCHA solving
* HAR export
* Full browser fingerprint spoofing
* WebGL spoofing
* Audio fingerprint spoofing
* Automated login
* Credential attack functionality
* Guaranteed Cloudflare or anti-bot bypass

Some applications may require longer interaction windows, authenticated cookies, specific workflows, or manual browser interaction.

---

## Disclaimer

This tool is intended for authorized security testing, research, education, and defensive assessment only.


---

<div align="center">

**Happy Hacking — Authorized Testing Only**

</div>
