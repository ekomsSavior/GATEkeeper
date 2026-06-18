# GATEkeeper

<div align="center">

**GATEkeeper by ek0mssavior.dev**

**Advanced Browser Automation for Gatekeeper Testing & Network Recon**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Bulk Scanning](#bulk-scanning) • [Options](#options) • [Output](#output) • [Disclaimer](#disclaimer)

</div>

---

## Overview

GATEkeeper is a Playwright-powered reconnaissance tool for authorized web application testing.

It launches a Chromium browser, simulates human-like interaction, captures browser network activity, tracks redirects and URL changes, logs console messages, saves the final rendered page, and optionally dumps response bodies for offline analysis.

GATEkeeper also performs lightweight preflight reconnaissance before browser interaction, including DNS resolution, target IP collection, common web port checks, service hints, TLS certificate metadata, and triage scoring.

It is useful for testing applications where content, redirects, API calls, authentication workflows, or client-side behavior only appear after JavaScript execution, user interaction, authentication, or delayed page activity.

---

## Features

* Interactive prompt mode or command-line mode
* Single-target scanning
* Bulk scanning from a file of domains or URLs
* Headless or visible Chromium browser automation
* Lightweight preflight recon:

  * DNS resolution
  * Target IP collection
  * Canonical name and alias collection
  * Common web port checks
  * Service hints for discovered ports
  * TLS certificate metadata
  * Subject Alternative Name preview
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
* Bulk `aggregate_report.json` generation
* Triage scoring to help prioritize interesting targets

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

GATEkeeper supports interactive mode, command-line mode, and bulk mode.

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

## Bulk Scanning

GATEkeeper can scan a list of targets from a text file.

Create a file like:

```text
app.example.com
api.example.com
portal.example.com
https://admin.example.com
```

Run:

```bash
python3 gatekeeper.py -i subs.txt --headless --duration 15 --timeout 30000 --report --concurrency 3 --delay 1
```

Bare domains are automatically normalized with `https://` unless another scheme is specified.

Example with a full path:

```bash
python3 gatekeeper.py \
  -i /home/ek0ms/kctcs/subs.txt \
  --headless \
  --duration 10 \
  --timeout 25000 \
  --report \
  --concurrency 3 \
  --delay 1
```

Bulk mode creates one folder per target and writes a ranked aggregate report.

Default bulk output:

```text
gatekeeper_bulk_results/
```

Example:

```text
gatekeeper_bulk_results/
├── aggregate_report.json
├── app.example.com/
│   ├── network_capture.json
│   ├── report.json
│   ├── final_page.html
│   ├── final_screenshot.png
│   └── console_log.txt
└── api.example.com/
    ├── network_capture.json
    ├── report.json
    ├── final_page.html
    ├── final_screenshot.png
    └── console_log.txt
```

For large scopes, start without `--save-bodies` to keep scans fast and output smaller. Use `--save-bodies` later on the most interesting hosts.

---

## Options

| Argument                  | Description                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `url`                     | Target URL. Optional if using interactive mode or bulk mode.                                                  |
| `-i`, `--input-file FILE` | File containing targets, one domain or URL per line.                                                          |
| `-o`, `--output DIR`      | Output directory. Defaults to `<domain>_bang/` for single scans or `gatekeeper_bulk_results/` for bulk scans. |
| `--headless`              | Run Chromium without a visible browser window.                                                                |
| `--duration N`            | Interaction duration in seconds. Default: `45`.                                                               |
| `--timeout N`             | Navigation timeout in milliseconds. Default: `60000`.                                                         |
| `--cookies FILE`          | Load cookies from a Playwright-compatible JSON cookie file.                                                   |
| `--header "Name: Value"`  | Add a custom HTTP header. Can be used multiple times.                                                         |
| `--user-agent STRING`     | Override the default User-Agent.                                                                              |
| `--wait-selector CSS`     | Wait for a CSS selector before starting interaction.                                                          |
| `--save-bodies`           | Save response bodies to disk.                                                                                 |
| `--report`                | Generate `report.json`.                                                                                       |
| `--non-interactive`       | Do not prompt for missing values.                                                                             |
| `--concurrency N`         | Number of targets to scan at once in bulk mode. Default: `2`.                                                 |
| `--delay N`               | Delay in seconds after each target finishes. Default: `0`.                                                    |
| `--scheme http/https`     | Default scheme for bare domains in input files. Default: `https`.                                             |

---

## Output

By default, single-target results are saved in a directory named after the target domain.

Example:

```text
example.com_bang/
```

Generated files:

| File / Directory        | Description                                                                              |
| ----------------------- | ---------------------------------------------------------------------------------------- |
| `network_capture.json`  | Full request, response, failure, URL change, console log, recon, and saved body metadata |
| `final_page.html`       | Final rendered DOM after interaction                                                     |
| `final_screenshot.png`  | Full-page screenshot                                                                     |
| `console_log.txt`       | JavaScript console messages                                                              |
| `report.json`           | Structured report generated with `--report`                                              |
| `response_bodies/`      | Saved response bodies generated with `--save-bodies`                                     |
| `aggregate_report.json` | Bulk scan summary generated in bulk mode                                                 |

---

## Terminal Summary

Each target prints a summary like:

```text
============================================================
GATEKEEPER SUMMARY
============================================================
Initial URL: https://example.com
Final URL:   https://example.com/
Title:       Example Domain
Requests:    12
Responses:   12
Failures:    0
Console:     1
URL changes: 0
Bodies saved:0

------------------------------------------------------------
LIGHTWEIGHT RECON
------------------------------------------------------------
Host:        example.com
IPs:         ['93.184.216.34']
Canonical:   example.com
Aliases:     []
Open ports:  [80, 443]

[+] Service hints:
  - 80: http
  - 443: https

[+] TLS info:
  Not before: May 28 15:39:24 2026 GMT
  Not after:  Dec 12 15:39:24 2026 GMT
  SAN count:  3
    - example.com
    - www.example.com

[+] No HTTP redirect responses captured.

[-] No configured interesting endpoint terms captured.

[+] Detected technologies:
  - Nginx

[!] Missing common security headers:
  - content-security-policy
  - permissions-policy

[+] Final HTML captured and does not obviously look stuck on a spinner.

[+] Triage score: 12
```

---

## Report Contents

When `--report` is used, GATEkeeper generates `report.json` with:

* Target URL
* Final URL
* Final page title
* Triage score
* DNS and IP information
* Canonical name and aliases
* Open common web ports
* Service hints
* TLS certificate metadata
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
  "final_title": "Dashboard",
  "triage_score": 18,
  "recon": {
    "host": "example.com",
    "dns": {
      "canonical_name": "example.com",
      "aliases": [],
      "ips": ["93.184.216.34"]
    },
    "open_ports": [80, 443],
    "services": [
      {"port": 80, "hint": "http"},
      {"port": 443, "hint": "https"}
    ],
    "tls": {
      "not_before": "May 28 15:39:24 2026 GMT",
      "not_after": "Dec 12 15:39:24 2026 GMT",
      "san": ["example.com", "www.example.com"]
    }
  },
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

## Aggregate Report

Bulk mode writes:

```text
aggregate_report.json
```

The aggregate report includes:

* Total targets
* Completed scans
* Errors
* Results ranked by triage score
* Final URL
* Final title
* IPs
* Canonical name
* Aliases
* Open ports
* Service hints
* TLS expiration
* Request/response/failure counts
* URL change count
* Detected technologies
* Interesting endpoint count

This makes it easier to triage large target lists without opening every folder manually.

---

## Triage Score

GATEkeeper assigns a lightweight triage score to help prioritize results.

The score increases for signals such as:

* Non-standard web ports
* URL changes
* Interesting endpoint terms
* Missing common security headers
* Final URL differing from the initial target
* Certain detected technologies

The score is not a vulnerability rating. It is a sorting helper for recon workflows.

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

1. Normalizes the target URL.
2. Runs lightweight preflight recon:

   * Resolves DNS
   * Collects target IPs
   * Checks common web ports
   * Adds service hints
   * Pulls TLS certificate metadata when HTTPS is open
3. Launches a Chromium browser with a realistic viewport and User-Agent.
4. Optionally loads cookies and custom headers.
5. Navigates to the target URL.
6. Optionally waits for a CSS selector.
7. Simulates browser interaction:

   * Mouse movement
   * Clicks
   * Scrolling
   * Keyboard input
   * Viewport resizing
8. Captures requests, responses, failed requests, redirects, URL changes, and console logs.
9. Saves final HTML and screenshot.
10. Optionally saves response bodies.
11. Optionally generates a structured report.
12. In bulk mode, writes an aggregate report ranked by triage score.

---

## Disclaimer

This tool is intended for authorized security testing, research, educational assessments only.



---

<div align="center">

**Happy Hacking — Authorized Testing Only**

</div>
