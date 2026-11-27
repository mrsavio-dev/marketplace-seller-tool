"""Eldorado seller API client.

The authentication flow follows Eldorado's published instructions:

* exchange Client ID + Client secret at ``POST https://eldorado.gg/api/authentication/seller/token``
* send the returned token in the ``Authorization`` header
* tokens expire after 15 minutes, so the client refreshes them

The offer endpoint paths are *not* documented publicly, so they come from the
config and live mode is refused until they are marked verified. Every call is
made against the live API: Eldorado has no test environment.
"""

from __future__ import annotations

import base64
import json
import time
import urllib.error
import urllib.request
from decimal import Decimal

DEFAULT_BASE_URL = "https://eldorado.gg/api"
TOKEN_PATH = "/authentication/seller/token"
TOKEN_LIFETIME_SECONDS = 15 * 60
REFRESH_MARGIN_SECONDS = 60


class EldoradoApiError(RuntimeError):
    def __init__(self, status: int, message: str, body: str = "") -> None:
        super().__init__(f"HTTP {status}: {message}")
        self.status = status
        self.body = body


class EldoradoClient:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 30.0,
    ) -> None:
        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._token: str | None = None
        self._token_expires_at = 0.0

    # -- auth ---------------------------------------------------------------

    def _basic_auth(self) -> str:
        raw = f"{self._client_id}:{self._client_secret}".encode("utf-8")
        return "Basic " + base64.b64encode(raw).decode("ascii")

    def _fetch_token(self) -> str:
        request = urllib.request.Request(
            self._base_url + TOKEN_PATH,
            data=b"{}",
            method="POST",
            headers={
                "Authorization": self._basic_auth(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self._timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        token = payload.get("access_token") or payload.get("accessToken") or payload.get("token")
        if not token:
            raise EldoradoApiError(200, "token response had no access token", json.dumps(payload)[:500])
        self._token = str(token)
        self._token_expires_at = time.monotonic() + TOKEN_LIFETIME_SECONDS - REFRESH_MARGIN_SECONDS
        return self._token

    def access_token(self) -> str:
        if self._token is None or time.monotonic() >= self._token_expires_at:
            return self._fetch_token()
        return self._token

    # -- transport ----------------------------------------------------------

    def call(self, method: str, path: str, payload: dict | None = None) -> dict:
        if not path.startswith("/"):
            raise ValueError("path must start with '/'")
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        request = urllib.request.Request(
            self._base_url + path,
            data=data,
            method=method.upper(),
            headers={
                "Authorization": self.access_token(),
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self._timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", "replace")
            raise EldoradoApiError(exc.code, exc.reason or "request failed", body) from exc
        except urllib.error.URLError as exc:
            raise EldoradoApiError(0, f"network error: {exc.reason}") from exc
        return json.loads(body) if body.strip() else {}

    # -- offers -------------------------------------------------------------

    def set_price(self, offer_path: str, price_path: str, offer_id: str, price: Decimal) -> dict:
        """Set the price of one offer.

        ``offer_path`` and ``price_path`` are templates from the config, e.g.
        ``/seller/offers/{offer_id}`` and ``/seller/offers/{offer_id}/price``.
        They are configurable because Eldorado does not publish them.
        """

        return self.call(
            "PATCH",
            offer_path.format(offer_id=offer_id),
            {"price": str(price)},
        )
