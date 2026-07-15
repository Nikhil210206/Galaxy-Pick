# tests/test_theme.py
from app import theme


def test_css_builds():
    """theme.CSS is an f-string, so a stray brace in a CSS rule or comment raises at import
    and takes the whole app down. Importing it here is the cheap guard."""
    assert len(theme.CSS) > 1000
    assert "{{" not in theme.CSS and "}}" not in theme.CSS   # escapes all resolved


def test_css_carries_the_design_tokens():
    for token in [theme.PRIMARY, theme.BG, theme.SURFACE, theme.RADIUS_CARD, "Inter"]:
        assert token in theme.CSS


def test_full_bleed_rules_outrank_streamlit():
    """Streamlit's own width/border rules are !important; ours only win with the .stApp
    prefix. Without it the nav stops short of the right edge and cards keep a grey stroke."""
    for rule in [".stApp .st-key-gp_nav", '.stApp [data-testid="stVerticalBlockBorderWrapper"]']:
        assert rule in theme.CSS


def test_money_uses_indian_digit_grouping():
    assert theme.money(147559) == "₹1,47,559"
    assert theme.money(68200) == "₹68,200"
    assert theme.money(999) == "₹999"
    assert theme.money(1200) == "₹1,200"
