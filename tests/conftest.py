"""Test helpers.

The integration package imports Home Assistant in its ``__init__``, so we load
the leaf modules under test directly from their files. This keeps the signing
and token unit tests fast and dependency-free (no Home Assistant needed).
"""

from __future__ import annotations

import importlib.util
import pathlib

_PKG = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "petnovations"


def load_module(name: str):
    """Load custom_components/petnovations/<name>.py as a standalone module."""
    path = _PKG / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"petnov_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module
