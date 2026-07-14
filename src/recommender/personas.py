# src/recommender/personas.py
PERSONAS = {
    "Priya — Photography enthusiast": {
        "story": "24, shoots daily. Wants the best camera; screen matters; gaming doesn't.",
        "weights": {"camera": 0.50, "performance": 0.10, "battery": 0.20, "value": 0.20},
        "budget_max": 80000},
    "Arjun — Mobile gamer": {
        "story": "21, competitive gamer. Raw performance + battery for long sessions.",
        "weights": {"camera": 0.10, "performance": 0.50, "battery": 0.30, "value": 0.10},
        "budget_max": 85000},
    "Meera — Budget-conscious student": {
        "story": "19, saving hard. Value-for-money and all-day battery on a tight budget.",
        "weights": {"camera": 0.15, "performance": 0.20, "battery": 0.30, "value": 0.35},
        "budget_max": 20000},
    "Rahul — Business all-rounder": {
        "story": "34, professional. Balanced, premium, reliable; strong battery + camera.",
        "weights": {"camera": 0.25, "performance": 0.30, "battery": 0.25, "value": 0.20},
        "budget_max": 140000},
}
