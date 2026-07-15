# src/recommender/personas.py
# Labels are the segment names the dataset's own `segment` column already uses, so the
# app, the catalog and the notebook all describe a shopper the same way. The weight
# vectors are unchanged — PLAN.md B.4's expected top-3 table still holds.
PERSONAS = {
    "Photography-first": {
        "story": "Shoots daily and prints the results. Optics lead; screen matters; gaming doesn't.",
        "weights": {"camera": 0.50, "performance": 0.10, "battery": 0.20, "value": 0.20},
        "budget_max": 80000},
    "Gaming & performance": {
        "story": "Sustained high-refresh play. Raw performance plus the battery to survive a session.",
        "weights": {"camera": 0.10, "performance": 0.50, "battery": 0.30, "value": 0.10},
        "budget_max": 85000},
    "Value / essentials": {
        "story": "Tight budget, no compromises on the basics: value for money and all-day battery.",
        "weights": {"camera": 0.15, "performance": 0.20, "battery": 0.30, "value": 0.35},
        "budget_max": 20000},
    "Business / all-rounder": {
        "story": "Premium and reliable across the board; strong battery and camera, no weak axis.",
        "weights": {"camera": 0.25, "performance": 0.30, "battery": 0.25, "value": 0.20},
        "budget_max": 140000},
}
