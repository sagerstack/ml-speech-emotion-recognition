"""
Simple test to validate the testing framework setup.
"""


def test_basic_math():
    """A simple test to verify pytest is working."""
    assert 2 + 2 == 4


def test_string_operations():
    """Test string operations."""
    text = "ML Speech Emotion Recognition"
    assert "Speech" in text
    assert len(text) > 0


def test_list_operations():
    """Test list operations."""
    emotions = ["happy", "sad", "angry", "fear", "disgust", "neutral", "surprise"]
    assert len(emotions) == 7
    assert "happy" in emotions


def test_dictionary_operations():
    """Test dictionary operations."""
    config = {
        "app_name": "ML Speech Emotion Recognition API",
        "version": "1.0.0",
        "debug": False
    }

    assert config["app_name"] == "ML Speech Emotion Recognition API"
    assert config["version"] == "1.0.0"
    assert "debug" in config