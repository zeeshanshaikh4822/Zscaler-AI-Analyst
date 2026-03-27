"""Zscaler OneAPI OAuth2 authentication with automatic token refresh."""

import time
import requests


class ZscalerAuth:
    def __init__(self, client_id: str, client_secret: str, cloud: str, vanity_domain: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.cloud = cloud
        self.vanity_domain = vanity_domain
        self._token = None
        self._expires_at: float = 0

    @property
    def token(self) -> str:
        if not self._token or time.time() >= self._expires_at - 60:
            self._refresh_token()
        return self._token

    def _refresh_token(self):
        url = f"https://{self.vanity_domain}/oauth2/v1/token"
        resp = requests.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=15,
            verify=True,
        )
        resp.raise_for_status()
        data = resp.json()
        self._token = data["access_token"]
        self._expires_at = time.time() + data.get("expires_in", 3600)

    @property
    def headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
