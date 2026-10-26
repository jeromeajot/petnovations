"""Async client for the Petnovations / CatGenie IoT API."""

from __future__ import annotations

import logging
from typing import Any

import aiohttp

from .const import (
    BASE_URL,
    DEVICES_PARAMS,
    DEVICES_PATH,
    REFRESH_SIGN_PATH,
    REFRESH_URL_PATH,
)
from .signing import Signer, resolve_key
from .tokenutil import find_access_token, find_refresh_token

_LOGGER = logging.getLogger(__name__)


class PetnovationsAuthError(Exception):
    """Raised when authentication fails and the user must re-authenticate."""


class PetnovationsApiError(Exception):
    """Raised for transient/other API errors."""


class PetnovationsAPI:
    """Talks to the signed CatGenie cloud API.

    Needs the signing key (or the 84-char secret) plus a long-lived refresh
    token. Access tokens are minted and re-minted automatically; none needs to
    be supplied, though a cached one can be passed to avoid an initial refresh.
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        hmac_key: str,
        refresh_token: str,
        access_token: str | None = None,
    ) -> None:
        self._session = session
        self._signer = Signer(resolve_key(hmac_key))
        self._refresh_token = refresh_token
        self._access_token = access_token

    @property
    def access_token(self) -> str | None:
        return self._access_token

    @property
    def refresh_token(self) -> str:
        return self._refresh_token

    async def _request(
        self,
        method: str,
        url_path: str,
        *,
        sign_path: str | None = None,
        params: dict | None = None,
        body: dict | None = None,
        _retry: bool = True,
    ) -> Any:
        if not self._access_token:
            await self.refresh()

        sign_path = sign_path or url_path
        headers = self._signer.headers(sign_path, method, body, params)
        headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
                "Authorization": f"Bearer {self._access_token}",
            }
        )
        url = f"{BASE_URL}/{url_path.lstrip('/')}"

        async with self._session.request(
            method, url, headers=headers, params=params, json=body
        ) as resp:
            text = await resp.text()
            _LOGGER.debug("%s %s -> %s", method, url_path, resp.status)

            if resp.status == 200:
                try:
                    return await resp.json(content_type=None)
                except Exception as err:  # noqa: BLE001
                    raise PetnovationsApiError(f"Bad JSON from {url_path}: {err}") from err

            if resp.status in (401, 403):
                lowered = text.lower()
                if "token" in lowered and _retry:
                    _LOGGER.debug("Access token rejected; refreshing and retrying")
                    await self.refresh()
                    return await self._request(
                        method,
                        url_path,
                        sign_path=sign_path,
                        params=params,
                        body=body,
                        _retry=False,
                    )
                raise PetnovationsAuthError(
                    f"Auth rejected (HTTP {resp.status}) for {url_path}: {text[:200]}"
                )

            raise PetnovationsApiError(f"HTTP {resp.status} from {url_path}: {text[:200]}")

    async def refresh(self) -> str:
        """Exchange the long-lived refresh token for a fresh access token."""
        body = {"refreshToken": self._refresh_token}
        headers = self._signer.headers(REFRESH_SIGN_PATH, "POST", body, None)
        headers.update(
            {
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )
        url = f"{BASE_URL}/{REFRESH_URL_PATH}"

        async with self._session.post(url, headers=headers, json=body) as resp:
            text = await resp.text()
            if resp.status != 200:
                raise PetnovationsAuthError(
                    f"Token refresh failed (HTTP {resp.status}): {text[:200]}"
                )
            try:
                data = await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                raise PetnovationsAuthError(f"Bad refresh response: {err}") from err

        token = find_access_token(data)
        if not token:
            raise PetnovationsAuthError(
                f"No access token found in refresh response. Keys: {list(data)[:12]}"
            )
        self._access_token = token
        new_refresh = find_refresh_token(data)
        if new_refresh:
            self._refresh_token = new_refresh
        return token

    async def async_get_devices(self) -> dict:
        """Return the raw device payload (contains 'thingList')."""
        data = await self._request("GET", DEVICES_PATH, params=DEVICES_PARAMS)
        if not isinstance(data, dict) or "thingList" not in data:
            raise PetnovationsApiError("Response did not contain 'thingList'")
        return data

    async def async_validate(self) -> dict:
        """Validate credentials during config flow; returns the device payload."""
        return await self.async_get_devices()
