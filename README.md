# Galaxy-Pick

A Samsung Galaxy phone recommender. Pick a persona — or just type what you want in plain English — and get a **ranked top-3** with a one-line reason for each.

Built for the Samsung GenAI capstone (PJ1). The graded analytical core is the notebook; the demo is a Streamlit app. Both import the **same engine** from `src/recommender/`, so they can never disagree.

- **36 Galaxy models**, 2024–2026 · 27 real / 9 projected · prices in **INR (₹)**
- **Weighted Sum Model** over four transparent 0–10 scores: camera, performance, battery, value
- **Runs fully offline.** No API key, no network, no database, no server. Gemini is an optional bonus that always falls back to the deterministic path.

## Run it

```bash
conda env create -f environment.yml
conda activate galaxy-pick
python scripts/build_dataset.py                  # writes data/processed/phones.csv
jupyter notebook notebooks/pj1_analysis.ipynb    # graded core
streamlit run app/streamlit_app.py               # demo UI
pytest -q                                        # tests
```

No API key is required. To enable the optional Gemini path, copy `.env.example` to `.env` and add a free Google AI Studio key — every call is wrapped in `try/except` and falls back to the rule-based path.

## How it works

```
curated_seed.csv  →  scoring.py  →  phones.csv  →  wsm.recommend()  →  top-3 + explain.reason()
   raw specs         4 scores       the catalog     filter → normalize      ranked, with a "why"
                                                    → weight → rank
```

| Module | Job |
|---|---|
| `config.py` | Paths, and `GEMINI_ENABLED` (True only if a key is actually present) |
| `data.py` | Load & validate `phones.csv`; provenance counts |
| `scoring.py` | Raw specs → four 0–10 scores |
| `personas.py` | The four personas and their weight vectors |
| `wsm.py` | Budget filter → normalize → weighted sum → rank → top-N |
| `nlp_parse.py` | Free text → `{weights, budget_max, form_factor, must_haves}` |
| `explain.py` | The one-line "why" for each pick |
| `cards.py` | Offline placeholder art (no external images needed) |

`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v`, with scores on 0–10 and weights summing to 1.

## Honesty about the data

- **2024–2025 (27 models) are real**, human-verified specs.
- **2026 (9 models) are projections**, flagged `spec_source=mock` everywhere — including in the recommendation text itself. They are *not* facts.
- **The scores are transparent heuristics, not benchmarks.** `camera_score` encodes our judgement about series optics; it is not DxOMark.

## Screenshots

_TODO — app screenshots (persona result, free-text result, provenance panel) land here once the UI is built._
