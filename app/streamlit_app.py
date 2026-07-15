"""Galaxy-Pick — Streamlit demo.

A port of the Stitch design (project 18177589114052184530) onto the WSM engine in
`src/recommender/`, which stays the single source of truth: this file computes nothing
it could import. Design tokens live in `app/theme.py`.

The flow the engine pins down, preserved through the redesign:
  free text (if any) -> nlp_parse.parse() ; else the persona's weights/budget
  -> wsm.recommend() -> explain.reason() per card
  ...plus the provenance panel, which is a graded Responsible-AI asset.

Where this departs from the Stitch screens, and why (all forced by CLAUDE.md):
  * 4 personas, not the design's 6 — Content Creator and Everyday User have no weight
    vector, and inventing one would ship a persona with no expected top-3 (rule 3, B.4);
  * "Display Quality"/"Storage Capacity"/series chips are hard filters on the pool, not
    weights — the WSM has exactly four criteria and may not grow more (rule 3);
  * a free-text box, which the design has nowhere, because the brief requires plain
    English in and the parse pre-fills the sliders so the shopper can correct it;
  * the design's "based on current market availability and official Samsung
    specifications" fine print is replaced by the provenance panel: every 2026 row is
    projected, and claiming otherwise is the one thing rule 6 forbids.
"""
import sys
import time
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import theme
from src.recommender import cards, config, data, explain, nlp_parse, personas, scoring, wsm

st.set_page_config(page_title="Galaxy Pick", page_icon="📱", layout="wide")
st.markdown(theme.CSS, unsafe_allow_html=True)

df = data.load_phones()

