"""Forwarding module for README compatibility.

Allows: `python -m orbitsuite.server.serve`
which internally executes the implementation in `src.server.serve`.
"""
from __future__ import annotations

from src.server.serve import run

if __name__ == "__main__":  # pragma: no cover
    run()
