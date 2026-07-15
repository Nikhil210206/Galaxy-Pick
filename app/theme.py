"""Design tokens + CSS, ported from the Stitch project.

Source: stitch.withgoogle.com/projects/18177589114052184530 ("Galaxy Pick System").
Ported from the generated screens' own Tailwind config and <style> block — NOT from
DESIGN.md's prose, which disagrees with what the screens render, and not from screenshots.
Pull a screen's HTML via the stitch MCP (`list_screens` → htmlCode.downloadUrl) to re-diff.

Deliberate deviations from the Stitch output, each forced by CLAUDE.md:
  * prices render in ₹, not the design's $ (rule 5);
  * the design's images are downloaded into app/assets/ and inlined, not hot-linked from
    lh3.googleusercontent.com — the app must run with no network at all (rule 2);
  * no #shader-canvas background: it is WebGL driven by a <script>, and Streamlit strips
    scripts from st.markdown. Reproducing it needs an iframe, which cannot sit behind the
    page. The static gradient below stands in for it.
"""
import base64
from functools import lru_cache
from pathlib import Path

# --- colour ---------------------------------------------------------------
# Values are the Tailwind token map the Stitch screens actually render with, not the prose
# in DESIGN.md's "Colors" section — the two disagree. The prose says background #F6F7FB and
# border #E5E7EB; every generated screen ships `background: #fbf8ff` and outline-variant
# #c5c5d5. The rendered tokens win: they are what the design looks like.
PRIMARY = "#001278"          # token `primary` — brand wordmark, active nav link
PRIMARY_CONTAINER = "#1428A0"  # token `primary-container` — Samsung Blue: CTAs, the "Galaxy" word
PRIMARY_DEEP = "#000D60"     # token `on-primary-fixed` — pressed/hover
BG = "#FBF8FF"               # token `background`/`surface`
SURFACE = "#FFFFFF"          # token `surface-container-lowest` — elevated components
SUBTLE = "#EFECF7"           # token `surface-container`
SUBTLE_HIGH = "#E9E7F1"      # token `surface-container-high`
BORDER = "#C5C5D5"           # token `outline-variant`
TEXT = "#1A1B22"             # token `on-surface`
TEXT_VARIANT = "#454653"     # token `on-surface-variant`
WARNING = "#8A5A00"
WARNING_BG = "#FFF4E0"

# --- layout ---------------------------------------------------------------
CONTAINER_MAX = "1440px"     # DESIGN.md spacing.container-max
EDGE = 48                    # DESIGN.md spacing.edge-margin

# --- shape / depth --------------------------------------------------------
RADIUS_CARD = "24px"         # all primary cards and large containers
RADIUS_NESTED = "16px"       # images inside a 24px card
RADIUS_INPUT = "12px"
SHADOW = "0px 4px 20px rgba(0, 0, 0, 0.04)"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

/* Inter is the design's surrogate for SamsungOne. The @import above is the app's only
   network call and is purely cosmetic — the -apple-system fallback keeps the demo
   identical in shape offline, which the fallback drill requires. */
