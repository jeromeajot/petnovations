"""Unit tests for refresh-response token extraction."""

from __future__ import annotations

from conftest import load_module

tokenutil = load_module("tokenutil")


def test_find_access_token_primary_field():
    assert tokenutil.find_access_token({"token": "abc"}) == "abc"


def test_find_access_token_alternate_fields():
    assert tokenutil.find_access_token({"accessToken": "a"}) == "a"
    assert tokenutil.find_access_token({"access_token": "b"}) == "b"
    assert tokenutil.find_access_token({"jwt": "c"}) == "c"


def test_find_access_token_nested():
    assert tokenutil.find_access_token({"data": {"token": "deep"}}) == "deep"
    assert tokenutil.find_access_token({"result": {"accessToken": "deep2"}}) == "deep2"


def test_find_access_token_missing():
    assert tokenutil.find_access_token({"nope": "x"}) is None
    assert tokenutil.find_access_token({"token": ""}) is None
    assert tokenutil.find_access_token({"token": 123}) is None


def test_find_refresh_token():
    assert tokenutil.find_refresh_token({"refreshToken": "r"}) == "r"
    assert tokenutil.find_refresh_token({"refresh_token": "r2"}) == "r2"
    assert tokenutil.find_refresh_token({"data": {"refreshToken": "r3"}}) == "r3"
    assert tokenutil.find_refresh_token({"token": "only-access"}) is None
