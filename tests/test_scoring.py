# tests/test_scoring.py
import pandas as pd
from src.recommender import scoring

Y = scoring.CATALOG_YEAR


def test_scores_bounded_on_catalog():
    df = pd.read_csv("data/processed/phones.csv")
    for c in ["camera_score", "performance_score", "battery_score", "value_score"]:
        assert df[c].between(0, 10).all()


def test_camera_flagship_beats_budget():
    assert scoring.camera_score(200, "S-Ultra", Y) > scoring.camera_score(50, "A", Y)


def test_performance_monotonic_in_tier():
    assert scoring.performance_score("Snapdragon 8 Elite", 8, 120) > \
           scoring.performance_score("Dimensity 6300", 8, 120)


def test_camera_ranks_by_optics_not_megapixels():
    """Same 50MP spec, very different cameras — optics tier must decide."""
    assert scoring.camera_score(50, "S", Y) > scoring.camera_score(50, "A", Y) \
           > scoring.camera_score(50, "M", Y) >= scoring.camera_score(50, "F", Y)


def test_camera_discriminates_across_the_catalog():
    """A criterion that barely varies can't influence a weighted sum."""
    df = pd.read_csv("data/processed/phones.csv")
    assert df["camera_score"].max() - df["camera_score"].min() >= 4.0


# --- headroom -------------------------------------------------------------
# The tier tables used to overflow 10.0 and get flattened by _clamp, so a 2024 Snapdragon
# 8 Gen3 and a 2026 8 Elite Gen2 both scored exactly 10.0 and the WSM could not separate
# four chipset generations. These pin the headroom that keeps the signal alive.

def test_top_flagship_lands_on_ten_without_clamping():
    """The best possible phone should reach 10.0 by arithmetic, not by hitting a ceiling."""
    best_chipset = max(scoring.CHIPSET_TIER.values())
    assert round(best_chipset + scoring.RAM_MAX + 0.3, 6) == 10.0
    assert round(max(scoring.SERIES_OPTICS.values()) + 1.0 + scoring.generation_bonus(Y), 6) == 10.0


def test_clamp_never_binds_on_the_real_catalog():
    """If anything hits 0 or 10 by clamping rather than by construction, a tier has
    outgrown its headroom and generations are being flattened again."""
    df = pd.read_csv("data/processed/phones.csv")
    for chipset, ram, hz in zip(df.chipset, df.ram_gb, df.refresh_rate_hz):
        raw = (scoring.CHIPSET_TIER.get(chipset, scoring.CHIPSET_DEFAULT)
               + max(scoring.RAM_MIN, min(scoring.RAM_MAX, (ram - 8) * scoring.RAM_STEP))
               + (0.3 if hz >= 120 else 0.0))
        assert 0.0 <= round(raw, 6) <= 10.0, f"{chipset}/{ram}GB overflows to {raw}"


def test_a_chipset_generation_outweighs_a_ram_bump():
    """8 Elite + 8GB must beat 8 Gen3 + 12GB. The reverse let a 2024 S24 Ultra outscore a
    2025 S25 on 'performance' purely on RAM."""
    assert scoring.performance_score("Snapdragon 8 Elite", 8, 120) > \
           scoring.performance_score("Snapdragon 8 Gen3", 12, 120)


def test_camera_separates_generations_of_the_same_series():
    """Identical optics tier and megapixels, two years apart — the model must still rank
    them, or 'best camera' returns whichever row happens to come first in the CSV."""
    a = scoring.camera_score(200, "S-Ultra", 2024)
    b = scoring.camera_score(200, "S-Ultra", 2025)
    c = scoring.camera_score(200, "S-Ultra", 2026)
    assert a < b < c


def test_generation_bonus_does_not_reward_the_future():
    """A projected 2027 row must not out-score the current year just for being later."""
    assert scoring.generation_bonus(Y + 5) == scoring.generation_bonus(Y)


# --- depreciation ---------------------------------------------------------

def test_current_year_models_sit_at_launch_price():
    assert scoring.current_price_inr(139999, Y, "S-Ultra") == 139999


def test_older_flagships_are_cheaper_than_their_successors():
    """The bug that started this: S24 Ultra and S25 Ultra both listed at ₹1,47,559."""
    s24 = scoring.current_price_inr(147559, 2024, "S-Ultra")
    s25 = scoring.current_price_inr(147559, 2025, "S-Ultra")
    s26 = scoring.current_price_inr(139999, 2026, "S-Ultra")
    assert s24 < s25 < s26


def test_flagships_depreciate_faster_than_budget_phones():
    assert scoring.current_price_inr(50000, 2024, "S") < scoring.current_price_inr(50000, 2024, "M")


def test_depreciated_price_never_exceeds_launch_price():
    df = pd.read_csv("data/processed/phones.csv")
    assert (df["price_inr"] <= df["launch_price_inr"]).all()
