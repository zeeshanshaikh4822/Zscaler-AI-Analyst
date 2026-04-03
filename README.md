# Zscaler Security Analyst — Powered by Claude

> [!WARNING]
> **Beta Software — Do Not Use in Production**
>
> This tool is under active development and has not been validated for production use. Run it only against a **non-production / lab Zscaler tenant** until a stable release is announced.
>
> **Always use a read-only API credential** (see [Zscaler API Setup](#zscaler-api-setup)). This tool only performs GET requests and never modifies your configuration, but a scoped read-only key ensures that is enforced at the API level.

A CLI tool that pulls live configuration data from your Zscaler tenant via OneAPI and sends it to Claude (Opus) for expert security analysis. Runs interactively in the terminal — no web server, no setup beyond credentials.

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![Anthropic](https://img.shields.io/badge/Claude-Opus%204.6-purple) ![Zscaler](https://img.shields.io/badge/Zscaler-ZIA%20OneAPI-00A1E0)

---

## What It Does

Select an analysis from the menu, and the tool fetches live data from your Zscaler tenant, sends it to Claude, and streams a formatted security report directly to your terminal. Every report is also saved to `logs/` as JSON.

```
╭─────────────────────────────────────────────╮
│  Zscaler Security Analyst — Powered by Claude │
│  Cloud: zscalerthree.net   Date: 2026-04-04  │
╰─────────────────────────────────────────────╯

Select an analysis:

  [1]  Firewall Rule Audit
  [2]  Shadow IT Risk Assessment
  [3]  SSL Inspection Policy Review
  [4]  DLP Dictionary Audit
  [5]  Threat Protection Config Review
  [6]  URL Category Policy Audit
  [7]  SSL Inspection Security Report
  [c]  Custom question (with data source selection)
  [q]  Quit
```

---

## Analyses

| # | Name | What Claude checks |
|---|------|--------------------|
| 1 | **Firewall Rule Audit** | Overly permissive rules, missing logging, shadow/conflicting rules, top 5 risks |
| 2 | **Shadow IT Risk Assessment** | Riskiest apps by exfiltration potential, compliance violations (HIPAA/PCI/SOC2), block vs. sanction recommendations |
| 3 | **SSL Inspection Policy Review** | Bypass blind spots, missing high-risk category coverage, certificate pinning scope |
| 4 | **DLP Dictionary Audit** | PII/PCI/PHI coverage gaps, false positive risk, GDPR/CCPA/HIPAA alignment |
| 5 | **Threat Protection Config Review** | Disabled protections, botnet/C2 detection, hardening steps by risk |
| 6 | **URL Category Policy Audit** | Risky allow-listed categories, SSL bypass conflicts, custom URL policy violations |
| 7 | **SSL Inspection Security Report** | Per-rule audit vs. Zscaler best practices — action names translated, per-rule Block SNI / OCSP / Block Undecryptable Traffic checks, criticality-rated table with exact admin fix steps |
| c | **Custom Question** | Choose any data source, ask your own question |

### SSL Inspection Security Report (Option 7)

The most detailed analysis. Produces two tables:

**Rules table** — one row per rule:

| Rule Name | Criticality | Current Config | Suggested Fix |
|-----------|-------------|----------------|---------------|
| Inspect All | HIGH | Inspect — All traffic (🟢 Enabled) \| SNI 🔴 \| OCSP 🔴 \| Undecryptable 🔴 | Enable Block SNI — traffic without SNI can bypass URL-based policies and hide C2 communications |
| Bypass Financial | ✅ OK | Do Not Inspect — Financial (🟢 Enabled) | No action needed |

**Global settings table** — tenant-wide SSL security settings with 🟢/🔴 status and bolded remediation if disabled.

---

## Zscaler API Setup

This tool uses Zscaler's OneAPI OAuth2 (`client_credentials` flow). To keep your tenant safe, create a **dedicated read-only API client** before running anything.

### Create a read-only API client in Zscaler

1. Log in to the Zscaler Admin Portal
2. Go to **Administration → API → API Key Management**
3. Click **Add API Client**
4. Fill in:
   - **Name**: `claude-analyst-readonly` (or similar)
   - **Role**: Select a role with **read-only** permissions — if no read-only role exists, create one (see below)
5. Copy the **Client ID** and **Client Secret** — you won't see the secret again
6. Click **Save**

### Create a read-only admin role (if needed)

1. Go to **Administration → Role Management → Add Role**
2. Set **Role Name**: `API Read Only`
3. Under **Permissions**, set everything to **View** — do not grant any Edit, Create, or Delete permissions
4. Save the role, then assign it to your API client in step 4 above

> [!NOTE]
> Zscaler's API does not have a built-in "read-only" toggle per client — access is controlled by the **admin role** assigned to the client. A properly scoped View-only role prevents any write operations even if someone reuses the credentials.

### What this tool reads (GET only)

| Zscaler Product | Data accessed |
|-----------------|--------------|
| ZIA | Firewall rules, SSL inspection rules, URL categories, DLP dictionaries, shadow IT apps, threat protection config, IP destination groups |
| ZPA | Application segments, access policies, connectors *(not yet in menu — available on client class)* |
| ZDX | App list, scorecard *(not yet in menu)* |

This tool makes **no POST, PUT, or DELETE requests**. All Zscaler calls are read-only GETs.

---

## Setup

### Prerequisites

- Python 3.9+
- A Zscaler ZIA tenant with OneAPI access
- An Anthropic API key

### Install

```bash
git clone https://github.com/your-org/zscaler-claude.git
cd zscaler-claude
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

| Variable | Where to find it |
|----------|-----------------|
| `ANTHROPIC_API_KEY` | [console.anthropic.com](https://console.anthropic.com) → API Keys |
| `ZSCALER_CLIENT_ID` | Zscaler Admin → API → API Key Management |
| `ZSCALER_CLIENT_SECRET` | Zscaler Admin → API → API Key Management |
| `ZSCALER_CLOUD` | Zscaler Admin → About (e.g. `zscalerthree.net`) |
| `ZSCALER_VANITY_DOMAIN` | Zscaler Admin → Authentication → Authentication Profile (e.g. `yourcompany.zslogin.net`) |

### Run

```bash
python3 main.py
```

---

## Architecture

```
main.py               — CLI entrypoint: menu loop, rich UI, report saving
src/auth.py           — ZscalerAuth: OAuth2 client_credentials, auto token refresh
src/zscaler_client.py — ZscalerClient: HTTP wrapper for ZIA/ZPA/ZDX endpoints
src/analyst.py        — ZscalerAnalyst: sends data to Claude, live markdown streaming
logs/                 — JSON reports saved after each analysis
```

**Data flow:**
```
Menu selection
  → ZscalerClient fetches live JSON from Zscaler OneAPI
  → ZscalerAnalyst sends JSON + question to Claude Opus
  → Response streams to terminal as rendered markdown
  → Full report saved to logs/<timestamp>_<label>.json
```

### Key design points

- **Auth is transparent** — `ZscalerAuth.token` is a lazy property that fetches and auto-refreshes the OAuth2 token. Token URL uses `ZSCALER_VANITY_DOMAIN`, not `ZSCALER_CLOUD`.
- **Streaming by default** — Claude's response renders live in the terminal via `rich.live.Live` + `rich.markdown.Markdown` as it arrives.
- **Reports always saved** — every analysis writes raw Zscaler data + Claude's analysis to `logs/` as JSON for audit trails.
- **EOF-safe input** — the `prompt()` helper returns `None` instead of raising on piped/non-interactive use.

---

## Zscaler API Coverage

### ZIA (wired to menu)

| Method | Endpoint |
|--------|----------|
| `get_firewall_rules()` | `/api/v1/firewall/rules` |
| `get_ssl_inspection_rules()` | `/api/v1/sslInspectionRules` |
| `get_ssl_inspection_full()` | SSL rules + URL categories combined |
| `get_url_categories()` | `/api/v1/urlCategories` |
| `get_shadow_it_apps()` | `/api/v1/cloudApplications/lite` |
| `get_dlp_dictionaries()` | `/api/v1/dlp/dictionaries` |
| `get_threat_log_config()` | `/api/v1/cyberThreatProtection/advancedThreatSettings` |
| `get_blocked_destinations()` | `/api/v1/ipDestinationGroups` |

### ZPA / ZDX (on client, not yet in menu)

ZPA methods (`get_zpa_applications`, `get_zpa_policies`, `get_zpa_connectors`) and ZDX methods (`get_zdx_apps`, `get_zdx_score`) exist on `ZscalerClient` but require a `customer_id` parameter with no UI yet.

---

## Reports

Reports are saved to `logs/<YYYYMMDD_HHMMSS>_<label>.json`:

```json
{
  "timestamp": "20260404_120000",
  "analysis_type": "SSL Inspection Security Report",
  "raw_data": { ... },
  "claude_analysis": "# SSL Inspection Security Report\n\n..."
}
```

---

## Requirements

```
anthropic>=0.40.0
requests>=2.31.0
python-dotenv>=1.0.0
rich>=13.0.0
```
