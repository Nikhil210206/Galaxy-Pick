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
    """A projected pick must never be presented as confirmed fact.

    Built from a synthetic row on purpose: the catalog has no projections today (the 2026
    line shipped and its specs were confirmed), but the disclosure mechanism must keep
    working for whatever gets projected next — a catalog with nothing to warn about is not
    evidence that the warning works.
    """
    row = pd.Series({"model_name": "Galaxy S27 Ultra", "launch_year": 2027, "price_inr": 149999,
                     "camera_score": 9.0, "performance_score": 9.0, "battery_score": 8.0,
                     "value_score": 1.0, "spec_source": "mock"})
    w = {f: 0.25 for f in nlp_parse.FACTORS}
    assert "projected" in explain.reason(row, w)


def test_real_rows_are_not_labelled_projected():
    """The flip side: now that the 2026 line is confirmed, it must NOT carry the warning."""
    df = pd.read_csv("data/processed/phones.csv")
    row = df[df["model_name"] == "Galaxy S26 Ultra"].iloc[0]
    w = {f: 0.25 for f in nlp_parse.FACTORS}
    assert "projected" not in explain.reason(row, w)


# --- negation -------------------------------------------------------------
# "I dont mind the budget" used to BOOST value to 0.34 — tied with camera — because the
# keyword "budget" is present and nothing looked to its left. The shopper said the exact
# opposite of what the parser heard.

def test_dismissed_factor_is_not_boosted():
    out = nlp_parse.parse_rules("I dont mind the budget, I want the best camera in samsung mobile.")
    assert "value" not in out["must_haves"]
    assert out["weights"]["camera"] > out["weights"]["value"]


def test_dismissal_does_not_swallow_the_next_clause():
    """The dismissal governs its own clause only — the camera ask behind the comma stands."""
    out = nlp_parse.parse_rules("I dont mind the budget, I want the best camera in samsung mobile.")
    assert out["must_haves"] == ["camera"]


def test_money_no_object_suppresses_value_only():
    out = nlp_parse.parse_rules("best camera, money is no object")
    assert out["must_haves"] == ["camera"]


def test_and_continues_a_dismissal():
    out = nlp_parse.parse_rules("I dont care about camera and battery, just performance")
    assert out["must_haves"] == ["performance"]


def test_but_ends_a_dismissal():
    out = nlp_parse.parse_rules("I dont mind the price but camera matters")
    assert out["must_haves"] == ["camera"]


def test_plain_budget_ask_still_boosts_value():
    """Negation handling must not break the ordinary case."""
    assert "value" in nlp_parse.parse_rules("budget phone under 15k")["must_haves"]


# --- budget phrasing ------------------------------------------------------
# The parser only understood "under/below/up to/within". "budget phone around 20,000" parsed
# to budget_max=None, so there was no budget at all: the full catalog stayed in the pool and
# a performance-weighted request returned a ₹1.4L S26 Ultra to someone asking for ₹20k.

def test_around_an_amount_is_a_band_not_a_ceiling():
    """'around 20,000' must not become 'up to 20,000' — with a value-weighted request that
    returns a ₹9,000 phone, which is the opposite of what the shopper asked for."""
    out = nlp_parse.parse_rules("I want a budget phone around 20,000 with good performance")
    assert out["budget_min"] == 17000 and out["budget_max"] == 23000


def test_ceiling_phrasings_set_only_a_maximum():
    for text in ["under 20000", "below 20k", "up to 20k", "within 20k", "max 25k",
                 "budget of 20000", "₹20,000", "Rs 20000", "20k budget"]:
        out = nlp_parse.parse_rules(text)
        assert out["budget_max"] is not None, f"{text!r} -> no budget"
        assert out["budget_min"] is None, f"{text!r} -> unexpected floor"


def test_target_phrasings_all_produce_the_same_band():
    for text in ["around 20k", "about 20k", "approximately 20000", "roughly 20k", "near 20k"]:
        out = nlp_parse.parse_rules(text)
        assert (out["budget_min"], out["budget_max"]) == (17000, 23000), text


def test_megapixels_are_not_mistaken_for_a_budget():
    """The reason bare numbers are never matched: '200MP' would become a ₹2,00,000 budget."""
    for text in ["200MP camera phone", "50MP camera", "a 108MP shooter"]:
        out = nlp_parse.parse_rules(text)
        assert out["budget_max"] is None, f"{text!r} invented a budget"


def test_the_b4_free_text_case_is_unchanged():
    """PLAN.md B.4 pins 'photography under ₹50k' — a ceiling, with no floor."""
    out = nlp_parse.parse_rules("photography under ₹50k")
    assert out["budget_max"] == 50000 and out["budget_min"] is None
