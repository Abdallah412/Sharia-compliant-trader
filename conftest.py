"""
Root conftest — ensure external packages that may not be installed
in the test environment are mocked at import time.
"""

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Mock yfinance if it is not installed
# ---------------------------------------------------------------------------
if "yfinance" not in sys.modules:
    yf_mock = MagicMock()
    sys.modules["yfinance"] = yf_mock

# ---------------------------------------------------------------------------
# Mock optional imports that backend modules pull in at module level
# ---------------------------------------------------------------------------
for mod_name in ("requests", "telegram", "telegram.ext"):
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()
