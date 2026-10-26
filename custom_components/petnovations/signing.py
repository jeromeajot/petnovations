"""Request signing for the Petnovations / CatGenie IoT API.

Petnovations reworked the mobile API so that EVERY request must carry a set of
signed headers. This module reproduces that scheme. The algorithm was reverse
engineered from the CatGenie React Native app (see CatDjinni research by
Rukongai); this is a clean reimplementation.

Headers produced per request:

    x-pm-en-ver : constant "1.0.0"
    x-render-t  : "<path-without-leading-slash>/<unix-ms-timestamp>"
    x-pm-en-dec : AES-256-CBC(zero IV, PKCS7) of "<ts>-<7 random chars + 'Z'>",
                  base64 encoded. Acts as an anti-replay / timestamp token.
    y-pm-sg-b   : HMAC-SHA256(key, serialize(body)   + x-render-t) hex
    y-pm-sg-p   : HMAC-SHA256(key, serialize(params) + x-render-t) hex

The HMAC key is NOT shipped here. It is an app secret that you must extract
from your own copy of the CatGenie app (see README). Pass it in as `hmac_key`.

The AES key below is a static value constructed inside the app bundle and is
the same for every user, so it is included.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import random
import string
import time

# Static AES-256 key for the x-pm-en-dec header (constant across all users).
# Built in the app as "P-3Rp6d81Kw9a3Z-" + getMessage('vyC').
_AES_KEY = b"P-3Rp6d81Kw9a3Z-CyvWH0WXRieyITk6"
_AES_IV = b"\x00" * 16

# Derivation parameters embedded in the app bundle, "index-prefix-suffix".
DERIVATION_PARAMS = {
    "dev": "0-1b-Mg",
    "staging": "28-wq-0C",
    "production": "56-Yt-x3",
}


def resolve_key(key_or_secret: str, environment: str = "production") -> str:
    """Accept either the final 32-char signing key or the 84-char app secret.

    An 84-character input is treated as the raw secret and run through the
    documented derivation. Anything else is assumed to already be the key.
    """
    value = (key_or_secret or "").strip()
    if len(value) == 84:
        return derive_hmac_key(value, environment)
    return value


def derive_hmac_key(secret: str, environment: str = "production") -> str:
    """Derive the HMAC key from the raw app secret.

    key = prefix + secret[index:index + 28] + suffix

    If you already extracted the final HMAC key directly, skip this and pass the
    key straight to Signer().
    """
    params = DERIVATION_PARAMS.get(environment, DERIVATION_PARAMS["production"])
    index_s, prefix, suffix = params.split("-")
    index = int(index_s)
    return prefix + secret[index : index + 28] + suffix


def _aes_encrypt(plaintext: bytes) -> bytes:
    """AES-256-CBC encrypt with zero IV and PKCS7 padding.

    Tries pycryptodome, then cryptography, then the openssl CLI. One of these is
    available inside Home Assistant (pycryptodome is declared in manifest.json);
    the openssl fallback keeps the standalone verifier running on a bare system
    Python with no extra packages installed.
    """
    pad_len = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad_len]) * pad_len

    try:
        from Crypto.Cipher import AES  # type: ignore

        return AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV).encrypt(padded)
    except ImportError:
        pass

    try:
        from cryptography.hazmat.primitives.ciphers import (  # type: ignore
            Cipher,
            algorithms,
            modes,
        )

        encryptor = Cipher(algorithms.AES(_AES_KEY), modes.CBC(_AES_IV)).encryptor()
        return encryptor.update(padded) + encryptor.finalize()
    except ImportError:
        pass

    import subprocess

    result = subprocess.run(
        [
            "openssl",
            "enc",
            "-aes-256-cbc",
            "-K",
            _AES_KEY.hex(),
            "-iv",
            _AES_IV.hex(),
            "-nosalt",
        ],
        input=padded,
        capture_output=True,
        check=True,
    )
    return result.stdout


def serialize_data(data: dict | None) -> str:
    """Serialize a body or params dict the way the app does before signing.

    Keys sorted in reverse alphabetical order, values concatenated (skipping
    None and the 'imageContent' key), then spaces stripped and lowercased.
    """
    if not data:
        return ""
    out = []
    for key in sorted(data.keys(), reverse=True):
        value = data.get(key)
        if value is not None and key != "imageContent":
            out.append(str(value))
    return "".join(out).replace(" ", "").lower()


class Signer:
    """Produces the signed headers for one request."""

    def __init__(self, hmac_key: str) -> None:
        if not hmac_key:
            raise ValueError(
                "An HMAC signing key is required. Extract it from your CatGenie "
                "app (see README) and pass it here."
            )
        self._key = hmac_key.encode("utf-8")

    def _hmac(self, message: str) -> str:
        return hmac.new(self._key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    def _enc_dec(self, timestamp_ms: int) -> str:
        if (timestamp_ms // 100) % 2 != 0:
            timestamp_ms += 100
        rand = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(7))
        pos = random.randint(0, len(rand))
        rand = rand[:pos] + "Z" + rand[pos:]
        plaintext = f"{timestamp_ms}-{rand}".encode()
        return base64.b64encode(_aes_encrypt(plaintext)).decode("utf-8")

    def headers(
        self,
        path: str,
        method: str = "GET",
        body: dict | None = None,
        params: dict | None = None,
    ) -> dict[str, str]:
        """Build the signed headers for a request to `path`."""
        timestamp_ms = int(time.time() * 1000)
        path_clean = path.lstrip("/")
        render_t = f"{path_clean}/{timestamp_ms}"

        body_part = serialize_data(body) if method.upper() in ("POST", "PUT", "PATCH") else ""
        params_part = serialize_data(params)

        return {
            "x-pm-en-dec": self._enc_dec(timestamp_ms),
            "x-pm-en-ver": "1.0.0",
            "x-render-t": render_t,
            "y-pm-sg-b": self._hmac(body_part + render_t),
            "y-pm-sg-p": self._hmac(params_part + render_t),
        }
