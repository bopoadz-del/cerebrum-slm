"""Test path setup — repo scripts and the collect tooling are importable."""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
for sub in ("scripts", "scripts/collect"):
    p = str(_ROOT / sub)
    if p not in sys.path:
        sys.path.insert(0, p)
