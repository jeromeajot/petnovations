"""Pure helpers for pulling tokens out of a refresh response.

Kept free of Home Assistant and aiohttp imports so it can be unit-tested in
isolation and reused without pulling in the whole integration.
"""

from __future__ import annotations

_TOKEN_KEYS = ("token", "accessToken", "access_token", "jwt", "authToken", "idToken")
_REFRESH_KEYS = ("refreshToken", "refresh_token")
_WRAPPERS = ("data", "result", "payload")


def _search(data: dict, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        val = data.get(key)
        if isinstance(val, str) and val:
            return val
    for wrapper in _WRAPPERS:
        inner = data.get(wrapper)
        if isinstance(inner, dict):
            found = _search(inner, keys)
            if found:
                return found
    return None


def find_access_token(data: dict) -> str | None:
    """Return the access token from a refresh response, field-name tolerant."""
    return _search(data, _TOKEN_KEYS)


def find_refresh_token(data: dict) -> str | None:
    """Return a rotated refresh token if the response carries one."""
    return _search(data, _REFRESH_KEYS)
