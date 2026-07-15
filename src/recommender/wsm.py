# src/recommender/wsm.py — budget filter → normalize → weighted sum → rank → top-N.
import pandas as pd

SCORE_COLS = ["camera_score", "performance_score", "battery_score", "value_score"]
FACTORS = ["camera", "performance", "battery", "value"]
NEUTRAL_NORM = 5.0      # what a criterion is worth when every option ties on it

# Hard filters cut the pool; weights only rank whatever survives. Each entry maps a
# filter key to (column, predicate) so `binding_filters` can re-test them one at a time.
FILTERS = {
    # The other half of the budget. `budget_max` is only a CEILING, and nothing in a weighted
    # sum pulls toward the money you're willing to spend: value_score is specs-per-rupee, so
    # the cheapest phone always wins it, and raising the cap from ₹20k to ₹50k returned the
    # identical ₹9,000 phone. A floor is what makes "I have ₹30k" mean something.
    "min_price_inr":    lambda df, v: df["price_inr"] >= v,
    "min_ram_gb":       lambda df, v: df["ram_gb"] >= v,
    "min_storage_gb":   lambda df, v: df["storage_gb"] >= v,
    "min_battery_mah":  lambda df, v: df["battery_mah"] >= v,
    "min_refresh_hz":   lambda df, v: df["refresh_rate_hz"] >= v,
    "min_charging_w":   lambda df, v: df["charging_w"] >= v,
    "max_screen_inch":  lambda df, v: df["screen_size_inch"] <= v,
    "min_screen_inch":  lambda df, v: df["screen_size_inch"] >= v,
    "series":           lambda df, v: df["series"].isin(list(v)),
    "exclude_projections": lambda df, v: df["spec_source"] != "mock" if v else df["model_name"].notna(),
}


def apply_filters(df, filters):
    """Drop every row failing any hard filter. Unknown/None keys are ignored."""
    pool = df
    for key, value in (filters or {}).items():
        if value is None or key not in FILTERS:
            continue
        pool = pool[FILTERS[key](pool, value)]
    return pool


def normalize_scores(df):
    """Put all four criteria on a common 0–10 scale across the rows given.

    A weighted sum only respects its weights if the criteria share a scale: a
    criterion's real influence is weight × spread. The raw scores don't share one
    (value_score already spans 0–10, camera spans ~3), so without this step value
    silently outvotes camera even at half the weight. Standard MCDM practice is to
    normalize the decision matrix — i.e. the alternatives actually being compared —
    so this is applied to the in-budget pool, not the whole catalog.
    """
    out = df.copy()
    for c in SCORE_COLS:
        lo, hi = df[c].min(), df[c].max()
        # every option identical on this criterion → it can't discriminate, so it
        # must not tip the ranking either way
        out[c] = (df[c] - lo) / (hi - lo) * 10 if hi > lo else NEUTRAL_NORM
    return out


def match_scores(df, weights):
    w = [weights["camera"], weights["performance"], weights["battery"], weights["value"]]
    return (df[SCORE_COLS] * w).sum(axis=1).round(2)


def build_pool(df, budget_max=None, form_factor=None, filters=None):
    """Every hard constraint, applied in one place so `binding_filters` can replay it."""
    pool = df.copy()
    if budget_max:
        pool = pool[pool["price_inr"] <= budget_max]
    if form_factor == "foldable":
        pool = pool[pool["series"].isin(["Z-Flip", "Z-Fold"])]
    elif form_factor == "compact":
        pool = pool[pool["screen_size_inch"] <= 6.4]
    return apply_filters(pool, filters)


def recommend(df, weights, budget_max=None, form_factor=None, top_n=3, *, filters=None):
    """Rank the phones matching every hard constraint. `filters` is keyword-only so the
    signature frozen in PLAN.md §11 keeps working positionally for the notebook."""
    pool = build_pool(df, budget_max, form_factor, filters)
    if pool.empty:
        # An empty pool used to fall back to the whole catalog. That was harmless for a
        # budget slider but lies once hard filters exist: ask for 12GB RAM and you'd get
        # 6GB phones back with no warning. Say nothing rather than say something false —
        # callers pair this with binding_filters() to name what to relax.
        return pool.assign(match_score=pd.Series(dtype=float))

    # rank on the normalized pool, but hand back the raw scores — the cards and the
    # "why" line quote them, and "camera 7.4/10" is meaningful while a pool-relative
    # 0.0 is not.
    ranked = match_scores(normalize_scores(pool), weights)
    pool = pool.assign(match_score=ranked)
    # Ties are common and were previously broken by CSV row order, which favoured whatever
    # was listed first — in practice the oldest phone. When the WSM genuinely cannot
    # separate two phones, prefer the newer one, then the cheaper one; both are defensible
    # to a shopper in a way that "it was earlier in the file" is not.
    return pool.sort_values(
        ["match_score", "launch_year", "price_inr"],
        ascending=[False, False, True], kind="mergesort",
    ).head(top_n)


def binding_filters(df, budget_max=None, form_factor=None, filters=None):
    """Which single constraints are starving the pool — i.e. dropping any one of these
    on its own brings results back. Empty when the pool is non-empty, or when no single
    relaxation is enough (the constraints are jointly, not individually, too tight)."""
    if not build_pool(df, budget_max, form_factor, filters).empty:
        return []

    culprits = []
    if budget_max and not build_pool(df, None, form_factor, filters).empty:
        culprits.append("budget_max")
    if form_factor in ("foldable", "compact") and not build_pool(df, budget_max, None, filters).empty:
        culprits.append("form_factor")
    for key, value in (filters or {}).items():
        if value is None or key not in FILTERS:
            continue
        without = {k: v for k, v in filters.items() if k != key}
        if not build_pool(df, budget_max, form_factor, without).empty:
            culprits.append(key)
    return culprits
