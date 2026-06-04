"""Configuration settings for MedChat backend."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = BASE_DIR / "data" / "datathuoc_enriched.json"

CONFIDENCE_THRESHOLD = 0.72
FUZZY_ACCEPT_SCORE = 55  # Lowered for brand name matching
FUZZY_REVIEW_SCORE = 40