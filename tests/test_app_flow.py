# tests/test_app_flow.py — the two entry paths must stay different journeys.
#
# They had collapsed into one: picking a persona dumped you on the same "Tailor Your Choice"
# form as "Build My Own Preferences", so the quiz answered nothing and both buttons led to
# identical manual work. The design's persona path is personas -> analyzing -> results
# (that's what "Step 1 of 3" counts); the form is the *other* path.
from streamlit.testing.v1 import AppTest

APP = "app/streamlit_app.py"


def fresh():
    at = AppTest.from_file(APP, default_timeout=30)
    at.run()
    return at


def test_persona_path_reaches_results_without_the_manual_form():
    at = fresh()
    at.button(key="cta_start").click().run()
    at.button(key="path_persona").click().run()
    at.button(key="persona_Photography-first").click().run()
    assert at.session_state["screen"] == "personas", "Select marks the card, it does not navigate"
    at.button(key="persona_continue").click().run()
    assert at.session_state["screen"] == "results"
    assert at.session_state["persona"] == "Photography-first"


def test_build_your_own_path_reaches_the_manual_form():
    at = fresh()
    at.button(key="cta_start").click().run()
    at.button(key="path_custom").click().run()
    assert at.session_state["screen"] == "custom"
    assert at.session_state["persona"] is None


def test_the_two_paths_do_not_land_on_the_same_screen():
    a = fresh()
    a.button(key="cta_start").click().run()
    a.button(key="path_persona").click().run()
    a.button(key="persona_Gaming & performance").click().run()
    a.button(key="persona_continue").click().run()

    b = fresh()
    b.button(key="cta_start").click().run()
    b.button(key="path_custom").click().run()

    assert a.session_state["screen"] != b.session_state["screen"], \
        "picking a persona must answer the question, not hand over the same form"


def test_persona_applies_its_own_weights_and_budget():
    at = fresh()
    at.button(key="cta_start").click().run()
    at.button(key="path_persona").click().run()
    at.button(key="persona_Value / essentials").click().run()
    at.button(key="persona_continue").click().run()
    assert at.session_state["budget_max"] == 20000
    assert at.session_state["weights"]["value"] == 0.35


def test_persona_does_not_inherit_filters_from_an_earlier_custom_run():
    """A persona answers on its own terms — a leftover 12GB filter would silently narrow it."""
    at = fresh()
    at.session_state["filters"] = {"min_ram_gb": 12}
    at.session_state["screen"] = "personas"
    at.run()
    at.button(key="persona_Value / essentials").click().run()
    assert at.session_state["filters"] == {}


def test_sliders_rebuild_from_persisted_state_not_widget_keys():
    """Returning to the form must show the shopper's numbers, not a reset one.

    Streamlit purges a keyed widget's state on any run that doesn't render it and keeps the
    dead key in _old_state, so setdefault skipped it and the sliders fell back to min_value:
    every weight read 0.00 and the range reset to full the moment you came back via
    "Fine-tune this". The sliders now carry no key and derive from budget_max / filters /
    weights, which persist because they are ours rather than a widget's.

    Driven by seeding session_state rather than clicking across screens: AppTest keeps stale
    nodes from the previous screen in its element tree and raises on the keyless multiselect.
    """
    at = fresh()
    at.session_state["screen"] = "custom"
    at.session_state["weights"] = {"camera": 0.15, "performance": 0.35,
                                   "battery": 0.15, "value": 0.35}
    at.session_state["budget_max"] = 23000
    at.session_state["filters"] = {"min_price_inr": 17000}
    at.run()

    weight_sliders = [s for s in at.slider if not isinstance(s.value, (tuple, list))]
    assert [s.value for s in weight_sliders][:4] == [0.15, 0.35, 0.15, 0.35], \
        "weights must come back, not reset to 0.00"

    budget = [s for s in at.slider if isinstance(s.value, (tuple, list))][0]
    assert tuple(budget.value) == (17000, 23000), "the band must come back with you"


def test_budget_slider_defaults_to_the_full_span_when_nothing_is_set():
    at = fresh()
    at.session_state["screen"] = "custom"
    at.run()
    budget = [s for s in at.slider if isinstance(s.value, (tuple, list))][0]
    lo, hi = budget.value
    assert lo == min(int(x) for x in [9000]) and hi >= 139999


def test_around_20k_prompt_returns_phones_near_20k():
    """End to end: the prompt that returned a ₹1.4L S26 Ultra."""
    import sys; sys.path.insert(0, ".")
    from src.recommender import data, wsm
    at = fresh()
    at.session_state["screen"] = "custom"
    at.run()
    at.text_input(key="free_text").set_value(
        "I want a budget phone around 20,000 with good performance").run()
    at.button(key="do_parse").click().run()
    at.button(key="do_recommend").click().run()

    df = data.load_phones()
    top = wsm.recommend(df, at.session_state["weights"], budget_max=at.session_state["budget_max"],
                        top_n=3, filters=at.session_state["filters"])
    assert len(top) == 3
    assert (top["price_inr"] >= 17000).all() and (top["price_inr"] <= 23000).all()
