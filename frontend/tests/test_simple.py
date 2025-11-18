"""
Simple test to verify testing setup is working
"""

import pytest


def test_simple_assertion():
    """A simple test to verify the testing framework works"""
    assert True


def test_math_operations():
    """Test basic math operations"""
    assert 1 + 1 == 2
    assert 5 * 5 == 25
    assert 10 - 3 == 7


def test_string_operations():
    """Test string operations"""
    assert "hello" + " world" == "hello world"
    assert "test".upper() == "TEST"
    assert "PYTHON".lower() == "python"


@pytest.mark.parametrize("input_val,expected", [
    (1, 1),
    (2, 4),
    (3, 9),
    (4, 16),
    (5, 25)
])
def test_square_function(input_val, expected):
    """Test square function with parameters"""
    assert input_val ** 2 == expected


def test_imports():
    """Test that required modules can be imported"""
    import json
    import tempfile
    from pathlib import Path

    assert json is not None
    assert tempfile is not None
    assert Path is not None