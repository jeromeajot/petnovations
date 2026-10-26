"""Unit tests for the request signing scheme.

Uses a DUMMY 84-character secret — never a real credential. The algorithm was
verified against genuine captured traffic during development; these tests guard
against regressions.
"""

from __future__ import annotations

import base64
import hashlib
import hmac

from conftest import load_module

signing = load_module("signing")

# A dummy secret and its known-answer derivations (computed offline).
DUMMY_SECRET = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz0123456789ABCDEFGHIJKL"
)
EXPECTED_KEY = "Ytuvwxyz0123456789ABCDEFGHIJKLx3"
RENDER = "device/device/v2/1700000000000"
EXPECTED_RENDER_MAC = "9d9a915cce60c9ddf83332facf1407bbdb39cd41ddacd22345f824eb62ea1ffa"


def test_derive_hmac_key_production():
    assert signing.derive_hmac_key(DUMMY_SECRET) == EXPECTED_KEY
    assert len(signing.derive_hmac_key(DUMMY_SECRET)) == 32


def test_resolve_key_treats_84_chars_as_secret():
    assert signing.resolve_key(DUMMY_SECRET) == EXPECTED_KEY


def test_resolve_key_passes_through_final_key():
    assert signing.resolve_key(EXPECTED_KEY) == EXPECTED_KEY
    assert signing.resolve_key("  " + EXPECTED_KEY + "  ") == EXPECTED_KEY


def test_known_answer_mac():
    mac = hmac.new(EXPECTED_KEY.encode(), RENDER.encode(), hashlib.sha256).hexdigest()
    assert mac == EXPECTED_RENDER_MAC


def test_serialize_reverse_sorted_values_lowercased():
    out = signing.serialize_data({"b": "Hello World", "a": 2, "imageContent": "X", "z": None})
    # reverse key order z,b,a -> skip z(None) -> "Hello World" + "2" -> strip+lower
    assert out == "helloworld2"


def test_serialize_empty():
    assert signing.serialize_data(None) == ""
    assert signing.serialize_data({}) == ""


def test_headers_structure_and_determinism(monkeypatch):
    # Freeze time and randomness for a stable comparison.
    monkeypatch.setattr(signing.time, "time", lambda: 1700000000.0)
    monkeypatch.setattr(signing.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(signing.random, "randint", lambda a, b: 0)

    signer = signing.Signer(EXPECTED_KEY)
    headers = signer.headers(
        "device/device/v2", "GET", None, {"useFleetIndexAndGetRealConnectivity": "true"}
    )

    assert set(headers) == {"x-pm-en-dec", "x-pm-en-ver", "x-render-t", "y-pm-sg-b", "y-pm-sg-p"}
    assert headers["x-pm-en-ver"] == "1.0.0"
    assert headers["x-render-t"] == "device/device/v2/1700000000000"
    assert len(headers["y-pm-sg-b"]) == 64
    # body is empty on GET -> body signature is the mac over render_t alone
    assert headers["y-pm-sg-b"] == EXPECTED_RENDER_MAC
    # params signature includes the serialized "true"
    expected_p = hmac.new(
        EXPECTED_KEY.encode(), ("true" + "device/device/v2/1700000000000").encode(), hashlib.sha256
    ).hexdigest()
    assert headers["y-pm-sg-p"] == expected_p


def test_enc_dec_roundtrips_to_timestamp(monkeypatch):
    monkeypatch.setattr(signing.time, "time", lambda: 1700000000.0)
    monkeypatch.setattr(signing.random, "choice", lambda seq: seq[0])
    monkeypatch.setattr(signing.random, "randint", lambda a, b: 0)
    signer = signing.Signer(EXPECTED_KEY)
    enc = signer.headers("device/device/v2", "GET", None, None)["x-pm-en-dec"]

    # Decrypt and confirm it carries the (adjusted) millisecond timestamp.
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    dec = Cipher(algorithms.AES(signing._AES_KEY), modes.CBC(signing._AES_IV)).decryptor()
    padded = dec.update(base64.b64decode(enc)) + dec.finalize()
    plaintext = padded[: -padded[-1]].decode()  # strip PKCS7
    ts_str, _, rand = plaintext.partition("-")
    assert ts_str.startswith("1700000000")
    assert "Z" in rand


def test_signer_requires_key():
    import pytest

    with pytest.raises(ValueError):
        signing.Signer("")
