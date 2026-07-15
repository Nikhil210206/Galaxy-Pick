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
