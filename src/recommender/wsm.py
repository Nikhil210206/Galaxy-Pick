# src/recommender/wsm.py — budget filter → normalize → weighted sum → rank → top-N.
SCORE_COLS = ["camera_score", "performance_score", "battery_score", "value_score"]
FACTORS = ["camera", "performance", "battery", "value"]
NEUTRAL_NORM = 5.0      # what a criterion is worth when every option ties on it


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


def recommend(df, weights, budget_max=None, form_factor=None, top_n=3):
    pool = df.copy()
    if budget_max:
        pool = pool[pool["price_inr"] <= budget_max]
    if form_factor == "foldable":
        pool = pool[pool["series"].isin(["Z-Flip", "Z-Fold"])]
    elif form_factor == "compact":
        pool = pool[pool["screen_size_inch"] <= 6.4]
    if pool.empty:                       # graceful: never return nothing
        pool = df.copy()

    # rank on the normalized pool, but hand back the raw scores — the cards and the
    # "why" line quote them, and "camera 7.4/10" is meaningful while a pool-relative
    # 0.0 is not.
    ranked = match_scores(normalize_scores(pool), weights)
    pool = pool.assign(match_score=ranked)
    return pool.sort_values("match_score", ascending=False).head(top_n)
