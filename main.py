#!/usr/bin/env python3
"""
Zscaler + Claude CLI
Run: python main.py
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule

load_dotenv()

console = Console()

# ── Validate env vars ──────────────────────────────────────────────────────
REQUIRED = ["ANTHROPIC_API_KEY", "ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET", "ZSCALER_CLOUD", "ZSCALER_VANITY_DOMAIN"]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    console.print(f"[bold red][ERROR][/] Missing environment variables: {', '.join(missing)}")
    console.print("Copy .env.example to .env and fill in your credentials.")
    sys.exit(1)

from src import ZscalerAuth, ZscalerClient, ZscalerAnalyst

# ── Menu definitions ───────────────────────────────────────────────────────
MENU = {
    "1": {
        "label": "Firewall Rule Audit",
        "fetcher": "get_firewall_rules",
        "question": (
            "Audit these firewall rules for security gaps:\n"
            "1. Identify any overly permissive rules (e.g., ANY/ANY)\n"
            "2. Flag rules without logging enabled\n"
            "3. Check for shadow/conflicting rules\n"
            "4. List the top 5 risks with remediation steps"
        ),
    },
    "2": {
        "label": "Shadow IT Risk Assessment",
        "fetcher": "get_shadow_it_apps",
        "question": (
            "Assess these shadow IT applications:\n"
            "1. Rank the top 10 riskiest apps by data exfiltration potential\n"
            "2. Identify any that violate common compliance requirements (HIPAA, PCI, SOC2)\n"
            "3. Recommend which should be blocked vs. sanctioned\n"
            "4. Suggest DLP policies for apps that should be allowed but monitored"
        ),
    },
    "3": {
        "label": "SSL Inspection Policy Review",
        "fetcher": "get_ssl_inspection_rules",
        "question": (
            "Review these SSL inspection rules:\n"
            "1. Identify bypasses that create blind spots (financial, health sites)\n"
            "2. Flag missing inspection for high-risk categories\n"
            "3. Check if certificate pinning exceptions are too broad\n"
            "4. Recommend improvements for zero trust alignment"
        ),
    },
    "4": {
        "label": "DLP Dictionary Audit",
        "fetcher": "get_dlp_dictionaries",
        "question": (
            "Audit these DLP dictionaries:\n"
            "1. Identify gaps in coverage for common data types (PII, PCI, PHI)\n"
            "2. Flag any dictionaries that may generate high false positives\n"
            "3. Recommend additional patterns to add\n"
            "4. Check alignment with GDPR/CCPA/HIPAA data classifications"
        ),
    },
    "5": {
        "label": "Threat Protection Config Review",
        "fetcher": "get_threat_log_config",
        "question": (
            "Review this advanced threat protection configuration:\n"
            "1. Identify any protections that are disabled or set to 'Allow'\n"
            "2. Flag missing protections for current threat landscape\n"
            "3. Check botnet/C2 detection settings\n"
            "4. Recommend hardening steps prioritized by risk"
        ),
    },
    "6": {
        "label": "URL Category Policy Audit",
        "fetcher": "get_url_categories",
        "question": (
            "Audit these URL category policies:\n"
            "1. Identify categories set to 'Allow' that should be blocked or monitored\n"
            "2. Find categories that bypass SSL inspection\n"
            "3. Check for policy conflicts or redundant rules\n"
            "4. Recommend tightening for a zero trust posture\n"
            "5. POLICY VIOLATION CHECK (flag as critical): Our security policy strictly requires that all URLs "
            "in custom categories must be placed under 'URLs Retaining Parent Category' (dbCategorizedUrls / "
            "urlsRetainingParentCategoryCount > 0). Any custom category that has URLs in the 'Custom URLs' "
            "field (urls list / customUrlsCount > 0) is a policy violation. For each violating category, show "
            "only the category name and the customUrlsCount — do not list the actual URLs. State that each "
            "must have its URLs moved to 'URLs Retaining Parent Category'."
        ),
    },
    "7": {
        "label": "SSL Inspection Security Report",
        "fetcher": "get_ssl_inspection_full",
        "question": (
            "Audit these SSL inspection rules against Zscaler best practices. "
            "Produce exactly two things — nothing else.\n\n"
            "## SSL Inspection Rules\n\n"
            "A markdown table with these four columns, one row per rule:\n\n"
            "| Rule Name | Criticality | Current Config | Suggested Fix |\n"
            "|-----------|-------------|----------------|---------------|\n\n"
            "Column guidance:\n"
            "- **Rule Name**: exact rule name from the data\n"
            "- **Criticality**: CRITICAL / HIGH / MEDIUM / LOW / ✅ OK\n"
            "- **Current Config**: translate API values — DECRYPT → Inspect, DO_NOT_DECRYPT → Do Not Inspect, BLOCK → Block. "
            "Show state as 🟢 Enabled or 🔴 Disabled. "
            "Also check and show inline for each rule: "
            "Block SNI (🟢/🔴), OCSP Check (🟢/🔴), Block Undecryptable (🟢/🔴) if those fields exist on the rule. "
            "Format: 'Inspect — All traffic (🟢 Enabled) | SNI 🔴 | OCSP 🔴 | Undecryptable 🔴'\n"
            "- **Suggested Fix**: combine the policy flaw fix (if any) with any of these missing security checks. "
            "Use these exact phrases when the check is missing/disabled:\n"
            "  • Block SNI missing on a DECRYPT/Inspect rule: "
            "'Enable Block SNI — traffic without SNI can bypass URL-based policies and hide C2 communications'\n"
            "  • OCSP Revocation Check disabled: "
            "'Enable OCSP check — without it, connections to sites with revoked certificates (compromised/phishing) are permitted'\n"
            "  • Block Undecryptable Traffic disabled on an Inspect All or default rule: "
            "'Enable Block Undecryptable Traffic — undecryptable traffic is a known exfiltration and C2 evasion technique'\n"
            "  If multiple issues exist on one rule, list each on a new line within the cell. "
            "If no issues, use 'No action needed'.\n\n"
            "Criticality rules (escalate if any security check above is also missing):\n"
            "- CRITICAL: Do Not Inspect on malware/botnets/phishing/anonymizers/newly registered domains, or ANY/ANY bypass\n"
            "- HIGH: Do Not Inspect on cloud storage/file sharing/social media; broad category bypass; "
            "Block SNI missing on an Inspect rule\n"
            "- MEDIUM: 🔴 Disabled rule; rule ordering issue; OCSP or Block Undecryptable missing\n"
            "- LOW: minor best-practice deviation\n"
            "- ✅ OK: correctly configured with all security checks enabled\n\n"
            "## Global SSL Settings\n\n"
            "A second markdown table for tenant-wide SSL settings "
            "(look for blockNoSni, ocspEnabled, blockUndecryptableTraffic or similar fields in the data):\n\n"
            "| Setting | Status | Recommendation |\n"
            "|---------|--------|----------------|\n"
            "| Block No Server Name Indication (SNI) | 🟢 Enabled / 🔴 Disabled | ... |\n"
            "| OCSP Revocation Check | 🟢 Enabled / 🔴 Disabled | ... |\n"
            "| Block Undecryptable Traffic | 🟢 Enabled / 🔴 Disabled | ... |\n\n"
            "Show 🟢 Enabled if true/present, 🔴 Disabled if false/missing. "
            "If 🔴 Disabled, bold the recommendation. Use these exact recommendations:\n"
            "- Block SNI disabled: **Enable on all Inspect rules — traffic without SNI can bypass URL-based policies and hide C2 communications**\n"
            "- OCSP disabled: **Enable globally — without OCSP checks, connections to sites with revoked certificates (compromised/phishing) are permitted**\n"
            "- Block Undecryptable disabled: **Enable on Inspect All and default rule — undecryptable traffic is a known exfiltration and C2 evasion technique**\n\n"
            "End with one summary line: count of CRITICAL, HIGH, MEDIUM, LOW, and OK rules. Nothing else."
        ),
    },
}


def prompt(msg: str):
    """Read a line of input, returning None on EOF (non-interactive/piped use)."""
    try:
        return input(msg).strip()
    except EOFError:
        return None


def print_banner():
    console.print(Panel.fit(
        f"[bold cyan]Zscaler Security Analyst[/] — Powered by Claude\n"
        f"[dim]Cloud:[/] {os.environ['ZSCALER_CLOUD']}   "
        f"[dim]Date:[/] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        border_style="cyan",
    ))


def print_menu():
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=5)
    table.add_column()
    for key, item in MENU.items():
        table.add_row(f"[{key}]", item["label"])
    table.add_row("[c]", "Custom question (with data source selection)")
    table.add_row("[q]", "Quit")
    console.print("\n[bold]Select an analysis:[/]\n")
    console.print(table)
    console.print()


def save_report(label: str, data, analysis: str):
    Path("logs").mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = label.lower().replace(" ", "_")
    path = Path(f"logs/{timestamp}_{slug}.json")
    path.write_text(json.dumps({
        "timestamp": timestamp,
        "analysis_type": label,
        "raw_data": data,
        "claude_analysis": analysis,
    }, indent=2))
    console.print(f"\n  [bold green]✓ Saved[/] {path}")


def run_custom(zs: ZscalerClient, analyst: ZscalerAnalyst):
    """Let user pick a data source and type a custom question."""
    sources = {str(i + 1): (name, getattr(zs, name)) for i, name in enumerate([
        "get_firewall_rules", "get_url_categories", "get_ssl_inspection_rules",
        "get_shadow_it_apps", "get_dlp_dictionaries", "get_threat_log_config",
        "get_blocked_destinations", "get_ssl_inspection_full",
    ])}

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=5)
    table.add_column()
    for k, (name, _) in sources.items():
        table.add_row(f"[{k}]", name)
    console.print("\n[bold]Available data sources:[/]\n")
    console.print(table)
    console.print()

    src_key = prompt("Select data source: ")
    if src_key is None:
        return
    if src_key not in sources:
        console.print("  [bold red][ERROR][/] Invalid selection.")
        return

    name, fetcher = sources[src_key]
    try:
        with console.status(f"Fetching [cyan]{name}[/]..."):
            data = fetcher()
    except Exception as e:
        console.print(f"  [bold red][ERROR][/] Failed to fetch data ({type(e).__name__}). Check your credentials and network.")
        return

    question = prompt("\nYour question: ")
    if not question:
        return

    console.print(Rule(title="Claude Analysis", style="cyan"))
    analysis = analyst.analyze(data, question)
    save_report(name, data, analysis)


def main():
    print_banner()

    auth = ZscalerAuth(
        client_id=os.environ["ZSCALER_CLIENT_ID"],
        client_secret=os.environ["ZSCALER_CLIENT_SECRET"],
        cloud=os.environ["ZSCALER_CLOUD"],
        vanity_domain=os.environ["ZSCALER_VANITY_DOMAIN"],
    )
    analyst = ZscalerAnalyst(api_key=os.environ["ANTHROPIC_API_KEY"])

    # Test auth on startup
    try:
        with console.status("Authenticating with Zscaler OneAPI..."):
            _ = auth.token
        console.print("  [green]✓[/] Authenticated")
    except Exception as e:
        console.print(f"  [bold red][ERROR][/] Authentication failed ({type(e).__name__}). Check ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, and ZSCALER_VANITY_DOMAIN.")
        sys.exit(1)

    zs = ZscalerClient(auth)

    while True:
        print_menu()
        choice = prompt("Choice: ")
        if choice is None:
            console.print("  Bye.\n")
            break
        choice = choice.lower()

        if choice == "q":
            console.print("  Bye.\n")
            break

        if choice == "c":
            run_custom(zs, analyst)
            continue

        if choice not in MENU:
            console.print("  [bold red][ERROR][/] Invalid choice.")
            continue

        item = MENU[choice]
        label = item["label"]
        fetcher_name = item["fetcher"]
        question = item["question"]

        try:
            with console.status(f"Fetching [cyan]{label}[/] data from Zscaler..."):
                data = getattr(zs, fetcher_name)()
            count = len(data) if isinstance(data, list) else f"{sum(len(v) for v in data.values() if isinstance(v, list))} records" if isinstance(data, dict) else "N/A"
            console.print(f"  [green]✓[/] {count} records fetched")
        except Exception as e:
            console.print(f"  [bold red][ERROR][/] Zscaler API call failed ({type(e).__name__}). Check your permissions and network.")
            continue

        console.print(Rule(title="Claude Analysis", style="cyan"))
        analysis = analyst.analyze(data, question)
        save_report(label, data, analysis)

        if prompt("\n  Press Enter to continue...") is None:
            break


if __name__ == "__main__":
    main()
