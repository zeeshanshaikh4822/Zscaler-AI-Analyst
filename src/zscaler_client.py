"""Zscaler OneAPI client — ZIA, ZPA, ZDX endpoints."""

import requests
from .auth import ZscalerAuth


class ZscalerClient:
    def __init__(self, auth: ZscalerAuth):
        self.auth = auth
        self._zia = f"https://zsapi.{auth.cloud}/api/v1"
        self._zpa = f"https://zsapi.{auth.cloud}/zpa/api/v1"
        self._zdx = f"https://zsapi.{auth.cloud}/zdx/api/v1"

    def _get(self, url: str, params: dict = None):
        resp = requests.get(url, headers=self.auth.headers, params=params, timeout=20, verify=True)
        resp.raise_for_status()
        return resp.json()

    # ── ZIA ──────────────────────────────────────────────────────────────────

    def get_url_categories(self) -> list:
        """All URL filtering categories and their policy actions."""
        return self._get(f"{self._zia}/urlCategories")

    def get_firewall_rules(self) -> list:
        """Firewall filtering rules ordered by precedence."""
        return self._get(f"{self._zia}/firewall/rules")

    def get_ssl_inspection_rules(self) -> list:
        """SSL inspection policy rules."""
        return self._get(f"{self._zia}/sslInspectionRules")

    def get_threat_log_config(self) -> dict:
        """Advanced threat protection configuration."""
        return self._get(f"{self._zia}/cyberThreatProtection/advancedThreatSettings")

    def get_shadow_it_apps(self) -> list:
        """Shadow IT cloud applications discovered in traffic."""
        return self._get(f"{self._zia}/cloudApplications/lite")

    def get_blocked_destinations(self) -> list:
        """Custom blocked IP/URL destination lists."""
        return self._get(f"{self._zia}/ipDestinationGroups")

    def get_dlp_dictionaries(self) -> list:
        """DLP dictionaries in use."""
        return self._get(f"{self._zia}/dlp/dictionaries")

    # ── ZPA ──────────────────────────────────────────────────────────────────

    def get_zpa_applications(self, customer_id: str) -> list:
        """ZPA application segments."""
        return self._get(f"{self._zpa}/mgmtconfig/v1/admin/customers/{customer_id}/application")

    def get_zpa_policies(self, customer_id: str) -> list:
        """ZPA access policies."""
        return self._get(f"{self._zpa}/mgmtconfig/v1/admin/customers/{customer_id}/policySet/rules/policyType/ACCESS_POLICY")

    def get_zpa_connectors(self, customer_id: str) -> list:
        """App connectors status."""
        return self._get(f"{self._zpa}/mgmtconfig/v1/admin/customers/{customer_id}/connector")

    # ── ZDX ──────────────────────────────────────────────────────────────────

    def get_zdx_apps(self) -> list:
        """Apps being monitored by ZDX."""
        return self._get(f"{self._zdx}/apps")

    def get_zdx_score(self) -> dict:
        """Overall ZDX digital experience score."""
        return self._get(f"{self._zdx}/scorecard")
