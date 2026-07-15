# tests/test_wsm.py
import pandas as pd
from src.recommender import wsm, personas


def test_persona_weights_sum_to_one():
    for p in personas.PERSONAS.values():
        assert abs(sum(p["weights"].values()) - 1.0) < 1e-9


def test_worked_example_equals_7_5():
    df = pd.DataFrame([{"camera_score": 9, "performance_score": 6, "battery_score": 7, "value_score": 5}])
    w = {"camera": 0.5, "performance": 0.1, "battery": 0.2, "value": 0.2}
    assert float(wsm.match_scores(df, w).iloc[0]) == 7.5


def test_recommend_respects_budget():
    df = pd.read_csv("data/processed/phones.csv")
    w = {"camera": 0.25, "performance": 0.25, "battery": 0.25, "value": 0.25}
    out = wsm.recommend(df, w, budget_max=20000, top_n=3)
    assert (out["price_inr"] <= 20000).all() and len(out) <= 3


# --- normalization guards -------------------------------------------------
# Without normalize_scores(), value_score (which spans the full 0-10) outvoted
# camera_score (which spans ~3) even at 2.5x less weight, and every persona
# collapsed onto the cheapest phone. These pin that behaviour down.

def test_normalize_puts_criteria_on_a_common_scale():
    df = pd.read_csv("data/processed/phones.csv")
    nd = wsm.normalize_scores(df)
    for c in wsm.SCORE_COLS:
        assert nd[c].min() == 0.0 and nd[c].max() == 10.0


def test_normalize_is_neutral_when_a_criterion_cannot_discriminate():
    """All options tied on a criterion → it must not tip the ranking."""
    df = pd.DataFrame([
        {"camera_score": 7.0, "performance_score": 4.0, "battery_score": 9.0, "value_score": 8.0},
        {"camera_score": 7.0, "performance_score": 9.0, "battery_score": 5.0, "value_score": 2.0},
    ])
    assert (wsm.normalize_scores(df)["camera_score"] == wsm.NEUTRAL_NORM).all()


def test_personas_produce_distinct_recommendations():
    """The whole point of personas: different priorities → different phones."""
    df = pd.read_csv("data/processed/phones.csv")
    tops = {}
    for name, p in personas.PERSONAS.items():
        out = wsm.recommend(df, p["weights"], budget_max=p["budget_max"], top_n=3)
        tops[name] = out.iloc[0]["model_name"]
    assert len(set(tops.values())) > 1, f"every persona returned the same phone: {tops}"


def test_camera_persona_picks_the_best_camera_in_budget():
    """Photography-first weights camera 0.50 — its #1 must be a camera leader, not the cheapest."""
    df = pd.read_csv("data/processed/phones.csv")
    p = personas.PERSONAS["Photography-first"]
    out = wsm.recommend(df, p["weights"], budget_max=p["budget_max"], top_n=3)
    best_available = df[df["price_inr"] <= p["budget_max"]]["camera_score"].max()
    assert out.iloc[0]["camera_score"] == best_available


def test_budget_persona_still_picks_on_value():
    df = pd.read_csv("data/processed/phones.csv")
    p = personas.PERSONAS["Value / essentials"]
    out = wsm.recommend(df, p["weights"], budget_max=p["budget_max"], top_n=3)
    assert out.iloc[0]["value_score"] >= 9.0


# --- hard filters ---------------------------------------------------------
# recommend() used to fall back to the whole catalog when the pool emptied, so an
# unsatisfiable filter returned phones that violated it. These pin the honest behaviour.

NEUTRAL_W = {"camera": 0.25, "performance": 0.25, "battery": 0.25, "value": 0.25}


def test_hard_filters_are_never_violated():
    df = pd.read_csv("data/processed/phones.csv")
    out = wsm.recommend(df, NEUTRAL_W, filters={"min_ram_gb": 12, "min_storage_gb": 256}, top_n=5)
    assert len(out) > 0
    assert (out["ram_gb"] >= 12).all() and (out["storage_gb"] >= 256).all()


