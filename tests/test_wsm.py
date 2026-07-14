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
    """Priya weights camera 0.50 — her #1 must be a camera leader, not the cheapest."""
    df = pd.read_csv("data/processed/phones.csv")
    p = personas.PERSONAS["Priya — Photography enthusiast"]
    out = wsm.recommend(df, p["weights"], budget_max=p["budget_max"], top_n=3)
    best_available = df[df["price_inr"] <= p["budget_max"]]["camera_score"].max()
    assert out.iloc[0]["camera_score"] == best_available


def test_budget_persona_still_picks_on_value():
    df = pd.read_csv("data/processed/phones.csv")
    p = personas.PERSONAS["Meera — Budget-conscious student"]
    out = wsm.recommend(df, p["weights"], budget_max=p["budget_max"], top_n=3)
    assert out.iloc[0]["value_score"] >= 9.0
