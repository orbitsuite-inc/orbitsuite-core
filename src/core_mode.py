"""Explicit Core (toy) mode helpers.

Separated from feature_gates so that user code can import lightweight
runtime presentation utilities (banner) without pulling gating semantics.
"""
from __future__ import annotations

from src.feature_gates import is_core_minimal, require_pro  # re-export

BANNER_PRINTED: bool = False  # set once (server startup)


def core_banner() -> str:
    return (
        "OrbitSuite Core (toy mode) – OpenAI-only | demo=2 calls | no retries | no fallbacks | stdout only"
    )


__all__ = [
    "is_core_minimal",
    "require_pro",
    "core_banner",
    "BANNER_PRINTED",
]
