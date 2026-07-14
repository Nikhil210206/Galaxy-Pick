# tests/test_scoring.py
import pandas as pd
from src.recommender import scoring


def test_scores_bounded_on_catalog():
    df = pd.read_csv("data/processed/phones.csv")
    for c in ["camera_score", "performance_score", "battery_score", "value_score"]:
        assert df[c].between(0, 10).all()


def test_camera_flagship_beats_budget():
    assert scoring.camera_score(200, "S-Ultra") > scoring.camera_score(50, "A")


def test_performance_monotonic_in_tier():
    assert scoring.performance_score("Snapdragon 8 Elite", 8, 120) > \
           scoring.performance_score("Dimensity 6300", 8, 120)


def test_camera_ranks_by_optics_not_megapixels():
    """Same 50MP spec, very different cameras — optics tier must decide."""
    assert scoring.camera_score(50, "S") > scoring.camera_score(50, "A") \
           > scoring.camera_score(50, "M") >= scoring.camera_score(50, "F")


def test_camera_discriminates_across_the_catalog():
    """A criterion that barely varies can't influence a weighted sum."""
    df = pd.read_csv("data/processed/phones.csv")
    assert df["camera_score"].max() - df["camera_score"].min() >= 4.0
