"""Configuration and fixtures for infrastructure integration tests."""

import sys
from pathlib import Path

import pytest

# Import UltraEnsembleModel so it's available when unpickling v3/v4 models
try:
    # Try to import from the app
    from app.infrastructure.model.ultra_ensemble import UltraEnsembleModel

    # Make it available in __main__ for pickle
    sys.modules["__main__"].UltraEnsembleModel = UltraEnsembleModel
except ImportError:
    # If UltraEnsembleModel doesn't exist or can't be imported, skip real model tests
    pass


@pytest.fixture
def skip_if_models_not_loadable():
    """Skip test if real models can't be loaded due to pickle issues."""
    try:
        from app.infrastructure.model.ultra_ensemble import UltraEnsembleModel

        return False
    except ImportError:
        pytest.skip("UltraEnsembleModel not available for loading real models")
