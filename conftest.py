# Makes `from src.recommender import ...` resolve and anchors the relative data
# paths in the tests, so `pytest` works from anywhere in the repo.
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
