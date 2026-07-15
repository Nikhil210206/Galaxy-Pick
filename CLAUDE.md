# CLAUDE.md — Galaxy-Pick

> Repo memory for the AI coding agent. Read this first, then follow **`PLAN.md`** (phases 0–5) for the actual build.

## What this is
**Galaxy-Pick** is the **PJ1** submission for the Samsung GenAI capstone: a **Galaxy phone recommendation prototype**. A shopper picks a persona *or* types what they want in plain English; the app returns a **ranked top-3** with a one-line reason for each. The graded analytical core lives in a **Jupyter notebook**; the demo is a **Streamlit** app. Both import the same engine in `src/recommender/`.

## Non-negotiable rules (do not violate these)
1. **Free / open-source only. No paid services, ever.** No Grok. No paid Hugging Face inference. No hosting fees. Gemini is **optional and free-tier only**.
2. **Deterministic-first.** The app MUST run fully **offline with no API key and no network**. Every Gemini call is wrapped in `try/except` and falls back to the rule-based path. The demo never depends on a network call.
3. **The recommendation logic is a Weighted Sum Model (WSM).** The brief requires it. Do **NOT** replace it with ML, embeddings, RAG, a vector DB, or a learned ranker — all explicitly out of scope.
4. **No over-engineering.** No backend server, no database, no auth, no caching layer. Data is a flat CSV; the app is Streamlit calling in-process Python functions.
5. **Currency is INR (₹).**
6. **Dataset = 2024–2026, one row per model (~37 rows). Never present modelled data as fact, and never pad with fabricated model names.** As of 2026-07-15 the 2026 line has **shipped**: every row now carries a confirmed spec sheet (`spec_source=real`) and nothing in the catalog is a projection. This rule used to read "every 2026 row is `spec_source=mock`" — that was true while the line was unreleased, and the earlier mock sheets were wrong in ways that mattered (the S26 is an **Exynos 2600**, not the invented "Snapdragon 8 Elite Gen2"; the S26 Ultra is 5000mAh/60W, not 5200/65). **The disclosure machinery stays** (`spec_source=mock` → ⚠ badge, "hide projections" filter, `explain.reason()` caveat); it simply has nothing to flag until something is projected again, and the UI hides the toggle when nothing is. Multi-variant models take the **base** RAM/storage variant — the one the quoted price buys.
6a. **Prices are two different things, and the difference is graded.** `launch_price_inr` is the real MSRP. `price_inr` is the **estimated street price at `scoring.CATALOG_YEAR` (2026)**, derived at build time by depreciating MSRP by age (`price_source=depreciation_model`); 2026 rows sit at MSRP (`price_source=launch_msrp`). It is an **estimate, never a quote** — the UI and the provenance panel must keep saying so. Do **not** wire up a live price API: Grok is banned (rule 1), Gemini has no retail feed and would hallucinate a fresh number every run, runtime fetching breaks rule 2, and nothing has prices for the projected S26 line regardless.
7. **The AI agent must NOT create git commits or appear in author history.** Generate/modify files only. Print the suggested commit message from `PLAN.md` §10 — the human runs `git` themselves. **No `Co-Authored-By` trailer**, ever.

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
- `wsm.py` — budget filter → **normalize the pool** → weighted sum → rank → top-N. The normalize step is load-bearing: influence in a weighted sum is weight × spread, so unscaled criteria silently re-weight the model (see `PLAN.md` B.4).
- `nlp_parse.py` — free-text → `{weights, budget_max, form_factor, must_haves}`; Gemini if enabled else rule-based; **always validated** before use.
- `explain.py` — template "why" string (+ optional Gemini polish).

## Quick reference
`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v` (scores 0–10, weights sum to 1 → match 0–10). Full scoring formulas and the persona weight table are in **`PLAN.md` Appendix B**.

## Definition of done
- `phones.csv`: ~36 rows, `launch_year ∈ {2024,2025,2026}`, all 2026 rows `spec_source=mock`, every score ∈ [0,10], no nulls in required columns.
- Notebook runs top-to-bottom (Restart & Run All) and contains 3 EDA findings + the WSM worked example (`7.5`).
- App: each persona → correct top-3, **matching the notebook** (expected picks are tabled in `PLAN.md` B.4); free-text "photography under ₹50k" → camera-weighted, in-budget results.
- **Personas must disagree.** If every persona returns the same phone, the WSM is broken — that's the exact failure the normalize step fixes, and `tests/test_wsm.py` guards it.
- **Fallback drill:** with no key and no network, NL parsing + explanations still work.
- `pytest` green.

## Out of scope (do not add)
Fine-tuning · RAG · embeddings · vector DB · backend/API server · database · authentication · caching · Grok · paid Hugging Face · web scraping at runtime.
