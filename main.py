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

load_dotenv()

# ── Validate env vars ──────────────────────────────────────────────────────
REQUIRED = ["ANTHROPIC_API_KEY", "ZSCALER_CLIENT_ID", "ZSCALER_CLIENT_SECRET", "ZSCALER_CLOUD", "ZSCALER_VANITY_DOMAIN"]
missing = [k for k in REQUIRED if not os.environ.get(k)]
if missing:
    print(f"[ERROR] Missing environment variables: {', '.join(missing)}")
    print("Copy .env.example to .env and fill in your credentials.")
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
            "4. Recommend tightening for a zero trust posture"
        ),
    },
}


def print_banner():
    print("\n" + "═" * 60)
    print("  Zscaler Security Analyst — Powered by Claude")
    print("═" * 60)
    print(f"  Cloud: {os.environ['ZSCALER_CLOUD']}")
    print(f"  Date:  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═" * 60)


def print_menu():
    print("\nSelect an analysis:\n")
    for key, item in MENU.items():
        print(f"  [{key}] {item['label']}")
    print("  [c] Custom question (with data source selection)")
    print("  [q] Quit\n")


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
    print(f"\n  [Saved] {path}")


def run_custom(zs: ZscalerClient, analyst: ZscalerAnalyst):
    """Let user pick a data source and type a custom question."""
    sources = {str(i + 1): (name, getattr(zs, name)) for i, name in enumerate([
        "get_firewall_rules", "get_url_categories", "get_ssl_inspection_rules",
        "get_shadow_it_apps", "get_dlp_dictionaries", "get_threat_log_config",
        "get_blocked_destinations",
    ])}

    print("\nAvailable data sources:")
    for k, (name, _) in sources.items():
        print(f"  [{k}] {name}")

    src_key = input("\nSelect data source: ").strip()
    if src_key not in sources:
        print("  Invalid selection.")
        return

    name, fetcher = sources[src_key]
    print(f"\n  Fetching {name}...")
    try:
        data = fetcher()
    except Exception as e:
        print(f"  [ERROR] Failed to fetch data ({type(e).__name__}). Check your credentials and network.")
        return

    question = input("\nYour question: ").strip()
    if not question:
        return

    print("\n" + "─" * 60)
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
    print("\n  Authenticating with Zscaler OneAPI...", end="", flush=True)
    try:
        _ = auth.token
        print(" OK")
    except Exception as e:
        print(f"\n  [ERROR] Authentication failed ({type(e).__name__}). Check ZSCALER_CLIENT_ID, ZSCALER_CLIENT_SECRET, and ZSCALER_VANITY_DOMAIN.")
        sys.exit(1)

    zs = ZscalerClient(auth)

    while True:
        print_menu()
        choice = input("Choice: ").strip().lower()

        if choice == "q":
            print("  Bye.\n")
            break

        if choice == "c":
            run_custom(zs, analyst)
            continue

        if choice not in MENU:
            print("  Invalid choice.")
            continue

        item = MENU[choice]
        label = item["label"]
        fetcher_name = item["fetcher"]
        question = item["question"]

        print(f"\n  Fetching {label} data from Zscaler...", end="", flush=True)
        try:
            data = getattr(zs, fetcher_name)()
            count = len(data) if isinstance(data, list) else "N/A"
            print(f" {count} records")
        except Exception as e:
            print(f"\n  [ERROR] Zscaler API call failed ({type(e).__name__}). Check your permissions and network.")
            continue

        print(f"\n  Analyzing with Claude...\n")
        print("─" * 60)
        analysis = analyst.analyze(data, question)
        save_report(label, data, analysis)

        input("\n  Press Enter to continue...")


if __name__ == "__main__":
    main()
