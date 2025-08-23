import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))
import pytest
from src.demo import main

def test_demo_main():
    """Test the main function in demo.py."""
    try:
        main()
        # Validate that the function executes without raising exceptions
        # Add meaningful checks if the function has a return value or side effects
    except Exception as e:
        pytest.fail(f"Demo main raised an exception: {e}")
