#!/usr/bin/env python3
"""Standalone CatGenie checker — full flow, no extra packages needed.

Given your signing key (or 84-char secret) and your long-lived refresh token,
this refreshes an access token and reads your CatGenie, printing cycle state and
any error. AES is done via the openssl CLI, so stock system Python works.

Usage:

    python3 verify_catgenie.py --key "<your-32-char-signing-key>" \
                               --refresh-token "eyJ..."

    # or derive the key from the 84-char keychain secret:
    python3 verify_catgenie.py --secret "Cnwtyp59...Fwt" --refresh-token "eyJ..."

Env vars CATGENIE_KEY / CATGENIE_SECRET / CATGENIE_REFRESH also work.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import random
import string
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "https://iot.petnovations.com"
AES_KEY = b"P-3Rp6d81Kw9a3Z-CyvWH0WXRieyITk6"
AES_IV = b"\x00" * 16

DEVICES_URL_PATH = "device/device/v2"
DEVICES_PARAMS = {"useFleetIndexAndGetRealConnectivity": "true"}
REFRESH_URL_PATH = "facade/v1/mobile-user/refreshToken/v2"
REFRESH_SIGN_PATH = "mobile-user/refreshToken/v2"


def derive_key(secret: str) -> str:
    """Production derivation: 'Yt' + secret[56:84] + 'x3'."""
    return "Yt" + secret[56:84] + "x3"


def aes_b64(plaintext: bytes) -> str:
    pad = 16 - (len(plaintext) % 16)
    padded = plaintext + bytes([pad]) * pad
    out = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-K", AES_KEY.hex(), "-iv", AES_IV.hex(), "-nosalt"],
        input=padded, capture_output=True, check=True,
    )
    return base64.b64encode(out.stdout).decode()


def serialize(data: dict | None) -> str:
    if not data:
        return ""
    out = []
    for key in sorted(data.keys(), reverse=True):
        v = data.get(key)
        if v is not None and key != "imageContent":
            out.append(str(v))
    return "".join(out).replace(" ", "").lower()


def signed_headers(key: str, sign_path: str, method: str, body: dict | None, params: dict | None) -> dict:
    ts = int(time.time() * 1000)
    render_t = f"{sign_path.lstrip('/')}/{ts}"
    ts_enc = ts + 100 if (ts // 100) % 2 != 0 else ts
    rand = "".join(random.choice(string.ascii_letters + string.digits) for _ in range(7))
    pos = random.randint(0, len(rand))
    rand = rand[:pos] + "Z" + rand[pos:]
    body_part = serialize(body) if method in ("POST", "PUT", "PATCH") else ""

    def mac(msg: str) -> str:
        return hmac.new(key.encode(), msg.encode(), hashlib.sha256).hexdigest()

    return {
        "x-pm-en-dec": aes_b64(f"{ts_enc}-{rand}".encode()),
        "x-pm-en-ver": "1.0.0",
        "x-render-t": render_t,
        "y-pm-sg-b": mac(body_part + render_t),
        "y-pm-sg-p": mac(serialize(params) + render_t),
    }


def http(method: str, url: str, headers: dict, body: dict | None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.status, resp.read().decode(errors="replace")
    except urllib.error.HTTPError as err:
        return err.code, err.read().decode(errors="replace")


def refresh(key: str, refresh_token: str) -> tuple[str | None, str]:
    body = {"refreshToken": refresh_token}
    headers = signed_headers(key, REFRESH_SIGN_PATH, "POST", body, None)
    headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
    })
    status, text = http("POST", f"{BASE_URL}/{REFRESH_URL_PATH}", headers, body)
    if status != 200:
        print(f"Refresh failed: HTTP {status}\n{text[:400]}")
        return None, text
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("Refresh response was not JSON:\n", text[:400])
        return None, text
    print("Refresh response keys:", list(data.keys()))
    for k in ("token", "accessToken", "access_token", "jwt", "authToken", "idToken"):
        if isinstance(data.get(k), str) and data[k]:
            return data[k], text
    for w in ("data", "result", "payload"):
        if isinstance(data.get(w), dict):
            for k in ("token", "accessToken", "access_token"):
                if isinstance(data[w].get(k), str):
                    return data[w][k], text
    print("Could not find an access token field in the refresh response.")
    return None, text


def get_devices(key: str, token: str):
    url = f"{BASE_URL}/{DEVICES_URL_PATH}?" + urllib.parse.urlencode(DEVICES_PARAMS)
    headers = signed_headers(key, DEVICES_URL_PATH, "GET", None, DEVICES_PARAMS)
    headers.update({
        "Content-Type": "application/json",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Authorization": f"Bearer {token}",
    })
    return http("GET", url, headers, None)


STATE = {0: "Idle", 1: "Cleaning", 2: "Paused"}


def summarize(payload: str) -> None:
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        print("Response was not JSON:\n", payload[:800]); return
    things = data.get("thingList")
    if things is None:
        print("No 'thingList'. Raw:\n", json.dumps(data, indent=2)[:1200]); return
    print(f"\nFound {len(things)} device(s):\n")
    for dev in things:
        op = dev.get("operationStatus", {}) or {}
        state = STATE.get(op.get("state"), "Unknown")
        err = op.get("error")
        print(f"  {dev.get('name','?')}")
        print(f"    firmware    : {dev.get('fwVersion','?')}")
        print(f"    online      : {dev.get('reportedStatus','?')}")
        print(f"    cycle       : {state}" + (f" ({op.get('progress')}%)" if state == "Cleaning" else ""))
        print(f"    error       : {err if err not in (None,0,'0') else 'none'}")
        print(f"    cartridge   : {dev.get('remainingSaniSolution','?')} cycles left")
        print(f"    last clean  : {dev.get('lastClean','?')}\n")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--key", default=os.environ.get("CATGENIE_KEY", ""))
    p.add_argument("--secret", default=os.environ.get("CATGENIE_SECRET", ""))
    p.add_argument("--refresh-token", default=os.environ.get("CATGENIE_REFRESH", ""))
    p.add_argument("--token", default="", help="Optional: an access token, to skip refresh")
    args = p.parse_args()

    key = args.key.strip() or (derive_key(args.secret.strip()) if args.secret.strip() else "")
    if not key:
        print("ERROR: provide --key or --secret.", file=sys.stderr); return 2
    print(f"Signing key: {key}  (len {len(key)})")

    token = args.token.strip()
    if not token:
        if not args.refresh_token.strip():
            print("ERROR: provide --refresh-token (or --token).", file=sys.stderr); return 2
        print("Refreshing access token...")
        token, _ = refresh(key, args.refresh_token.strip())
        if not token:
            return 1
        print("Got access token.")

    status, body = get_devices(key, token)
    print(f"\nGET device/device/v2 -> HTTP {status}")
    if status == 200:
        summarize(body)
        print("SUCCESS: signing, refresh, and read all work.")
        return 0
    if status in (401, 403):
        print("Auth rejected. If signing were wrong you'd see a 400; a 401 means the token/key pair was not accepted.")
    print("Raw:", body[:500])
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
