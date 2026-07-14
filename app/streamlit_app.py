"""Galaxy-Pick — Streamlit demo.

PLACEHOLDER LAYOUT. The real UI is being designed in Stitch and will replace the
body of this file (PLAN.md Phase 3). This skeleton exists so the engine is
demoable and the offline fallback drill can be run end to end today — it is
deliberately unstyled, so don't invest in polishing it here.

What must survive the redesign:
  free text (if any) -> nlp_parse.parse() ; else the persona's weights/budget
  -> wsm.recommend() -> explain.reason() per card
  ...plus the provenance panel, which is a graded Responsible-AI asset.
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.recommender import cards, config, data, explain, nlp_parse, personas, wsm

st.set_page_config(page_title="Galaxy-Pick", page_icon="📱", layout="wide")
df = data.load_phones()

# --- sidebar: the shopper's input ---------------------------------------
st.sidebar.title("Galaxy-Pick")
persona_name = st.sidebar.selectbox("Who are you shopping for?", list(personas.PERSONAS))
persona = personas.PERSONAS[persona_name]
st.sidebar.caption(persona["story"])

free_text = st.sidebar.text_input("…or describe what you want", placeholder="photography under ₹50k")
budget = st.sidebar.slider("Budget (₹)", 10_000, 200_000, int(persona["budget_max"]), step=5_000)

# Free text wins when present; otherwise the persona drives.
if free_text.strip():
    parsed = nlp_parse.parse(free_text)
    weights = parsed["weights"]
    budget_max = parsed["budget_max"] or budget
    form_factor = parsed["form_factor"]
    label = None
    st.sidebar.caption(f"Parsed → {parsed['weights']}")
else:
    weights, budget_max, form_factor, label = persona["weights"], budget, "any", persona_name

top3 = wsm.recommend(df, weights, budget_max=budget_max, form_factor=form_factor, top_n=3)
close = explain.is_close_call(top3)

# --- main: the top-3 ----------------------------------------------------
st.header("Your top 3")
for col, (_, row) in zip(st.columns(3), top3.iterrows()):
    with col:
        st.markdown(cards.placeholder_svg(row["model_name"], row["series"]), unsafe_allow_html=True)
        st.subheader(row["model_name"])
        st.metric("Match", f"{row['match_score']}/10")
        st.write(f"₹{int(row['price_inr']):,}")
        if row["spec_source"] == "mock":
            st.warning(f"{int(row['launch_year'])} projection — not confirmed specs", icon="⚠️")
        st.bar_chart({c.replace("_score", ""): [row[c]] for c in wsm.SCORE_COLS})
        st.caption(explain.reason(row, weights, persona_label=label, close_call=close))

st.subheader("Full ranking")
st.dataframe(wsm.recommend(df, weights, budget_max=budget_max, form_factor=form_factor, top_n=len(df)))

# --- Responsible AI (graded Ch.4 asset — must stay visible) -------------
with st.expander("Data provenance & limitations"):
    p = data.provenance(df)
    st.write(f"**{p['total']} models** — {p['real']} real (2024–25), {p['mock']} projected ({', '.join(map(str, p['mock_years']))}).")
    st.write("- **2026 models are projections**, not confirmed specs. They can and do win recommendations.")
    st.write("- **Scores are transparent heuristics, not benchmarks.** `camera_score` reflects series optics tier, not lab testing.")
    st.write("- `value_score` is price-driven by construction, so it structurally favours budget phones.")
    st.write(f"- Natural-language parsing: **{'Gemini (with offline fallback)' if config.GEMINI_ENABLED else 'deterministic offline parser'}**.")
