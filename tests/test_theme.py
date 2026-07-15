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


# --- ported from the screens' real CSS, not DESIGN.md's prose ------------

def test_uses_the_rendered_token_values_not_the_prose():
    """DESIGN.md's prose says background #F6F7FB / border #E5E7EB; every generated screen
    actually ships #fbf8ff and #c5c5d5. The rendered tokens are what the design looks like."""
    assert theme.BG.upper() == "#FBF8FF"
    assert theme.BORDER.upper() == "#C5C5D5"
    assert theme.PRIMARY.upper() == "#001278"            # brand wordmark / active nav
    assert theme.PRIMARY_CONTAINER.upper() == "#1428A0"  # Samsung Blue: CTAs


def test_carries_the_designs_signature_effects():
    for rule in ["backdrop-filter", "gp-glass", "slideUpFade", "gp-float", "gp-hover-scale"]:
        assert rule in theme.CSS, f"{rule} missing — the design's look depends on it"


# --- assets --------------------------------------------------------------

def test_design_images_are_local_and_inlined():
    """The design hot-links lh3.googleusercontent.com; the demo must run with no network,
    so the images live in app/assets/ and are inlined as data URIs."""
    for name in ["hero_devices.jpg", "rec_top.jpg", "rec_alt_1.jpg", "rec_alt_2.jpg"]:
        uri = theme.asset(name)
        assert uri.startswith("data:image/jpeg;base64,")
        assert len(uri) > 5000


def test_no_remote_image_hosts_in_the_app():
    from pathlib import Path
    src = Path("app/streamlit_app.py").read_text() + theme.CSS
    for host in ["lh3.googleusercontent.com", "contribution.usercontent.google.com",
                 "cdn.tailwindcss.com"]:
        assert host not in src, f"{host} would make the demo depend on the network"
