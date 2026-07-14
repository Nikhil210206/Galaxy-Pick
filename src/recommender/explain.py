# src/recommender/explain.py — the one-line "why" for each recommendation.
#
# Template-first, same as everything else: the string below is always produced
# offline. Gemini can only polish an already-valid sentence.
from . import config

FACTOR_LABEL = {
    "camera": "camera",
    "performance": "performance",
    "battery": "battery life",
    "value": "value for money",
}
SCORE_COL = {f: f"{f}_score" for f in FACTOR_LABEL}
CLOSE_CALL_DELTA = 0.3


def top_factors(row, weights, n=2):
    """The factors that contributed most to this row's match score — weight × score."""
    contributions = {f: weights.get(f, 0.0) * float(row[SCORE_COL[f]]) for f in FACTOR_LABEL}
    ranked = sorted(contributions, key=contributions.get, reverse=True)
    return ranked[:n]


def is_close_call(ranked_df, delta=CLOSE_CALL_DELTA):
    """True when the top two are within `delta` — worth telling the shopper."""
    if len(ranked_df) < 2 or "match_score" not in ranked_df.columns:
        return False
    scores = ranked_df["match_score"].tolist()
    return (scores[0] - scores[1]) < delta


def reason(row, weights, persona_label=None, close_call=False):
    """One-line justification for a single recommendation."""
    first, second = top_factors(row, weights, n=2)
    goal = persona_label.split("—")[-1].strip() if persona_label else "what you asked for"

    text = (
        f"Great for {goal}: strong {FACTOR_LABEL[first]} ({row[SCORE_COL[first]]}/10) "
        f"and {FACTOR_LABEL[second]} ({row[SCORE_COL[second]]}/10), "
        f"and at ₹{int(row['price_inr']):,} it fits your budget."
    )
    if close_call:
        text += " Note: this was a close call with the runner-up — compare both."
    if str(row.get("spec_source", "real")) == "mock":
        text += f" ({int(row['launch_year'])} specs are projected, not confirmed.)"

    if config.GEMINI_ENABLED:
        try:
            return _polish(text)
        except Exception:
            pass    # polish is cosmetic; the template already says everything needed
    return text


def _polish(text):
    """Optional Gemini rewrite. Raises on any problem so `reason` keeps the template."""
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    prompt = (
        "Rewrite this phone recommendation as one friendly sentence for a shopper. "
        "Keep every number and fact exactly as given. Do not add claims. Output the sentence only.\n\n"
        f"{text}"
    )
    out = (model.generate_content(prompt).text or "").strip()
    if not out or len(out) > 3 * len(text):
        raise ValueError("implausible polish result")
    return out
