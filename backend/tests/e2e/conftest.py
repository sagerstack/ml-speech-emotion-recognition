"""Configuration and fixtures for E2E tests."""

import sys

# Import UltraEnsembleModel so it's available when unpickling v3/v4 models
try:
    from app.infrastructure.model.ultra_ensemble import UltraEnsembleModel

    # Make it available in __main__ for pickle
    sys.modules["__main__"].UltraEnsembleModel = UltraEnsembleModel
except ImportError:
    # If UltraEnsembleModel doesn't exist, tests might fail when loading v4 model
    pass
