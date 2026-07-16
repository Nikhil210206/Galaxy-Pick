# CLAUDE.md — Galaxy-Pick

> Repo memory for the AI coding agent. Read this first, then follow **`PLAN.md`** (phases 0–5) for the actual build.

## What this is
**Galaxy-Pick** is the **PJ1** submission for the Samsung GenAI capstone: a **Galaxy phone recommendation prototype**. A shopper picks a persona *or* types what they want in plain English; the app returns a **ranked top-3** with a one-line reason for each. The graded analytical core lives in a **Jupyter notebook**; the demo is a **Streamlit** app. Both import the same engine in `src/recommender/`.

> **Current state (2026-07-16):** Phases 0–5 are **done and green** — 37 models, 83 tests passing, the notebook runs top-to-bottom with saved outputs, and the v1 Stitch UI is ported (7 screens). **The next piece of work is `PLAN.md` Phase 6: the GalaxyPick v2 redesign** — read that section before starting. Its decisions are settled, not open questions.

## Non-negotiable rules (do not violate these)
1. **Free / open-source only. No paid services, ever.** No Grok. No paid Hugging Face inference. No hosting fees. Gemini is **optional and free-tier only**.
2. **Deterministic-first.** The app MUST run fully **offline with no API key and no network**. Every Gemini call is wrapped in `try/except` and falls back to the rule-based path. The demo never depends on a network call.
3. **The recommendation logic is a Weighted Sum Model (WSM).** The brief requires it. Do **NOT** replace it with ML, embeddings, RAG, a vector DB, or a learned ranker — all explicitly out of scope.
4. **No over-engineering.** No backend server, no database, no auth, no caching layer. Data is a flat CSV; the app is Streamlit calling in-process Python functions.
5. **Currency is INR (₹).**
6. **Dataset = 2024–2026, one row per model (~37 rows). Never present modelled data as fact, and never pad with fabricated model names.** As of 2026-07-15 the 2026 line has **shipped**: every row now carries a confirmed spec sheet (`spec_source=real`) and nothing in the catalog is a projection. This rule used to read "every 2026 row is `spec_source=mock`" — that was true while the line was unreleased, and the earlier mock sheets were wrong in ways that mattered (the S26 is an **Exynos 2600**, not the invented "Snapdragon 8 Elite Gen2"; the S26 Ultra is 5000mAh/60W, not 5200/65). **The disclosure machinery stays** (`spec_source=mock` → ⚠ badge, "hide projections" filter, `explain.reason()` caveat); it simply has nothing to flag until something is projected again, and the UI hides the toggle when nothing is. Multi-variant models take the **base** RAM/storage variant — the one the quoted price buys.
6a. **Prices are two different things, and the difference is graded.** `launch_price_inr` is the real MSRP. `price_inr` is the **estimated street price at `scoring.CATALOG_YEAR` (2026)**, derived at build time by depreciating MSRP by age (`price_source=depreciation_model`); 2026 rows sit at MSRP (`price_source=launch_msrp`). It is an **estimate, never a quote** — the UI and the provenance panel must keep saying so. Do **not** wire up a live price API: Grok is banned (rule 1), Gemini has no retail feed and would hallucinate a fresh number every run, runtime fetching breaks rule 2, and nothing has prices for the projected S26 line regardless.
7. **The AI agent must NOT create git commits or appear in author history.** Generate/modify files only. Print the suggested commit message from `PLAN.md` §10 — the human runs `git` themselves. **No `Co-Authored-By` trailer**, ever.
8. **No invented commerce data — ever.** We have no ratings, no review counts, no user photos, no colours, and no retailer prices, so **none of those may be displayed**. A "4.6 out of 5 · 2,345 reviews" or an Amazon/Flipkart price would be a fabricated record — the exact thing rule 6 forbids, on the screen an examiner will poke first. **Outbound links are the only permitted commerce integration**: "Buy on Amazon" / "Read reviews on Amazon" may link out to a *search* URL (we have no product IDs). This keeps rule 2 — the app still renders offline; only the link needs the user's internet. Embedding a retailer is **impossible anyway**: `amazon.in` sends `x-frame-options: SAMEORIGIN` (verified 2026-07-16), scraping is banned by rule 1 and their ToS, and the Product Advertising API needs an affiliate account and returns no review text.

## Stack (all free / OSS)
Python 3.11 (Anaconda) · pandas · numpy · Jupyter · Streamlit · matplotlib · pytest · python-dotenv · google-generativeai *(optional)*.

## How to run
```bash
conda env create -f environment.yml
conda activate galaxy-pick
python scripts/build_dataset.py                  # writes data/processed/phones.csv
jupyter notebook notebooks/pj1_analysis.ipynb    # graded core
streamlit run app/streamlit_app.py               # demo UI
pytest -q                                         # tests
```

