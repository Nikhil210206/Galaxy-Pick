# tests/test_nlp_parse.py — the fallback drill (PLAN.md Phase 4 acceptance), as tests.
# These all exercise the deterministic path: no key, no network.
import pandas as pd
import pytest

from src.recommender import nlp_parse, wsm, explain


def _sums_to_one(weights):
    return abs(sum(weights.values()) - 1.0) < 1e-6


@pytest.mark.parametrize("text", ["", "   ", "asdkjhasd qwe zzz", "!!!", "the a of"])
def test_bad_input_gives_neutral_weights_and_no_crash(text):
    out = nlp_parse.parse_rules(text)
    assert _sums_to_one(out["weights"])
    assert out["weights"] == {f: 0.25 for f in nlp_parse.FACTORS}
    assert out["budget_max"] is None and out["form_factor"] == "any"


def test_keyword_boost_favours_named_factor():
    out = nlp_parse.parse_rules("I want the best camera for photography")
    assert _sums_to_one(out["weights"])
    assert out["weights"]["camera"] == max(out["weights"].values())
    assert "camera" in out["must_haves"]


@pytest.mark.parametrize("text,expected", [
    ("photography under ₹50k", 50000),
    ("gaming phone below 60000", 60000),
    ("something under 30k", 30000),
    ("phone within rs 1,20,000", 120000),
    ("no budget mentioned", None),
])
def test_budget_extraction(text, expected):
    assert nlp_parse.parse_rules(text)["budget_max"] == expected


def test_budget_is_clamped_to_catalog_range():
    assert nlp_parse.parse_rules("phone under 900k")["budget_max"] == nlp_parse.BUDGET_MAX
    assert nlp_parse.parse_rules("phone under 1000")["budget_max"] == nlp_parse.BUDGET_MIN


@pytest.mark.parametrize("text,expected", [
    ("a compact phone", "compact"),
    ("small phone for one hand", "compact"),
    ("a foldable please", "foldable"),
    ("flip phone under 100k", "foldable"),
    ("any phone", "any"),
])
def test_form_factor_detection(text, expected):
    assert nlp_parse.parse_rules(text)["form_factor"] == expected


def test_photography_under_50k_is_camera_weighted_and_in_budget():
    """The exact demo query from the PLAN.md acceptance criteria."""
    df = pd.read_csv("data/processed/phones.csv")
    parsed = nlp_parse.parse_rules("photography under ₹50k")
    out = wsm.recommend(df, parsed["weights"], budget_max=parsed["budget_max"], top_n=3)

    assert parsed["weights"]["camera"] == max(parsed["weights"].values())
    assert (out["price_inr"] <= 50000).all()
    assert len(out) == 3


def test_reason_works_offline_for_every_top_pick():
    df = pd.read_csv("data/processed/phones.csv")
    parsed = nlp_parse.parse_rules("best camera under 50k")
    out = wsm.recommend(df, parsed["weights"], budget_max=parsed["budget_max"], top_n=3)
    close = explain.is_close_call(out)

    for _, row in out.iterrows():
        text = explain.reason(row, parsed["weights"], close_call=close)
        assert text and "₹" in text and "/10" in text


def test_mock_rows_are_disclosed_in_the_reason():
    """A 2026 pick must never be presented as confirmed fact."""
    df = pd.read_csv("data/processed/phones.csv")
    row = df[df["spec_source"] == "mock"].iloc[0]
    w = {f: 0.25 for f in nlp_parse.FACTORS}
    assert "projected" in explain.reason(row, w)
