"""Design tokens + CSS, ported from the Stitch project's DESIGN.md.

Source: stitch.withgoogle.com/projects/18177589114052184530 ("Galaxy Pick System").
Values are copied from that design system rather than eyeballed from screenshots, so
a design change can be re-ported by diffing DESIGN.md against this file.

Two deliberate deviations from the Stitch output, both forced by CLAUDE.md:
  * prices render in ₹, not the design's $ (rule 5);
  * product shots are local SVG placeholders, not the design's hosted photography —
    the app must run with no network at all (rule 2).
"""

# --- colour ---------------------------------------------------------------
PRIMARY = "#1428A0"          # Samsung Blue — key actions, active states only
PRIMARY_DEEP = "#001278"
BG = "#F6F7FB"               # cool-toned canvas; never pure white
SURFACE = "#FFFFFF"          # elevated interactive components
SUBTLE = "#F2F4F8"           # secondary buttons, input fields
BORDER = "#E5E7EB"
TEXT = "#1A1B22"
TEXT_VARIANT = "#454653"
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
    background: {SURFACE}; border-bottom: 1px solid {BORDER};
    margin-left: -{EDGE}px; margin-right: -{EDGE}px; margin-bottom: 40px;
    padding: 12px {EDGE}px;
    width: calc(100% + {EDGE * 2}px) !important;
    max-width: calc(100% + {EDGE * 2}px) !important;
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

/* --- buttons: pill; primary blue, secondary #F2F4F8 -------------------- */
.stButton > button {{
    border-radius: 9999px; border: none; background: {SUBTLE}; color: {TEXT};
    font-family: Inter, sans-serif; font-size: 16px; font-weight: 600;
    padding: 8px 24px; width: 100%; transition: background .15s ease;
}}
.stButton > button:hover {{ background: #E6E9F0; color: {TEXT}; }}
.stButton > button[kind="primary"] {{ background: {PRIMARY}; color: #FFFFFF; padding: 12px 32px; }}
.stButton > button[kind="primary"]:hover {{ background: {PRIMARY_DEEP}; color: #FFFFFF; }}

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