html, body, [class*="css"], .stApp {{
    font-family: Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
.stApp {{ background: {BG}; color: {TEXT}; }}
#MainMenu, footer, header {{ visibility: hidden; }}
.block-container {{ max-width: {CONTAINER_MAX}; padding: 0 {EDGE}px 80px {EDGE}px; }}

h1, h2, h3 {{ color: {TEXT}; letter-spacing: -0.01em; }}

/* --- type scale ------------------------------------------------------- */
.gp-hero {{ font-size: 36px; font-weight: 700; line-height: 1.2; letter-spacing: -0.02em; }}
.gp-page-title {{ font-size: 28px; font-weight: 700; line-height: 1.3; letter-spacing: -0.01em; }}
.gp-section-title {{ font-size: 22px; font-weight: 600; line-height: 1.4; }}
.gp-body {{ font-size: 16px; font-weight: 400; line-height: 1.6; color: {TEXT_VARIANT}; }}
.gp-caption {{ font-size: 14px; font-weight: 500; line-height: 1.4; color: {TEXT_VARIANT}; }}
.gp-label {{
    font-size: 12px; font-weight: 700; line-height: 1; letter-spacing: 0.05em;
    text-transform: uppercase; color: {TEXT_VARIANT};
}}

/* --- nav: white bar, subtle bottom border, 72px ------------------------
   The brand and the links must sit on ONE row inside the bar. Rendering the bar as a raw
   <div> and the buttons as Streamlit columns underneath leaves the links floating below
   it — st.markdown cannot wrap widgets that come after it. So the bar is a keyed
   st.container and everything lives inside it. */
/* The bar is full-bleed: it must cancel the block-container's edge padding on both sides,
   or it stops short of the right edge and reads as a floating panel, not a nav bar.
   The `.stApp` prefix is load-bearing: Streamlit's own stVerticalBlock width rule is also
   !important, and at equal specificity the later rule (theirs) wins — so the width silently
   stayed at the padded content width even though the negative margins applied. */
.stApp .st-key-gp_nav {{
    /* .nav-blur from the Stitch screens: translucent + backdrop blur, NOT solid white */
    background: rgba(251, 248, 255, 0.8);
    backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid {BORDER};
    margin-left: -{EDGE}px; margin-right: -{EDGE}px; margin-bottom: 40px;
    padding: 12px {EDGE}px;
    width: calc(100% + {EDGE * 2}px) !important;
    max-width: calc(100% + {EDGE * 2}px) !important;
    position: sticky; top: 0; z-index: 99;
}}

/* Glassmorphism, straight from the design's .glass-effect */
.gp-glass {{
    backdrop-filter: blur(24px); -webkit-backdrop-filter: blur(24px);
    background-color: rgba(255, 255, 255, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.4);
}}

/* Entrance + idle motion, from the design's keyframes */
@keyframes slideUpFade {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
.gp-stagger-1 {{ animation: slideUpFade .8s ease-out forwards; }}
.gp-stagger-2 {{ animation: slideUpFade .8s ease-out .2s forwards; opacity: 0; }}
.gp-stagger-3 {{ animation: slideUpFade .8s ease-out .4s forwards; opacity: 0; }}
.gp-stagger-4 {{ animation: slideUpFade .8s ease-out .6s forwards; opacity: 0; }}
@keyframes float {{
    0%   {{ transform: translateY(0px); }}
    50%  {{ transform: translateY(-15px); }}
    100% {{ transform: translateY(0px); }}
}}
.gp-float {{ animation: float 6s ease-in-out infinite; }}
.gp-hover-scale {{ transition: transform .4s cubic-bezier(0.175, 0.885, 0.32, 1.275); }}
.gp-hover-scale:hover {{ transform: scale(1.05); }}
@media (prefers-reduced-motion: reduce) {{
    .gp-stagger-1, .gp-stagger-2, .gp-stagger-3, .gp-stagger-4, .gp-float {{
        animation: none; opacity: 1;
    }}
}}
.st-key-gp_nav [data-testid="stVerticalBlockBorderWrapper"] {{
    background: transparent; box-shadow: none; border: none; padding: 0;
}}
.gp-brand {{ font-size: 20px; font-weight: 700; color: {PRIMARY}; letter-spacing: -0.01em; }}

/* --- cards: white, 24px radius, 0.04 shadow, 24-32px padding ----------
   Every card that contains a widget is an st.container(border=True); this styles the
   wrapper Streamlit puts around it. .gp-card remains for pure-HTML blocks (no widgets). */
.stApp [data-testid="stVerticalBlockBorderWrapper"] {{
    background: {SURFACE}; border-radius: {RADIUS_CARD} !important;
    box-shadow: {SHADOW} !important;
    /* DESIGN.md: depth comes from a soft ambient shadow, not a stroke. Streamlit's own
       border=True stroke is !important, so this needs the .stApp prefix to win. */
    border: 1px solid transparent !important; padding: 24px;
}}
.gp-card {{
    background: {SURFACE}; border-radius: {RADIUS_CARD}; box-shadow: {SHADOW};
    padding: 32px; border: 1px solid transparent; transition: border-color .15s ease;
}}
.gp-card:hover {{ border-color: {BORDER}; }}
.gp-card-tight {{ padding: 24px; }}

/* the page background must not look like a card */
.stApp > [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stMainBlockContainer"] > div > [data-testid="stVerticalBlockBorderWrapper"] {{
    background: transparent; box-shadow: none; padding: 0;
}}

/* --- buttons: pill; primary Samsung Blue, secondary tonal ------------- */
.stButton > button {{
    border-radius: 9999px; border: none; background: {SUBTLE}; color: {TEXT};
    font-family: Inter, sans-serif; font-size: 16px; font-weight: 600;
    padding: 8px 24px; width: 100%; transition: background .15s ease;
}}
.stButton > button:hover {{ background: {SUBTLE_HIGH}; color: {TEXT}; }}
.stButton > button[kind="primary"] {{ background: {PRIMARY_CONTAINER}; color: #FFFFFF; padding: 12px 32px; }}
.stButton > button[kind="primary"]:hover {{ background: {PRIMARY_DEEP}; color: #FFFFFF; }}

/* --- nav links: text with an underline on the active one, not pills ----
   The design's nav is <a> elements — `font-bold text-primary border-b-2` when active,
   `text-on-surface-variant` otherwise. Streamlit only gives us buttons, so strip them back
   to look like links rather than leaving four grey pills floating in the bar. */
.st-key-gp_nav .stButton > button {{
    background: transparent !important; border-radius: 0 !important;
    color: {TEXT_VARIANT}; font-weight: 700; padding: 4px 0 !important;
    border-bottom: 2px solid transparent !important; width: auto;
    transition: color .2s ease, border-color .2s ease;
}}
.st-key-gp_nav .stButton > button:hover {{
    background: transparent !important; color: {PRIMARY};
}}
.st-key-gp_nav .stButton > button[kind="primary"] {{
    background: transparent !important; color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY} !important; padding: 4px 0 !important;
}}

/* --- inputs: grey fill, 12px radius, no border; blue focus ring -------- */
.stTextInput > div > div > input {{
    background: {SUBTLE}; border-radius: {RADIUS_INPUT}; border: none;
    font-size: 16px; padding: 12px 16px; color: {TEXT};
}}
.stTextInput > div > div > input:focus {{
    background: {SURFACE}; border: 2px solid {PRIMARY};
    box-shadow: 0 0 0 4px rgba(20, 40, 160, 0.10);
}}
[data-baseweb="select"] > div {{
    background: {SUBTLE}; border-radius: {RADIUS_INPUT}; border: none;
}}

/* --- sliders ---------------------------------------------------------- */
.stSlider [data-baseweb="slider"] [role="slider"] {{ background: {PRIMARY}; }}
.stSlider [data-baseweb="slider"] > div > div > div {{ background: {PRIMARY}; }}

/* --- badges / chips ---------------------------------------------------- */
.gp-badge {{
    display: inline-block; background: {PRIMARY}; color: #FFF;
    font-size: 12px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
    padding: 6px 14px; border-radius: 9999px;
}}
.gp-chip {{
    display: inline-block; background: {SUBTLE}; color: {TEXT_VARIANT};
    font-size: 12px; font-weight: 600; padding: 6px 14px; border-radius: 9999px;
    margin: 0 6px 6px 0;
}}
.gp-chip-warn {{
    display: inline-block; background: {WARNING_BG}; color: {WARNING};
    font-size: 12px; font-weight: 700; padding: 6px 14px; border-radius: 9999px;
    margin: 0 6px 6px 0;
}}

/* --- misc -------------------------------------------------------------- */
.gp-rule {{ height: 1px; background: {BORDER}; border: none; margin: 24px 0; }}
.gp-footer {{
    border-top: 1px solid {BORDER}; margin-top: 80px; padding-top: 24px;
    display: flex; justify-content: space-between; color: {TEXT_VARIANT}; font-size: 14px;
}}
.gp-cta {{
    background: {PRIMARY}; border-radius: {RADIUS_CARD}; padding: 32px; color: #FFFFFF;
}}
.gp-cta h3 {{ color: #FFFFFF; margin: 0 0 8px 0; }}
</style>
"""


@lru_cache(maxsize=None)
def asset(name):
    """A design image as a base64 data URI.

    The images are the Stitch project's own, downloaded into app/assets/ rather than
    hot-linked: the design points at lh3.googleusercontent.com, and the demo has to run with
    no network at all (rule 2). Inlining as a data URI keeps full CSS control (object-contain,
    the float animation, drop shadows) which st.image would not give us.
    """
    path = Path(__file__).parent / "assets" / name
    return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()


def money(rupees):
    """₹1,04,999 — Indian digit grouping (rule 5); the design's $ formatting is wrong here."""
    s = str(int(rupees))
    if len(s) <= 3:
        return f"₹{s}"
    head, tail = s[:-3], s[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return "₹" + ",".join(parts + [tail])
