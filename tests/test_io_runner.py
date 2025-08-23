import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from src.io_runner import run_io

def test_io_runner():
    """Test the run_io function in io_runner.py."""
    try:
        run_io(root="test_root")
        # Validate that the function executes without raising exceptions
        # Add meaningful checks if the function has a return value or side effects
    except Exception as e:
        pytest.fail(f"IO runner raised an exception: {e}")
