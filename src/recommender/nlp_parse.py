# src/recommender/nlp_parse.py — free text → {weights, budget_max, form_factor, must_haves}
#
# Deterministic-first: the rule-based parser below is the default and always works
# offline. Gemini is tried only when a key is present, and any failure — network,
# quota, malformed JSON, invalid weights — silently falls back to the rules.
import json
import re

from . import config

FACTORS = ["camera", "performance", "battery", "value"]
NEUTRAL = {f: 0.25 for f in FACTORS}
BOOST = 0.3
BUDGET_MIN, BUDGET_MAX = 5000, 200000

KEYWORDS = {
    "camera": ["camera", "photo", "photography", "photos", "pictures", "picture", "shoot", "selfie", "zoom"],
    "performance": ["game", "gaming", "games", "fps", "performance", "fast", "smooth", "speed", "lag", "powerful"],
    "battery": ["battery", "backup", "long-lasting", "long lasting", "charge", "charging", "all-day", "all day"],
    "value": ["cheap", "budget", "value", "affordable", "worth", "vfm", "money"],
}

_BUDGET_RE = re.compile(r"(?:under|below|less than|within|upto|up to)\s*(?:₹|rs\.?|inr)?\s*(\d+(?:,\d+)*)\s*(k|thousand|lakh|l)?", re.I)
_COMPACT_RE = re.compile(r"\b(compact|small|one[- ]hand(ed)?|pocket)\b", re.I)
_FOLDABLE_RE = re.compile(r"\b(fold|folds|foldable|flip|flips)\b", re.I)


def _renormalize(weights):
    """Force the four weights onto a valid simplex summing to 1.0."""
    clean = {}
    for f in FACTORS:
        try:
            v = float(weights.get(f, 0.0))
        except (TypeError, ValueError):
            v = 0.0
        clean[f] = max(0.0, v)         # negatives are meaningless here
    total = sum(clean.values())
    if total <= 0:                      # nothing usable → neutral, never divide by zero
        return dict(NEUTRAL)
    return {f: round(clean[f] / total, 4) for f in FACTORS}


def _parse_budget(text):
    m = _BUDGET_RE.search(text)
    if not m:
        return None
    amount = float(m.group(1).replace(",", ""))
    unit = (m.group(2) or "").lower()
    if unit in ("k", "thousand"):
        amount *= 1_000
    elif unit in ("lakh", "l"):
        amount *= 100_000
    elif amount <= 200:                 # bare "under 50" almost certainly means 50k
        amount *= 1_000
    return int(min(max(amount, BUDGET_MIN), BUDGET_MAX))


def _parse_form_factor(text):
    if _FOLDABLE_RE.search(text):
        return "foldable"
    if _COMPACT_RE.search(text):
        return "compact"
    return "any"


def parse_rules(text):
    """The deterministic fallback. Never raises, never touches the network."""
    text = (text or "").strip()
    if not text:
        return {"weights": dict(NEUTRAL), "budget_max": None, "form_factor": "any", "must_haves": []}

    low = text.lower()
    weights = dict(NEUTRAL)
    must_haves = []
    for factor, words in KEYWORDS.items():
        if any(w in low for w in words):
            weights[factor] += BOOST
            must_haves.append(factor)

    return {
        "weights": _renormalize(weights),   # gibberish → all neutral, still sums to 1
        "budget_max": _parse_budget(low),
        "form_factor": _parse_form_factor(low),
        "must_haves": must_haves,
    }


GEMINI_PROMPT = """\
Convert the shopper request into JSON only (no prose), matching:
{{"weights":{{"camera":0-1,"performance":0-1,"battery":0-1,"value":0-1}},
 "budget_max": <int INR or null>, "form_factor":"any|compact|foldable", "must_haves":[str]}}
Rules: the four weights must sum to 1.0; if a need is unstated use 0.25 each; "50k"=50000.
Example: "best camera phone under 60k" ->
{{"weights":{{"camera":0.55,"performance":0.15,"battery":0.15,"value":0.15}},
 "budget_max":60000,"form_factor":"any","must_haves":["camera"]}}
Request: "{text}" ->
"""


def _validate(raw):
    """Coerce a model response into the contract, or raise so the caller falls back."""
    if not isinstance(raw, dict):
        raise ValueError("not a JSON object")

    weights = raw.get("weights")
    if not isinstance(weights, dict) or not all(f in weights for f in FACTORS):
        raise ValueError("weights missing one of the four factors")
    weights = _renormalize(weights)

    budget = raw.get("budget_max")
    if budget is not None:
        budget = int(min(max(float(budget), BUDGET_MIN), BUDGET_MAX))

    form_factor = raw.get("form_factor", "any")
    if form_factor not in ("any", "compact", "foldable"):
        form_factor = "any"

    must_haves = raw.get("must_haves") or []
    if not isinstance(must_haves, list):
        must_haves = []

    return {
        "weights": weights,
        "budget_max": budget,
        "form_factor": form_factor,
        "must_haves": [str(m) for m in must_haves],
    }


def parse_gemini(text):
    """Live path. Raises on any problem — the caller is expected to catch and fall back."""
    import google.generativeai as genai

    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel(config.GEMINI_MODEL)
    resp = model.generate_content(GEMINI_PROMPT.format(text=text))
    body = (resp.text or "").strip()
    body = re.sub(r"^```(?:json)?|```$", "", body, flags=re.M).strip()  # strip code fences
    return _validate(json.loads(body))


def parse(text):
    """free text → {"weights", "budget_max", "form_factor", "must_haves"}.

    Gemini when a key is set and it succeeds; the rule-based parser otherwise.
    """
    if config.GEMINI_ENABLED and (text or "").strip():
        try:
            return parse_gemini(text)
        except Exception:
            pass    # any failure at all → deterministic path, demo must never break
    return parse_rules(text)
