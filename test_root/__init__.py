# core/tests/__init__.py
"""
Tests package for OrbitSuite Core.

This package contains unit tests for the OrbitSuite Core framework.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

# Optional utilities for testing
def get_test_version() -> str:
    """Get the version of the tests package."""
    return "1.0.0-tests"