def test_unsatisfiable_filter_returns_empty_not_the_whole_catalog():
    df = pd.read_csv("data/processed/phones.csv")
    out = wsm.recommend(df, NEUTRAL_W, filters={"min_ram_gb": 999})
    assert len(out) == 0
    assert "match_score" in out.columns      # shape stays stable for callers


def test_binding_filters_names_what_to_relax():
    df = pd.read_csv("data/processed/phones.csv")
    # 12GB RAM exists, and cheap phones exist, but no 12GB phone is under ₹20k.
    filters = {"min_ram_gb": 12}
    assert wsm.recommend(df, NEUTRAL_W, budget_max=20000, filters=filters).empty
    assert set(wsm.binding_filters(df, budget_max=20000, filters=filters)) == {"budget_max", "min_ram_gb"}


def test_binding_filters_is_empty_when_results_exist():
    df = pd.read_csv("data/processed/phones.csv")
    assert wsm.binding_filters(df, budget_max=200000) == []


def test_exclude_projections_drops_every_mock_row():
    """Filters on spec_source, NOT on launch_year.

    These were the same thing while every 2026 row was a projection. They aren't any more —
    the 2026 line shipped with confirmed specs — and conflating them would hide real,
    current phones from anyone who ticked the box.
    """
    df = pd.read_csv("data/processed/phones.csv")
    mock = pd.DataFrame([{**df.iloc[0].to_dict(), "model_name": "Galaxy S27 Ultra",
                          "launch_year": 2026, "spec_source": "mock"}])
    pool = pd.concat([df, mock], ignore_index=True)

    out = wsm.recommend(pool, NEUTRAL_W, filters={"exclude_projections": True}, top_n=len(pool))
    assert len(out) == len(df)
    assert (out["spec_source"] != "mock").all()
    assert (out["launch_year"] == 2026).any(), "confirmed 2026 phones must survive the filter"


# --- tie-breaking ---------------------------------------------------------
# When every candidate ties, normalize returns NEUTRAL for all of them and match_score is
# identical. Ranking then fell back to CSV row order, which is oldest-first — so "best
# camera, money no object" returned a 2024 S24 Ultra over the 2026 S26 Ultra.

def test_ties_prefer_the_newer_phone():
    df = pd.DataFrame([
        {"model_name": "Old", "launch_year": 2024, "price_inr": 90000, "series": "S",
         "camera_score": 8.0, "performance_score": 8.0, "battery_score": 8.0, "value_score": 8.0},
        {"model_name": "New", "launch_year": 2026, "price_inr": 90000, "series": "S",
         "camera_score": 8.0, "performance_score": 8.0, "battery_score": 8.0, "value_score": 8.0},
    ])
    out = wsm.recommend(df, NEUTRAL_W, top_n=2)
    assert out.iloc[0]["model_name"] == "New"


def test_ties_of_the_same_year_prefer_the_cheaper_phone():
    df = pd.DataFrame([
        {"model_name": "Dear", "launch_year": 2026, "price_inr": 120000, "series": "S",
         "camera_score": 8.0, "performance_score": 8.0, "battery_score": 8.0, "value_score": 8.0},
        {"model_name": "Cheap", "launch_year": 2026, "price_inr": 60000, "series": "S",
         "camera_score": 8.0, "performance_score": 8.0, "battery_score": 8.0, "value_score": 8.0},
    ])
    out = wsm.recommend(df, NEUTRAL_W, top_n=2)
    assert out.iloc[0]["model_name"] == "Cheap"


def test_best_camera_money_no_object_returns_the_newest_ultra():
    """The exact regression: camera weighted to the exclusion of all else must not hand
    back a two-year-old flagship."""
    df = pd.read_csv("data/processed/phones.csv")
    out = wsm.recommend(df, {"camera": 1.0, "performance": 0.0, "battery": 0.0, "value": 0.0},
                        budget_max=200000, top_n=1)
    assert out.iloc[0]["model_name"] == "Galaxy S26 Ultra"
