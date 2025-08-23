"""Core feature gating utilities (toy mode).

This module lives in open-core to provide a stable import surface for any
future gating logic. It intentionally hard-codes the minimal edition status
so that attempts to enable premium features are deterministic and auditable.

Rules:
  • Core is OpenAI-only (no local LLM adapters, no webhooks, no autosync).
  • No retries / fallbacks / advanced memory in Core.
  • Any access to a Pro/Enterprise feature MUST raise a standardized error.
"""
from __future__ import annotations

CORE_MINIMAL: bool = True  # immutable flag; do not mutate at runtime


def is_core_minimal() -> bool:
    """Return True indicating this build is the Core (open) edition."""
    return True


def require_pro(feature: str) -> None:
    """Raise for a Pro/Enterprise-only feature.

    The message prefix "PRO_FEATURE:" is machine-parsable so the web UI or
    clients can strip / surface upgrade hints without brittle parsing.
    """
    raise RuntimeError(
        f"PRO_FEATURE: '{feature}' requires Pro/Enterprise. Core is OpenAI-only (no local LLMs, webhooks, autosync, retries, fallbacks, or advanced memory)."
    )


__all__ = ["CORE_MINIMAL", "is_core_minimal", "require_pro"]
