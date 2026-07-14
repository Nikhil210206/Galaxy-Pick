# src/recommender/config.py — paths + the Gemini feature flag.
#
# Deterministic-first: GEMINI_ENABLED is True only when a key is actually present.
# Everything downstream must still work when it is False.
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:  # python-dotenv absent or .env unreadable — offline mode is the default anyway
    pass

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
CURATED_SEED_CSV = DATA_RAW / "curated_seed.csv"
PHONES_CSV = DATA_PROCESSED / "phones.csv"

GEMINI_API_KEY = (os.getenv("GEMINI_API_KEY") or "").strip()
GEMINI_ENABLED = bool(GEMINI_API_KEY)
GEMINI_MODEL = "gemini-1.5-flash"   # free tier
