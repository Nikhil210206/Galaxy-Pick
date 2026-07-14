# src/recommender/scoring.py — deterministic, explainable spec → 0–10 scores.
CHIPSET_TIER = {
    "Snapdragon 8 Elite Gen2": 9.7,   # 2026 (mock)
    "Snapdragon 8 Elite": 9.5, "Snapdragon 8 Gen3": 9.2, "Snapdragon 8 Gen2": 8.9,
    "Exynos 2500": 8.7,               # 2026 (mock)
    "Exynos 2400": 8.5, "Exynos 2400e": 8.1,
    "Snapdragon 7 Gen1": 6.3, "Exynos 1680": 6.2,   # 1680 = 2026 (mock)
    "Exynos 1580": 6.0, "Exynos 1480": 5.6, "Snapdragon 6 Gen3": 5.4,
    "Exynos 1380": 5.2, "Exynos 1280": 4.6,
    "Dimensity 6400": 4.4,            # 2026 (mock)
    "Dimensity 6300": 4.2, "Dimensity 6100+": 4.0,
}
CHIPSET_DEFAULT = 4.0

# Optics tier is the PRIMARY camera signal, not megapixels. Megapixel count is a
# famously poor proxy for image quality — a Galaxy S24 and a budget F15 are both
# "50MP" but are not remotely the same camera. What actually differs is sensor
# size, OIS, zoom hardware and ISP, and those track the series tier. Scoring on MP
# alone made every phone under ₹1,39,999 camera-identical, which collapsed the WSM
# (see the notebook's EDA finding 3).
SERIES_OPTICS = {"S-Ultra": 9.0, "S": 8.0, "Z-Fold": 7.6, "S-FE": 7.2,
                 "Z-Flip": 7.0, "A": 5.8, "M": 5.2, "F": 5.0}
SERIES_OPTICS_DEFAULT = 5.0


def _clamp(x, lo=0.0, hi=10.0):
    return round(float(max(lo, min(hi, x))), 1)


def camera_score(rear_camera_mp, series):
    mp = rear_camera_mp
    base = SERIES_OPTICS.get(series, SERIES_OPTICS_DEFAULT)
    mp_bonus = 0.0 if mp <= 12 else 0.2 if mp <= 50 else 0.4 if mp <= 64 else 0.7 if mp <= 108 else 1.0
    return _clamp(base + mp_bonus)


def performance_score(chipset, ram_gb, refresh_rate_hz):
    base = CHIPSET_TIER.get(chipset, CHIPSET_DEFAULT)
    ram_bonus = max(-0.3, min(0.6, (ram_gb - 8) * 0.15))
    refresh_bonus = 0.3 if refresh_rate_hz >= 120 else 0.0
    return _clamp(base + ram_bonus + refresh_bonus)


def battery_score(battery_mah, charging_w, screen_size_inch):
    base = 5.0 + (battery_mah - 3700) / 2300.0 * 4.5
    charge_bonus = 0.6 if charging_w >= 45 else 0.0
    screen_penalty = -0.4 if screen_size_inch >= 7.0 else 0.0
    return _clamp(base + charge_bonus + screen_penalty)


def value_score_column(df):
    # emergent: spec-points per ₹10k, min-max scaled to 0–10 across the catalog
    raw = (df["camera_score"] + df["performance_score"] + df["battery_score"]) / (df["price_inr"] / 10000.0)
    lo, hi = raw.min(), raw.max()
    return ((raw - lo) / (hi - lo) * 10).round(1)


# Plain-English summary of the logic above — printed in the notebook (brief Step 6
# requires showing the logic, not just the numbers).
LOGIC_SUMMARY = """\
camera_score:      series optics tier (Ultra 9.0 → S 8.0 → Fold 7.6 → FE 7.2 → Flip 7.0
                   → A 5.8 → M 5.2 → F 5.0), + a small megapixel bonus (50→+0.2, 200→+1.0).
                   Optics leads because MP ≠ image quality: sensor size, OIS, zoom and ISP
                   are what differ, and they track the series. Still a transparent heuristic.
performance_score: chipset tier (flagship Snapdragon/Exynos high, entry Dimensity/Exynos low)
                   + RAM adjustment (6/8/12 GB → −0.3/0/+0.6) + 0.3 for 120 Hz.
battery_score:     capacity scaled 3700→6000 mAh onto 5.0→9.5,
                   + 0.6 for ≥45 W charging, − 0.4 for big ≥7" foldable screens.
value_score:       emergent — (camera+performance+battery) per ₹10,000, min-max scaled 0–10.
                   Budget M/F models score high; flagships score low.
"""
