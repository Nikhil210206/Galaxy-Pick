# Galaxy-Pick

(A Capstone project for Samsung [SIC])

A Samsung Galaxy phone recommender. Pick a persona — or just type what you want in plain English — and get a **ranked top-3** with a one-line reason for each.

Built for the Samsung GenAI capstone (PJ1). The graded analytical core is the notebook; the demo is a Streamlit app. Both import the **same engine** from `src/recommender/`, so they can never disagree.

- **37 Galaxy models**, 2024–2026 · confirmed spec sheets · prices in **INR (₹)**
- **Weighted Sum Model** over four transparent 0–10 scores: camera, performance, battery, value
- **Runs fully offline.** No API key, no network, no database, no server. Gemini is an optional bonus that always falls back to the deterministic path.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python scripts/build_dataset.py                # writes data/processed/phones.csv
.venv/bin/python -m streamlit run app/streamlit_app.py   # demo UI
.venv/bin/python -m pytest -q                            # tests
.venv/bin/jupyter notebook notebooks/pj1_analysis.ipynb  # graded core
```

Prefer conda? `conda create -n galaxy-pick python=3.11 && conda activate galaxy-pick && pip install -r requirements-dev.txt`.

> **Two requirements files, on purpose.** `requirements.txt` is *runtime only* — the four things the app imports — because that's what a deploy host installs; matplotlib and Jupyter are ~78MB the app never touches. `requirements-dev.txt` adds those back for the notebook and the tests. Playwright is in neither: it's a dev-only browser check that downloads a ~150MB Chromium, so install it by hand when you need it.
>
> **Don't add an `environment.yml`.** Streamlit Community Cloud resolves dependency files `uv.lock` → `Pipfile` → `environment.yml` → `requirements.txt` and uses **only the first it finds** — a conda file at the root would silently hijack the deploy and install the entire dev stack.

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

## Deploy (free)

**Streamlit Community Cloud** — free for public apps, built by the Streamlit team, redeploys on every push. No card, no hosting fee (CLAUDE.md rule 1).

1. Push to GitHub (`main`).
2. Go to **[share.streamlit.io](https://share.streamlit.io)** → sign in with GitHub → **Create app** → **Deploy a public app from a repo**.
3. Fill in:
   - **Repository:** `Nikhil210206/Galaxy-Pick`
   - **Branch:** `main`
   - **Main file path:** `app/streamlit_app.py`   ← *not* the repo root
   - **Advanced settings → Python version:** **3.11**, 3.12 or 3.13. The code needs 3.11+ and uses no newer syntax. (Local dev may be on 3.14; don't assume the host offers it.)
4. **Deploy.** First build takes a few minutes.

**It just works offline-first.** No secrets are required: `config.GEMINI_ENABLED` is `False` without a key and every AI call falls back to the deterministic path (rule 2), which is also the graded one. `data/processed/phones.csv` and `app/assets/` are committed, so the host needs no build step.

**Optional — the Gemini path:** add `GEMINI_API_KEY = "..."` under **Settings → Secrets** in the Streamlit Cloud UI. Never commit a key: `.env` and `.streamlit/secrets.toml` are both gitignored. Verify `GEMINI_ENABLED` actually flips on the deployed app — `config.py` reads it via `os.getenv`, so confirm your host exposes secrets as environment variables before relying on it.

**Notes:** the free tier sleeps after inactivity and wakes on the next visit (a slow first load in a demo — open it a minute early). The runtime install is ~570MB against a ~1GB limit; ~163MB of that is the optional `google-generativeai` tree. It's kept because *without* it, adding a key later would fail **silently** — the import error gets swallowed by the fallback.

## Screenshots

_TODO — the UI is built (7 screens, ported from the Stitch design); drop PNGs of the persona result, the free-text result and the provenance panel in here._
