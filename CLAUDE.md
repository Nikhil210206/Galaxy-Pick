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
6. **Dataset = 2024–2026, one row per model (~36 rows).** 2024–2025 rows are real; **every 2026 row is `spec_source=mock`** and must be presented as a projection, never as fact. Never pad with fabricated model names.
7. **The AI agent must NOT create git commits or appear in author history.** Generate/modify files only. After each phase, print the suggested commit message from `PLAN.md` — the human runs `git` themselves.

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
- `scoring.py` — raw specs → four 0–10 scores (camera / performance / battery / value). Formulas in `PLAN.md` Appendix B.
- `personas.py` — 4 personas, each with a weight vector that sums to 1.0.
- `wsm.py` — budget filter → weighted sum → rank → top-N.
- `nlp_parse.py` — free-text → `{weights, budget_max, form_factor, must_haves}`; Gemini if enabled else rule-based; **always validated** before use.
- `explain.py` — template "why" string (+ optional Gemini polish).

## Quick reference
`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v` (scores 0–10, weights sum to 1 → match 0–10). Full scoring formulas and the persona weight table are in **`PLAN.md` Appendix B**.

## Definition of done
- `phones.csv`: ~36 rows, `launch_year ∈ {2024,2025,2026}`, all 2026 rows `spec_source=mock`, every score ∈ [0,10], no nulls in required columns.
- Notebook runs top-to-bottom (Restart & Run All) and contains 3 EDA findings + the WSM worked example.
- App: each persona → correct top-3; free-text "photography under ₹50k" → camera-weighted, in-budget results.
- **Fallback drill:** with no key and no network, NL parsing + explanations still work.
- `pytest` green.

## Out of scope (do not add)
Fine-tuning · RAG · embeddings · vector DB · backend/API server · database · authentication · caching · Grok · paid Hugging Face · web scraping at runtime.