# The design's series chips offer A/M/S/Z. The catalog also has an F line, and PLAN.md
# B.4 expects F15 5G in the Value / essentials top-3 — so F gets a chip too rather than
# being quietly unreachable.
SERIES_GROUPS = {
    "Galaxy S": ["S", "S-FE", "S-Ultra"],
    "Galaxy Z": ["Z-Flip", "Z-Fold"],
    "Galaxy A": ["A"],
    "Galaxy M": ["M"],
    "Galaxy F": ["F"],
}
FACTOR_LABELS = {
    "camera": "Camera importance",
    "performance": "Performance (gaming/work)",
    "battery": "Battery life",
    "value": "Price-to-value priority",
}
# Derived from the catalog, not hard-coded: the ceiling was 185000 for a Z Fold8 that turned
# out not to exist, which left the budget slider with 45k of dead travel above every phone.
PRICE_FLOOR = int(df["price_inr"].min() // 1000 * 1000)
PRICE_CEIL = int(-(-df["price_inr"].max() // 1000) * 1000)
# The 2026 line shipped with confirmed specs, so nothing in the catalog is projected today.
# The disclosure machinery stays — it just has nothing to say until something is projected again.
HAS_PROJECTIONS = bool((df["spec_source"] == "mock").any())

DEFAULTS = {
    "screen": "landing",
    "persona": None,
    "free_text": "",
    "weights": {f: 0.25 for f in wsm.FACTORS},
    "budget_max": PRICE_CEIL,
    "form_factor": "any",
    "filters": {},
    "detail_model": None,
    "parse_note": None,
}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
# The weight sliders read their value straight from session state — seeding the keys here
# (rather than passing value= at the call site) is what lets set_weights() move them.
for _f in wsm.FACTORS:
    st.session_state.setdefault(f"w_{_f}", DEFAULTS["weights"][_f])

WEIGHT_STEP = 0.05


def go(screen):
    st.session_state.screen = screen
    st.rerun()


def set_weights(weights):
    """Write weights to the slider widgets, not just to our own state.

    A keyed Streamlit widget ignores its `value=` argument once it exists, so assigning
    st.session_state.weights alone would leave the sliders showing the old numbers — the
    parse would look like it had done nothing.
    """
    st.session_state.weights = dict(weights)
    for factor, value in weights.items():
        # snap to the slider's grid so the handle lands on a notch it can return to
        st.session_state[f"w_{factor}"] = round(float(value) / WEIGHT_STEP) * WEIGHT_STEP


# --- chrome ---------------------------------------------------------------
def nav():
    """Brand and links on one row, inside the bar.

    Everything here must live inside the keyed container: a raw <div> from st.markdown
    closes immediately and does NOT wrap the widgets that follow, which is what left the
    four links floating below the bar instead of in it.
    """
    # Which nav item owns the current screen — the design underlines the active one.
    owner = {"landing": "landing", "choose": "choose", "personas": "choose", "custom": "choose",
             "analyzing": "choose", "results": "choose", "details": "choose",
             "compare": "compare", "about": "about"}.get(st.session_state.screen)
    with st.container(key="gp_nav"):
        brand, home, recs, comp, about = st.columns(
            [5, 1, 1.7, 1, 1], vertical_alignment="center")
        with brand:
            st.markdown("<div class='gp-brand'>Galaxy Pick</div>", unsafe_allow_html=True)
        for col, (label, screen) in zip(
            (home, recs, comp, about),
            [("Home", "landing"), ("Recommendations", "choose"),
             ("Compare", "compare"), ("About", "about")],
        ):
            with col:
                # "primary" is what the CSS hooks to draw the active underline
                if st.button(label, key=f"nav_{screen}",
                             type="primary" if owner == screen else "secondary"):
                    go(screen)


def footer():
    st.markdown(
        '<div class="gp-footer"><div>Galaxy Pick<br/>'
        "<span class='gp-caption'>Samsung GenAI capstone — PJ1 prototype. "
        "Not an official Samsung product.</span></div>"
        "<div class='gp-caption'>Prices in ₹ (INR)</div></div>",
        unsafe_allow_html=True,
    )


def card(key):
    """A card that can hold widgets. Use `with card("x"):` — never a raw <div>."""
    return st.container(border=True, key=key)


def price_block(row, size=22):
    """Current street price, with the drop from MSRP when there is one.

    Showing only MSRP was the original sin here: a 2024 S24 Ultra listed at its ₹1,47,559
    launch price in 2026. Showing only the aged price hides that it's an estimate.
    """
    now = theme.money(row["price_inr"])
    if row["price_source"] == "depreciation_model" and row["launch_price_inr"] > row["price_inr"]:
        off = 100 - round(row["price_inr"] / row["launch_price_inr"] * 100)
        return (f"<span style='font-size:{size}px;font-weight:600;color:{theme.PRIMARY}'>{now}</span>"
                f"<span class='gp-caption' style='margin-left:10px;text-decoration:line-through'>"
                f"{theme.money(row['launch_price_inr'])}</span>"
                f"<span class='gp-chip' style='margin-left:8px'>≈{off}% off launch · estimated</span>")
    return f"<span style='font-size:{size}px;font-weight:600;color:{theme.PRIMARY}'>{now}</span>"


# --- screens --------------------------------------------------------------
def screen_landing():
    hero, art = st.columns([1, 1.1], gap="large", vertical_alignment="center")
    with hero:
        st.markdown("<div style='height:48px'></div>", unsafe_allow_html=True)
        # tracking-tighter + the primary-container accent on "Galaxy", per the design
        st.markdown(
            "<div class='gp-hero gp-stagger-1'>Find Your Perfect<br/>"
            f"<span style='color:{theme.PRIMARY_CONTAINER}'>Galaxy</span></div>"
            "<div style='height:16px'></div>"
            "<div class='gp-body gp-stagger-2' style='max-width:512px;font-size:18px'>"
            "Tell us how you actually use a phone — or set the specs yourself — and we'll "
            "rank the Galaxy line against your priorities, and show our working.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        if st.button("Get Started", key="cta_start", type="primary"):
            go("choose")
        p = data.provenance(df)
        st.markdown(
            "<div style='height:24px'></div><div class='gp-stagger-4' style='opacity:.7'>"
            "<span class='gp-chip gp-glass'>Transparent scoring</span>"
            f"<span class='gp-chip gp-glass'>{p['total']} models · 2024–2026</span>"
            "<span class='gp-chip gp-glass'>Works offline</span></div>",
            unsafe_allow_html=True,
        )
    with art:
        # The design's own hero shot: object-contain, drop shadow, gently floating.
        st.markdown(
            f"<img src='{theme.asset('hero_devices.jpg')}' alt='Premium Samsung Galaxy devices' "
            f"class='gp-float' style='width:100%;height:auto;object-fit:contain;"
            f"border-radius:{theme.RADIUS_CARD};"
            "filter:drop-shadow(0 25px 25px rgba(0,0,0,0.15));'/>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='gp-section-title' style='text-align:center'>Explore the Galaxy Ecosystem</div>"
        "<div style='height:24px'></div>",
        unsafe_allow_html=True,
    )
    blurbs = {
        "Galaxy S": "Flagship performance and the most advanced camera system in the line.",
        "Galaxy Z": "Innovation meets portability with foldable and flip form factors.",
        "Galaxy A": "Everything you need in an everyday smartphone, at a price that works.",
    }
    for col, (label, blurb) in zip(st.columns(3, gap="medium"), blurbs.items()):
        pool = df[df["series"].isin(SERIES_GROUPS[label])]
        with col:
            st.markdown(
                f"<div class='gp-card gp-card-tight'>"
                f"<div class='gp-label'>{len(pool)} models</div>"
                f"<div style='height:8px'></div>"
                f"<div class='gp-section-title'>{label}</div>"
                # min-height keeps the three cards level when the blurbs wrap differently
                f"<div class='gp-body' style='font-size:14px;min-height:48px'>{blurb}</div>"
                f"<div style='height:8px'></div>"
                f"<div class='gp-caption'>From {theme.money(pool['price_inr'].min())}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


def screen_choose():
    st.markdown(
        "<div style='text-align:center'>"
        "<div class='gp-page-title'>How would you like to find your next Galaxy?</div>"
        "<div class='gp-body'>Choose the path that fits your shopping style.</div></div>"
        "<div style='height:40px'></div>",
        unsafe_allow_html=True,
    )
    left, right = st.columns(2, gap="large")
    # Both buttons belong INSIDE their card, as the design has them — a raw <div> from
    # st.markdown closes before the button renders and leaves it stranded underneath.
    with left, card("gp_path_persona"):
        st.markdown(
            "<div style='text-align:center'>"
            "<div class='gp-section-title'>What best describes you?</div>"
            "<div class='gp-body' style='font-size:14px;min-height:48px'>Choose a lifestyle "
            "that matches how you use your phone.</div></div>"
            "<div style='height:8px'></div>",
            unsafe_allow_html=True,
        )
        if st.button("Start Here", key="path_persona", type="primary"):
            go("personas")
    with right, card("gp_path_custom"):
        st.markdown(
            "<div style='text-align:center'>"
            "<div class='gp-section-title'>Build My Own Preferences</div>"
            "<div class='gp-body' style='font-size:14px;min-height:48px'>Describe it in plain "
            "English, then tune the priorities and specs yourself.</div></div>"
            "<div style='height:8px'></div>",
            unsafe_allow_html=True,
        )
        if st.button("Customize", key="path_custom"):
            st.session_state.persona = None
            go("custom")


def screen_personas():
    st.markdown(
        "<div style='text-align:center'>"
        "<div class='gp-label'>Step 1 of 3</div><div style='height:8px'></div>"
        "<div class='gp-page-title'>What best describes you?</div>"
        "<div class='gp-body'>Tell us a bit about your lifestyle and we'll rank the whole "
        "Galaxy line against it — no forms to fill in.</div></div>"
        "<div style='height:40px'></div>",
        unsafe_allow_html=True,
    )
    items = list(personas.PERSONAS.items())
    for row_start in (0, 2):
        for col, (name, p) in zip(st.columns(2, gap="large"), items[row_start:row_start + 2]):
            chosen = st.session_state.persona == name
            with col, card(f"gp_persona_{row_start}_{name[:4]}"):
                lead = max(p["weights"], key=p["weights"].get)
                st.markdown(
                    f"<div class='gp-section-title'>{name}</div>"
                    f"<div class='gp-body' style='font-size:14px;min-height:76px'>{p['story']}</div>"
                    f"<span class='gp-chip'>Leads on {explain.FACTOR_LABEL[lead]}</span>"
                    f"<span class='gp-chip'>Up to {theme.money(p['budget_max'])}</span>"
                    "<div style='height:12px'></div>",
                    unsafe_allow_html=True,
                )
                # Select marks the card; "Continue with Selection" below does the navigating,
                # exactly as the design lays it out.
                if st.button("Selected ✓" if chosen else "Select", key=f"persona_{name}",
                             type="primary" if chosen else "secondary"):
                    st.session_state.persona = name
                    set_weights(p["weights"])
                    st.session_state.budget_max = int(p["budget_max"])
                    st.session_state.free_text = ""
                    st.session_state.parse_note = None
                    # A persona answers on its own terms — don't carry over spec filters or a
                    # form factor left behind by an earlier "Build my own" run.
                    st.session_state.filters = {}
                    st.session_state.form_factor = "any"
                    st.rerun()
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        if st.button("Continue with Selection", key="persona_continue", type="primary",
                     disabled=st.session_state.persona is None):
            go("analyzing")
        if st.session_state.persona is None:
            st.markdown("<div class='gp-caption' style='text-align:center'>"
                        "Pick a profile to continue.</div>", unsafe_allow_html=True)


def screen_custom():
    st.markdown(
        "<div class='gp-page-title'>Tailor Your Choice</div>"
        "<div class='gp-body'>Adjust the parameters below to help us find the Galaxy that fits "
        "your lifestyle. Importance sliders re-rank the phones; the spec filters below remove "
        "phones that don't qualify at all.</div>"
        "<div style='height:24px'></div>",
        unsafe_allow_html=True,
    )
    if st.session_state.persona:
        st.markdown(
            f"<span class='gp-chip'>Starting from: {st.session_state.persona}</span>",
            unsafe_allow_html=True,
        )

    with card("gp_form"):

        # --- plain English -> weights (the design has no text box; the brief requires one)
        st.markdown("<div class='gp-label'>Describe what you want</div>", unsafe_allow_html=True)
        text = st.text_input(
            "free text", key="free_text", label_visibility="collapsed",
            placeholder="e.g. photography phone under ₹50k",
        )
        if st.button("Interpret this", key="do_parse"):
            if text.strip():
                parsed = nlp_parse.parse(text)
                set_weights(parsed["weights"])
                st.session_state.form_factor = parsed["form_factor"]
                if parsed["budget_max"]:
                    st.session_state.budget_max = int(parsed["budget_max"])
                engine = "Gemini" if config.GEMINI_ENABLED else "offline parser"
                st.session_state.parse_note = (
                    f"Read by the {engine} as: " + ", ".join(
                        f"{explain.FACTOR_LABEL[f]} {v:.0%}"
                        for f, v in parsed["weights"].items()
                    ) + (f" · budget {theme.money(parsed['budget_max'])}" if parsed["budget_max"] else "")
                    + (f" · {parsed['form_factor']}" if parsed["form_factor"] != "any" else "")
                    + ". Correct it with the sliders below."
                )
                st.rerun()
        if st.session_state.parse_note:
            st.markdown(
                f"<div class='gp-caption' style='background:{theme.SUBTLE};border-radius:12px;"
                f"padding:12px 16px'>{st.session_state.parse_note}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<hr class='gp-rule'/>", unsafe_allow_html=True)

        # --- series chips (hard filter) ---------------------------------------
        st.markdown("<div class='gp-label'>Which series interest you?</div>", unsafe_allow_html=True)
        picked = st.multiselect(
            "series", list(SERIES_GROUPS), default=[], label_visibility="collapsed",
            placeholder="All series",
        )

        st.markdown("<hr class='gp-rule'/>", unsafe_allow_html=True)

        # --- the four WSM weights --------------------------------------------
        st.markdown(
            "<div class='gp-label'>What matters to you</div>"
            "<div class='gp-caption'>These are the four criteria the ranking actually uses. "
            "They're re-scaled to sum to 100%, so raising one lowers the others.</div>",
            unsafe_allow_html=True,
        )
        # Two per row. zip() against a single st.columns(2) silently drops factors 3 and 4:
        # battery and value never rendered, and every ranking ran with them at 0%.
        raw = {}
        for start in range(0, len(wsm.FACTORS), 2):
            for col, factor in zip(st.columns(2, gap="large"), wsm.FACTORS[start:start + 2]):
                with col:
                    raw[factor] = st.slider(
                        FACTOR_LABELS[factor], 0.0, 1.0, step=WEIGHT_STEP, key=f"w_{factor}",
                    )
        assert len(raw) == len(wsm.FACTORS), "every WSM criterion must have a slider"
        weights = nlp_parse.renormalize(raw)
        st.markdown(
            "<div class='gp-caption'>Normalized weights: "
            + " · ".join(f"{explain.FACTOR_LABEL[f]} <b>{v:.0%}</b>"
                         for f, v in weights.items())
            + "</div>",
            unsafe_allow_html=True,
        )

        st.markdown("<hr class='gp-rule'/>", unsafe_allow_html=True)

        # --- hard spec filters -------------------------------------------------
        st.markdown(
            "<div class='gp-label'>Spec filters</div>"
            "<div class='gp-caption'>Unlike the sliders above, these remove phones from the "
            "running entirely.</div>",
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2, gap="large")
        with c1:
            budget = st.slider("Budget range", PRICE_FLOOR, PRICE_CEIL,
                               int(st.session_state.budget_max), 1000, format="₹%d")
            min_ram = st.select_slider("Minimum RAM", [0, 6, 8, 12], value=0,
                                       format_func=lambda v: "Any" if not v else f"{v} GB")
            min_storage = st.select_slider("Storage capacity", [0, 128, 256, 512], value=0,
                                           format_func=lambda v: "Any" if not v else f"{v} GB")
            min_batt = st.select_slider("Minimum battery", [0, 4000, 5000, 6000], value=0,
                                        format_func=lambda v: "Any" if not v else f"{v} mAh")
        with c2:
            # Display quality is a 90/120Hz split and nothing else — the catalog has only those
            # two refresh rates, so this filter is binary by construction, like camera MP.
            display = st.radio("Display quality", ["Any", "120Hz only"], horizontal=True)
            min_charge = st.select_slider("Minimum charging", [0, 25, 45, 65], value=0,
                                          format_func=lambda v: "Any" if not v else f"{v} W")
            form = st.radio("Form factor", ["any", "compact", "foldable"], horizontal=True,
                            index=["any", "compact", "foldable"].index(st.session_state.form_factor),
                            format_func=str.title)
            # Only offer this when there is something to hide. Every phone in the catalog now
            # has a confirmed spec sheet, so the toggle would do nothing — and worse, it would
            # imply some of these phones are speculative when none are.
            hide_mock = False
            if HAS_PROJECTIONS:
                hide_mock = st.toggle("Hide projections", value=False,
                                      help="Projected specs are modelled, not confirmed. Off by "
                                           "default so you see them — clearly marked — rather "
                                           "than silently not.")

        filters = {
            "min_ram_gb": min_ram or None,
            "min_storage_gb": min_storage or None,
            "min_battery_mah": min_batt or None,
            "min_charging_w": min_charge or None,
            "min_refresh_hz": 120 if display == "120Hz only" else None,
            "series": [s for g in picked for s in SERIES_GROUPS[g]] or None,
            "exclude_projections": hide_mock or None,
        }
        pool = wsm.build_pool(df, budget, form, filters)
        st.markdown(
            f"<div style='height:16px'></div><div class='gp-caption'>"
            f"<b>{len(pool)}</b> of {len(df)} phones match these filters. Scores are normalized "
            f"across whichever phones survive, so the ranking is relative to this pool.</div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    if st.button("Find My Galaxy", key="do_recommend", type="primary"):
        st.session_state.weights = weights
        st.session_state.budget_max = budget
        st.session_state.form_factor = form
        st.session_state.filters = filters
        go("analyzing")


def screen_analyzing():
    """The design's interstitial.

    The engine is in-process and finishes in microseconds, so the dwell below is a
    presentation beat, not compute time — hence copy that states what the WSM did rather
    than implying the machine is off thinking somewhere.
    """
    pool = wsm.build_pool(df, st.session_state.budget_max, st.session_state.form_factor,
                          st.session_state.filters)
    st.markdown("<div style='height:80px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='text-align:center'>"
        "<div class='gp-page-title'>Ranking your matches</div>"
        f"<div class='gp-body'>Filtered {len(df)} models to {len(pool)} · normalizing four "
        "criteria across that pool · applying your weights.</div></div>",
        unsafe_allow_html=True,
    )
    st.progress(100)
    time.sleep(0.7)
    go("results")


def phone_chips(row):
    out = []
    # this phone's own strongest axis — NOT "best in the pool", which is what "Best on
    # performance" implied on a card that was ranked second for photography
    lead = max(wsm.FACTORS, key=lambda f: row[f"{f}_score"])
    out.append(f"<span class='gp-chip'>Strongest: {explain.FACTOR_LABEL[lead]}</span>")
    out.append(f"<span class='gp-chip'>{int(row['ram_gb'])}GB · {int(row['storage_gb'])}GB</span>")
    out.append(f"<span class='gp-chip'>{int(row['battery_mah'])} mAh</span>")
    if str(row["spec_source"]) == "mock":
        out.append(f"<span class='gp-chip-warn'>⚠ {int(row['launch_year'])} projection</span>")
    return "".join(out)


def screen_results():
    top3 = wsm.recommend(df, st.session_state.weights, budget_max=st.session_state.budget_max,
                         form_factor=st.session_state.form_factor, top_n=3,
                         filters=st.session_state.filters)

    if top3.empty:
        blocking = wsm.binding_filters(df, st.session_state.budget_max,
                                       st.session_state.form_factor, st.session_state.filters)
        pretty = {"budget_max": "the budget", "form_factor": "the form factor",
                  "min_ram_gb": "minimum RAM", "min_storage_gb": "storage capacity",
                  "min_battery_mah": "minimum battery", "min_charging_w": "minimum charging",
                  "min_refresh_hz": "display quality", "series": "the series selection",
                  "exclude_projections": "hiding 2026 projections"}
        st.markdown("<div class='gp-page-title'>No phone matches those filters</div>",
                    unsafe_allow_html=True)
        if blocking:
            st.markdown(
                "<div class='gp-body'>Relaxing any one of these would bring results back: "
                + ", ".join(f"<b>{pretty.get(b, b)}</b>" for b in blocking) + ".</div>",
                unsafe_allow_html=True)
        else:
            st.markdown("<div class='gp-body'>The filters are too tight in combination — "
                        "no single change is enough. Try loosening a few.</div>",
                        unsafe_allow_html=True)
        if st.button("Adjust my filters", key="empty_back", type="primary"):
            go("custom")
        return

    close = explain.is_close_call(top3)
    label = st.session_state.persona
    st.markdown(
        "<div class='gp-page-title'>Recommended for You</div>"
        "<div class='gp-body'>Based on your preferences, these Galaxy devices are your "
        "best match.</div><div style='height:24px'></div>",
        unsafe_allow_html=True,
    )

    # --- best match -------------------------------------------------------
    best = top3.iloc[0]
    art, info = st.columns([1, 1.4], gap="large", vertical_alignment="center")
    with art:
        # The design's "Top Recommendation" art. It is a Galaxy line-up, not a shot of this
        # specific phone — decorative, exactly as Stitch uses it. The provenance panel says so.
        st.markdown(
            f"<div style='border-radius:{theme.RADIUS_CARD};overflow:hidden;"
            f"box-shadow:{theme.SHADOW};'>"
            f"<img src='{theme.asset('rec_top.jpg')}' alt='Galaxy range' class='gp-hover-scale' "
            "style='width:100%;height:100%;object-fit:cover;display:block;'/></div>",
            unsafe_allow_html=True,
        )
    with info, card("gp_best"):
        st.markdown(
            f"<span class='gp-badge'>Best match · {best['match_score']}/10</span>"
            f"<div style='height:16px'></div>"
            f"<div class='gp-hero' style='font-size:28px'>{best['model_name']}</div>"
            f"{price_block(best, size=24)}"
            f"<div style='height:8px'></div>"
            f"<div class='gp-body' style='font-size:15px'>"
            f"{explain.reason(best, st.session_state.weights, persona_label=label, close_call=close)}"
            f"</div><div style='height:8px'></div>{phone_chips(best)}"
            "<div style='height:12px'></div>",
            unsafe_allow_html=True,
        )
        b1, b2 = st.columns(2)
        with b1:
            if st.button("View Details", key="best_details", type="primary"):
                st.session_state.detail_model = best["model_name"]
                go("details")
        with b2:
            if st.button("Compare", key="best_compare"):
                go("compare")

    # --- runners-up -------------------------------------------------------
    st.markdown("<div style='height:40px'></div>"
                "<div class='gp-section-title'>Other Great Options</div>"
                "<div style='height:16px'></div>", unsafe_allow_html=True)
    alt_art = ["rec_alt_1.jpg", "rec_alt_2.jpg"]
    for i, (col, (_, row)) in enumerate(zip(st.columns(2, gap="large"),
                                            list(top3.iloc[1:].iterrows()))):
        with col, card("gp_alt_" + str(row["model_name"]).replace(" ", "_")):
            # Illustrative Galaxy photography from the design — one image per card slot, as
            # Stitch lays it out, not a photo of this particular model.
            st.markdown(
                f"<div style='border-radius:{theme.RADIUS_NESTED};overflow:hidden;"
                "margin:-8px 0 12px 0;height:150px;'>"
                f"<img src='{theme.asset(alt_art[i % len(alt_art)])}' alt='Galaxy devices' "
                "style='width:100%;height:100%;object-fit:cover;display:block;'/></div>"
                f"<span class='gp-chip'>{row['match_score']}/10 match</span>"
                f"<div style='height:8px'></div>"
                f"<div class='gp-section-title'>{row['model_name']}</div>"
                f"{price_block(row, size=18)}"
                f"<div class='gp-body' style='font-size:14px;min-height:72px'>"
                f"{explain.reason(row, st.session_state.weights, persona_label=label)}</div>"
                f"{phone_chips(row)}<div style='height:12px'></div>",
                unsafe_allow_html=True,
            )
            if st.button("View details", key=f"det_{row['model_name']}"):
                st.session_state.detail_model = row["model_name"]
                go("details")

    # --- retake CTA -------------------------------------------------------
    st.markdown("<div style='height:40px'></div>", unsafe_allow_html=True)
    cta, btn = st.columns([3, 1])
    with cta:
        st.markdown(
            "<div class='gp-cta'><h3>Not seeing the perfect match?</h3>"
            "<div style='opacity:.85'>Retake the quiz, or tune the priorities and specs "
            "yourself — your current answers carry over.</div></div>",
            unsafe_allow_html=True,
        )
    with btn:
        st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
        if st.button("Retake Quiz", key="retake"):
            go("personas")
        # The persona path now goes straight to results, so this is how a persona shopper
        # reaches the sliders — starting from their persona's weights rather than a blank form.
        if st.button("Fine-tune this", key="refine"):
            go("custom")

    full = wsm.recommend(df, st.session_state.weights, budget_max=st.session_state.budget_max,
                         form_factor=st.session_state.form_factor, top_n=len(df),
                         filters=st.session_state.filters)
    with st.expander(f"Full ranking — all {len(full)} phones matching your filters"):
        st.dataframe(
            full[["model_name", "series", "launch_year", "price_inr", "match_score",
                  *wsm.SCORE_COLS, "spec_source"]],
            hide_index=True, use_container_width=True,
        )
    provenance_panel()


def screen_details():
    row = df[df["model_name"] == st.session_state.detail_model]
    if row.empty:
        go("results")
    row = row.iloc[0]
    if st.button("← Back to recommendations", key="det_back"):
        go("results")

    art, info = st.columns([1, 1.4], gap="large")
    with art:
        st.markdown(
            f"<div class='gp-card' style='display:flex;justify-content:center'>"
            f"{cards.placeholder_svg(row['model_name'], row['series'])}</div>",
            unsafe_allow_html=True,
        )
    with info:
        st.markdown(
            f"<div class='gp-page-title'>{row['model_name']}</div>"
            f"{price_block(row, size=24)}"
            f"<div style='height:8px'></div>{phone_chips(row)}",
            unsafe_allow_html=True,
        )
        if str(row["spec_source"]) == "mock":
            st.warning(f"{int(row['launch_year'])} projection — these specs are modelled, "
                       "not confirmed by Samsung.", icon="⚠️")
        if row["price_source"] == "depreciation_model":
            st.info(f"Launched at {theme.money(row['launch_price_inr'])} in "
                    f"{int(row['launch_year'])}. The price shown is an **estimated** street "
                    f"price for {scoring.CATALOG_YEAR}, modelled from age — not a live quote.",
                    icon="ℹ️")

    st.markdown("<div style='height:24px'></div>"
                "<div class='gp-section-title'>Full specification</div>", unsafe_allow_html=True)
    specs = {
        "Series": row["series"], "Launched": int(row["launch_year"]),
        "Chipset": row["chipset"], "RAM": f"{int(row['ram_gb'])} GB",
        "Storage": f"{int(row['storage_gb'])} GB", "Rear camera": f"{int(row['rear_camera_mp'])} MP",
        "Battery": f"{int(row['battery_mah'])} mAh", "Screen": f"{row['screen_size_inch']}\"",
        "Refresh rate": f"{int(row['refresh_rate_hz'])} Hz",
        "Charging": f"{int(row['charging_w'])} W", "Segment": row["segment"],
    }
    items = list(specs.items())
    for start in range(0, len(items), 4):
        for col, (k, v) in zip(st.columns(4, gap="medium"), items[start:start + 4]):
            with col:
                st.markdown(f"<div class='gp-label'>{k}</div><div class='gp-body'>{v}</div>",
                            unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>"
                "<div class='gp-section-title'>How it scored</div>"
                "<div class='gp-caption'>Raw scores out of 10, before pool normalization.</div>",
                unsafe_allow_html=True)
    # One row per criterion. A dict of single-value lists makes each criterion a *series*,
    # which Streamlit stacks into one bar running to 28 — four scores out of ten, added up.
    st.bar_chart(
        pd.DataFrame({"score out of 10": [float(row[f"{f}_score"]) for f in wsm.FACTORS]},
                     index=[explain.FACTOR_LABEL[f] for f in wsm.FACTORS]),
        horizontal=True, height=220,
    )
    provenance_panel()


def screen_compare():
    st.markdown("<div class='gp-page-title'>Compare</div>"
                "<div class='gp-body'>Put any Galaxy models side by side.</div>",
                unsafe_allow_html=True)
    picks = st.multiselect("Models", df["model_name"].tolist(),
                           default=df["model_name"].tolist()[:2], label_visibility="collapsed")
    if not picks:
        st.info("Pick at least one model to compare.")
        return
    sub = df[df["model_name"].isin(picks)]
    rows = ["price_inr", "launch_price_inr", "series", "launch_year", "chipset", "ram_gb",
            "storage_gb", "rear_camera_mp", "battery_mah", "screen_size_inch",
            "refresh_rate_hz", "charging_w", *wsm.SCORE_COLS, "spec_source", "price_source"]
    table = sub.set_index("model_name")[rows].T
    table.index = [r.replace("_inr", " (₹)").replace("_", " ").title() for r in rows]
    st.dataframe(table, use_container_width=True)
    if (sub["spec_source"] == "mock").any():
        st.warning("Some models shown are projections — modelled specs, not confirmed.", icon="⚠️")
    if (sub["price_source"] == "depreciation_model").any():
        st.info("Prices shown for 2024–25 models are estimated street prices, not quotes — "
                "the launch MSRP is the confirmed figure.", icon="ℹ️")
    provenance_panel()


def screen_about():
    st.markdown("<div class='gp-page-title'>About Galaxy Pick</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='gp-card'><div class='gp-body'>"
        "Galaxy Pick ranks the Galaxy line against what you actually care about using a "
        "<b>Weighted Sum Model</b>: each phone gets four transparent 0–10 scores (camera, "
        "performance, battery, value), your priorities become weights that sum to 1, and "
        "<code>match = Σ score × weight</code>. Hard filters remove phones from the pool "
        "first; the weights only rank whatever survives.<br/><br/>"
        "There is no machine learning here, and that's deliberate — every number on screen "
        "can be traced back to a spec in a CSV and a formula you can read. The app runs "
        "fully offline; natural-language parsing uses Gemini when a key is present and a "
        "deterministic parser otherwise, with identical output contracts."
        "</div></div>",
        unsafe_allow_html=True,
    )
    provenance_panel()


def provenance_panel():
    """Responsible-AI disclosure (graded Ch.4 asset — must stay visible).

    This replaces the Stitch design's "based on current market availability and official
    Samsung specifications" line, which would be a false claim about a third of the rows.
    """
    p = data.provenance(df)
    with st.expander("Data provenance & limitations", expanded=False):
        st.markdown(
            f"**{p['total']} models** — {p['real']} with confirmed spec sheets, "
            f"{p['mock']} projected"
            + (f" ({', '.join(map(str, p['mock_years']))})" if p["mock_years"] else "")
            + f". **{p['modelled_prices']} prices are estimates**, not quotes."
        )
        st.markdown(
            ("- **Projected models are not confirmed specs.** They can and do win "
             "recommendations, and are marked wherever they appear.\n" if HAS_PROJECTIONS else
             "- **Every model here has shipped**, with a confirmed spec sheet — nothing in the "
             "catalog is a projection. Earlier versions carried modelled 2026 specs; those were "
             "replaced with real ones, which corrected the S26's chipset, the S26 Ultra's "
             "battery and charging, and the A17's silicon.\n")
            + f"- **Prices for 2024–25 models are modelled, not quoted.** Launch MSRP is real; "
            f"the {scoring.CATALOG_YEAR} street price is estimated by depreciating it "
            f"({int(scoring.DEPRECIATION['flagship']*100)}%/yr retained for flagships, "
            f"{int(scoring.DEPRECIATION['mid']*100)}% mid, {int(scoring.DEPRECIATION['budget']*100)}% budget). "
            "Real prices move with stock and offers; treat these as indicative.\n"
            "- **Product photography is illustrative.** The images are the design's stock "
            "Galaxy range shots, not photographs of the specific model on the card — the "
            "catalog has no per-model imagery. Judge a phone by its specs here, not its picture.\n"
            "- **Scores are transparent heuristics, not benchmarks.** `camera_score` reflects "
            "series optics tier, not lab testing.\n"
            "- `value_score` is price-driven by construction, so it structurally favours "
            "budget phones.\n"
            "- Scores are normalized **across the phones matching your filters**, so changing a "
            "filter changes what the ranking is relative to.\n"
            f"- Natural-language parsing: **{'Gemini (with offline fallback)' if config.GEMINI_ENABLED else 'deterministic offline parser'}**.\n"
            "- Prototype for a Samsung GenAI capstone. Not an official Samsung product, and "
            "not priced or stocked in real time."
        )


SCREENS = {
    "landing": screen_landing, "choose": screen_choose, "personas": screen_personas,
    "custom": screen_custom, "analyzing": screen_analyzing, "results": screen_results,
    "details": screen_details, "compare": screen_compare, "about": screen_about,
}

nav()
SCREENS[st.session_state.screen]()
footer()