## Architecture
`src/recommender/` is the **single source of truth**, imported by BOTH the notebook and the app. Never duplicate logic in the notebook or the app.
- `config.py` — paths + `GEMINI_ENABLED` flag (True only if a key is actually present).
- `data.py` — load & validate `phones.csv`.
- `scoring.py` — raw specs → four 0–10 scores (camera / performance / battery / value), plus the build-time price depreciation. Formulas in `PLAN.md` Appendix B. **`camera_score` ranks on series optics tier, not megapixels** — MP takes only two values across the catalog, so it can't discriminate. **Keep the tier tables sized so tier + bonuses reach exactly 10.0 and never clamp**: when they overflowed, `_clamp` flattened four chipset generations to a single 10.0 and a 2024 S24 Ultra tied a 2026 S26 Ultra on both camera and performance. `tests/test_scoring.py` guards the headroom.
- `personas.py` — 4 personas, each with a weight vector that sums to 1.0.
- `wsm.py` — budget + hard spec filters → **normalize the pool** → weighted sum → rank → top-N, ties broken by newer-then-cheaper. The normalize step is load-bearing: influence in a weighted sum is weight × spread, so unscaled criteria silently re-weight the model (see `PLAN.md` B.4). Hard filters live in the keyword-only `filters` dict (`FILTERS`); an unsatisfiable one returns an **empty** frame and `binding_filters()` names what to relax — it must never fall back to the whole catalog. **`budget_max` is only a ceiling**: nothing in a weighted sum pulls toward it, so `min_price_inr` is the other half of a budget (see below).
- `nlp_parse.py` — free-text → `{weights, budget_min, budget_max, form_factor, must_haves}`; Gemini if enabled else rule-based; **always validated** before use. A *ceiling* ("under 50k") sets `budget_max`; a *target* ("around 20k") is a **band**. Dismissals ("I don't mind the budget") suppress a factor instead of boosting it.
- `explain.py` — template "why" string (+ optional Gemini polish).

## Quick reference
`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v` (scores 0–10, weights sum to 1 → match 0–10). Full scoring formulas and the persona weight table are in **`PLAN.md` Appendix B**.

## Definition of done
- `phones.csv`: ~37 rows, `launch_year ∈ {2024,2025,2026}`, every score ∈ [0,10], no nulls in required columns, `price_inr ≤ launch_price_inr`, and **every chipset present in `scoring.CHIPSET_TIER`** (an unknown one silently scores the *lowest* tier — `build_dataset.py` asserts this).
- Notebook runs top-to-bottom (Restart & Run All) and contains 3 EDA findings + the WSM worked example (`7.5`).
- App: each persona → correct top-3, **matching the notebook** (expected picks are tabled in `PLAN.md` B.4); free-text "photography under ₹50k" → camera-weighted, in-budget results.
- **The two entry paths stay different journeys:** a persona goes personas → analyzing → results with *no form*; "Build My Own Preferences" is the only route to the sliders. `tests/test_app_flow.py` guards it.
- **Personas must disagree.** If every persona returns the same phone, the WSM is broken — that's the exact failure the normalize step fixes, and `tests/test_wsm.py` guards it.
- **Fallback drill:** with no key and no network, NL parsing + explanations still work.
- `pytest` green.

## Working on the app (`app/`) — traps that cost real time
The UI is a port of the Stitch design (project `18177589114052184530`); tokens live in `app/theme.py`. Each of these shipped a page that *looked* plausible and was wrong, and none was caught by `pytest`:
1. **`st.markdown("<div>")` does not wrap the widgets after it.** Streamlit closes the div immediately, so a "card" opened that way renders **empty** with its content spilling outside. Use `st.container(border=True, key=...)` and put widgets inside the `with`.
2. **Widget `key`s are a trap here — the sliders deliberately have none.** A keyed widget ignores `value=` once it exists (the parse can't move it), *and* Streamlit purges a keyed widget's state on any run that doesn't render it while keeping the dead key in `_old_state`, so `setdefault` skips it and the widget falls back to `min_value` (weights silently read 0.00). Keep the value in a **non-widget** key (`weights`, `budget_max`, `filters`) and pass `value=` to a **keyless** widget.
3. **Streamlit's own CSS is `!important`.** At equal specificity theirs wins, so prefix overrides with `.stApp` or they silently lose.
4. **`theme.CSS` is an f-string** — a brace in a CSS comment raises at import and kills the app. `tests/test_theme.py` guards it.
5. **`zip(st.columns(2), FOUR_THINGS)` silently drops two.** Loop in chunks.
6. **Port from each screen's HTML, not DESIGN.md's prose** — they disagree (prose says `#F6F7FB`, screens ship `#fbf8ff`). Fetch via the `stitch` MCP: `list_screens` → `htmlCode.downloadUrl`.
7. **Verify UI in a real browser** (Playwright, dev-only, not in `requirements.txt`). `AppTest` proves code runs, not that layout is right — and it raises `KeyError: '$$ID-…-None'` on keyless multiselects when clicking across screens, which the browser handles fine.

## Out of scope (do not add)
Fine-tuning · RAG · embeddings · vector DB · backend/API server · database · authentication · caching · Grok · paid Hugging Face · web scraping at runtime.
