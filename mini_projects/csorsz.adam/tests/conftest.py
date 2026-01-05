import sys
from pathlib import Path

# Ensure the package root (mini_projects/csorsz.adam) is on sys.path for pytest
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
