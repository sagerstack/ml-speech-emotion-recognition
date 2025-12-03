"""Conftest for models unit tests to ensure proper imports."""

import sys
from pathlib import Path

# Ensure backend root is in path for models imports
# This runs BEFORE test files are imported
BACKEND_ROOT = Path(__file__).resolve().parents[3]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
