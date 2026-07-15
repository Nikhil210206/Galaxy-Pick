# Galaxy-Pick

(A Capstone project for Samsung [SIC])

A Samsung Galaxy phone recommender. Pick a persona — or just type what you want in plain English — and get a **ranked top-3** with a one-line reason for each.

Built for the Samsung GenAI capstone (PJ1). The graded analytical core is the notebook; the demo is a Streamlit app. Both import the **same engine** from `src/recommender/`, so they can never disagree.

- **37 Galaxy models**, 2024–2026 · confirmed spec sheets · prices in **INR (₹)**
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

No conda? A venv works just as well — the project only needs the packages in `requirements.txt`:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/build_dataset.py
.venv/bin/python -m streamlit run app/streamlit_app.py
.venv/bin/python -m pytest -q
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
| `wsm.py` | Budget + hard spec filters → normalize → weighted sum → rank → top-N |
| `nlp_parse.py` | Free text → `{weights, budget_min, budget_max, form_factor, must_haves}` — "under 50k" is a ceiling, "around 20k" is a band |
| `explain.py` | The one-line "why" for each pick |
| `cards.py` | Offline placeholder art (no external images needed) |
| `app/theme.py` | Design tokens + CSS, ported from the Stitch project's `DESIGN.md` |

`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v`, with scores on 0–10 and weights summing to 1.

## Honesty about the data

Specs and prices have different provenance, and the app labels them separately.

- **Specs are confirmed for all 37 models** (`spec_source=real`). Nothing here is a projection. While the 2026 line was unreleased this catalog carried *modelled* specs for it; the real sheets later corrected several — the S26 runs an **Exynos 2600**, not the invented "Snapdragon 8 Elite Gen2"; the S26 Ultra is 5000 mAh / 60 W, not 5200 / 65. The disclosure machinery (⚠ badge, "hide projections" filter, a caveat in the reason text) is still in the engine for whatever gets projected next — modelled specs read exactly like real ones, which is the whole point of labelling them.
- **Prices are mixed, and labelled per row.** `launch_price_inr` is real MSRP everywhere. `price_inr` — the number shown, and the one `value_score` divides by — is real for the 10 models on sale now, and an **estimated street price** for the 27 older ones, modelled by depreciating MSRP by age (`price_source=depreciation_model`). It's an estimate, not a quote, and it's the least certain input in the model.
- **The scores are transparent heuristics, not benchmarks.** `camera_score` encodes our judgement about series optics; it is not DxOMark. `performance_score` is a chipset tier table, not a measured benchmark run.

## Screenshots

_TODO — the UI is built (7 screens, ported from the Stitch design); drop PNGs of the persona result, the free-text result and the provenance panel in here._
