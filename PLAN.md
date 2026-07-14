# PLAN.md — Galaxy-Pick Build Spec (Phases 0–5)

> **Audience:** the AI coding agent (Antigravity) + the 4-person team.
> **Goal:** build PJ1 — a Samsung Galaxy phone recommender — end to end, without errors.
> **Read `CLAUDE.md` first for the hard rules.** This file is the step-by-step build.

---

## 0. Overview & hard constraints (repeat of the rules that matter most)

- **Free/OSS only. No paid services.** Gemini is optional and free-tier only.
- **Deterministic-first:** the app runs fully **offline, no API key, no network**. Gemini is a bonus behind a flag + `try/except` fallback.
- **Recommendation logic = Weighted Sum Model (WSM).** No ML / RAG / embeddings / vector DB / backend / DB / auth.
- **Currency = INR.** **Dataset = 2024–2026**, one row per model, every 2026 row `spec_source=mock`.
- **The agent never commits.** The whole build lands as **one commit** (Section 10), which the human runs.

**Build order:** 0 → 1 → 2 → 4 → 5, then **3 last**.
Phase 2 (the notebook) is the **graded core** — once it's done the project is already pass-safe.
**Phase 3 (the UI) is deferred to the end**: it's the only phase blocked on an external artifact (the design is being done in Stitch), and nothing else depends on it. `app/streamlit_app.py` is a working, deliberately unstyled placeholder until that design lands.

---

## 1. Team split (Member 1–4)

Assign your 4 teammates to these four seats. Owners are primary; everyone helps on Day 1.

| Seat | Owns | Files |
|---|---|---|
| **Member 1 — Data** | Dataset + cleaning + provenance; co-owns EDA & screenshots | `scripts/build_dataset.py`, `data/processed/phones.csv`, `src/recommender/data.py` |
| **Member 2 — Engine** | Scoring, personas, WSM, the notebook's core sections, tests | `src/recommender/scoring.py`, `personas.py`, `wsm.py`, `notebooks/pj1_analysis.ipynb`, `tests/` |
| **Member 3 — UI** | Streamlit app, Samsung theme, cards, breakdown chart, accessibility | `app/streamlit_app.py`, `.streamlit/config.toml`, `src/recommender/cards.py` |
| **Member 4 — AI & Presentation** | NL parsing (Gemini + fallback), explanations, provenance panel, slides + demo | `src/recommender/nlp_parse.py`, `explain.py`, `presentation/` |

**Day-by-day (dependency-aware so nobody is blocked):**
- **Day 1 (Phase 0 + 1):** all-hands. Member 1 drives the dataset; 2/3/4 verify specs in parallel. **Freeze the `src/recommender/` function signatures (Section 11) this morning** so everyone codes to a stable interface. End of day → repo skeleton + `phones.csv`.
- **Day 2 (Phase 2):** Member 2 builds the notebook core → **pass-safe by EOD**. Member 1 finishes EDA + provenance. Member 3 builds the app skeleton + theme. Member 4 writes persona copy + the fallback parser + slide outline.
- **Day 3 (Phase 3 + 4):** Member 3 finishes the app on the shared engine. Member 2 wires the `src/` package + tests. Member 4 finishes NL parse + explanations + provenance panel. Member 1 handles data edge cases + starts screenshots.
- **Day 4 (Phase 5):** integration + polish. Pull in stretch features **only if green** (Member 3: weight sliders; Member 2: close-call flag). Member 4 builds the deck + demo script. Everyone tests.
- **Day 5 (buffer):** rehearse, run the fallback drill, capture final screenshots, finalize the deck.

---

## 2. Prerequisites
- Anaconda (or Miniconda) installed; `conda` on PATH.
- Python 3.11 (created by `environment.yml`).
- No API key required. *(Optional:* a free Google AI Studio key in `.env` unlocks the live Gemini path.)
- Copy the three source CSVs into `data/raw/` for reference (not required at runtime):
  `samsung_galaxy_dataset_2020_2026.csv`, `samsungMobilesData.csv`, `samsung_mobile_new_data.csv`.

---

## Phase 0 — Setup & skeleton  *(Owner: all; ~0.5 day)*

**Objective:** a clean repo skeleton + reproducible free/OSS environment.

**Create this tree:**
```
galaxy-pick/
├── CLAUDE.md            # already present
├── PLAN.md             # already present
├── README.md
├── environment.yml
├── requirements.txt
├── .gitignore
├── .env.example
├── .streamlit/config.toml
├── data/{raw/,processed/}
├── scripts/build_dataset.py
├── notebooks/pj1_analysis.ipynb
├── src/recommender/{__init__.py,config.py,data.py,scoring.py,personas.py,wsm.py,nlp_parse.py,explain.py,cards.py}
├── app/streamlit_app.py
├── assets/images/      # empty → code draws free placeholder cards
├── tests/{test_scoring.py,test_wsm.py}
└── presentation/
```

**`environment.yml`:**
```yaml
name: galaxy-pick
channels: [conda-forge]
dependencies:
  - python=3.11
  - pandas
  - numpy
  - matplotlib
  - jupyter
  - streamlit
  - pytest
  - python-dotenv
  - pip
  - pip:
      - google-generativeai   # optional; only used if a key is set
```

**`requirements.txt`** (pip mirror):
```
pandas
numpy
matplotlib
jupyter
streamlit
pytest
python-dotenv
google-generativeai
```

**`.gitignore`:**
```
__pycache__/
*.pyc
.env
.ipynb_checkpoints/
.streamlit/secrets.toml
```

**`.env.example`:**
```
# Optional. Leave blank to run 100% offline (deterministic mode).
GEMINI_API_KEY=
```

**`.streamlit/config.toml`** (Samsung theme):
```toml
[theme]
primaryColor = "#1428A0"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F5F6F8"
textColor = "#111111"
font = "sans serif"
```

**`README.md`:** short — what it is, the run commands from `CLAUDE.md`, and a screenshots placeholder.

**Acceptance:** `conda env create -f environment.yml` succeeds; `conda activate galaxy-pick`; `streamlit hello` opens.
*(No per-phase commit — the whole build lands as the single commit in Section 10.)*

---

## Phase 1 — Dataset  *(Owner: Member 1; ~1 day)*

**Objective:** one clean canonical `data/processed/phones.csv`, one row per model, 2024–2026, with the four scores + provenance.

### 1a. The curated raw dataset
Write the table in **Appendix A** verbatim to `data/raw/curated_seed.csv` (36 rows, header included). This is the source of truth for specs — do not invent or alter specs. It was Gemini-assisted then human-curated (see Appendix C for the generation prompt used, for your presentation story).

### 1b. `scripts/build_dataset.py`
Reads `curated_seed.csv`, computes the four scores with `src/recommender/scoring.py`, adds `image_ref`, validates, writes `data/processed/phones.csv`.

```python
# scripts/build_dataset.py
from pathlib import Path
import pandas as pd
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from recommender import scoring

RAW = Path("data/raw/curated_seed.csv")
OUT = Path("data/processed/phones.csv")

def main():
    df = pd.read_csv(RAW)
    df["camera_score"] = df.apply(lambda r: scoring.camera_score(r["rear_camera_mp"], r["series"]), axis=1)
    df["performance_score"] = df.apply(lambda r: scoring.performance_score(r["chipset"], r["ram_gb"], r["refresh_rate_hz"]), axis=1)
    df["battery_score"] = df.apply(lambda r: scoring.battery_score(r["battery_mah"], r["charging_w"], r["screen_size_inch"]), axis=1)
    df["value_score"] = scoring.value_score_column(df)
    df["image_ref"] = df.apply(lambda r: f"placeholder:{r['series']}:{r['model_name']}", axis=1)

    # validation
    assert 30 <= len(df) <= 50, f"unexpected row count {len(df)}"
    assert set(df["launch_year"]).issubset({2024, 2025, 2026})
    assert (df.loc[df.launch_year == 2026, "spec_source"] == "mock").all()
    for c in ["camera_score","performance_score","battery_score","value_score"]:
        assert df[c].between(0, 10).all(), f"{c} out of [0,10]"
    assert df[["model_name","price_inr","chipset"]].notna().all().all()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} — {len(df)} models "
          f"({(df.spec_source=='real').sum()} real / {(df.spec_source=='mock').sum()} mock)")

if __name__ == "__main__":
    main()
```

**Acceptance:** `python scripts/build_dataset.py` prints ~36 models (27 real / 9 mock) and all asserts pass.
*(No per-phase commit — see Section 10.)*

---

## Phase 2 — Notebook: the graded core  *(Owner: Member 2; ~1 day)*

**Objective:** `notebooks/pj1_analysis.ipynb` that satisfies brief Steps 5–8 and 10. This is what's graded — make it clean and narrated with markdown between code cells.

**Cell plan:**
1. **Intro (markdown):** problem, personas approach, that the dataset is curated + partly mock (Ch.4 honesty).
2. **Load** `data/processed/phones.csv`; show `.head()`, `.shape`, `.describe()`.
3. **EDA — write down exactly 3 findings** (brief Step 5), e.g.: (a) price range per `segment`; (b) which raw spec varies most across segments; (c) one surprise (e.g., budget M-series dominates `value_score`). Back each with a number or a small matplotlib chart.
4. **Feature engineering (markdown + code):** re-derive the four scores by importing `scoring.py` (don't re-implement). **Print the scoring logic** (brief Step 6 requires showing the logic, not just numbers) — paste the formula summary from Appendix B.
5. **Personas (markdown table):** the 4 personas + weight vectors from `personas.py`; confirm each sums to 1.0.
6. **WSM (code):** import `wsm.py`; show the formula; run the **worked example** (Appendix B.4) and print `= 7.5`.
7. **Recommend for each persona:** print top-3 per persona with match scores.
8. **Wrap-up (markdown):** 3 findings restated; one limitation (scores are heuristic; 2026 is projected).

**Acceptance:** *Restart & Run All* → no errors; worked example prints `7.5`; each persona shows a sensible in-budget top-3.
*(No per-phase commit — see Section 10.)*

---

## Phase 3 — Streamlit app  *(Owner: Member 3; ~1 day)*

**Objective:** `app/streamlit_app.py` — the Samsung-styled demo over the shared engine.

**Layout:**
- **Sidebar:** title "Galaxy-Pick"; a **persona `selectbox`**; a **free-text `text_input`** ("Describe what you want…"); a budget `slider` (₹10k–₹200k); an "Advanced: weight sliders" `expander` (stretch).
- **Main:** header; **top-3 cards** in 3 columns (placeholder image, model, price, match-score badge, a matplotlib **score-breakdown bar**, one-line "why"); below that a full ranked `dataframe`; a **"Data provenance & limitations" `expander`** (real vs. mock counts, "scores are heuristic", 2026 projected).

**Key behaviour:** if the free-text box is non-empty → `nlp_parse.parse(text)`; else use the selected persona's weights/budget. Then `wsm.recommend(...)` → `explain.reason(...)` per card. Placeholder card = a coloured block by `series` with the model name (see `cards.py`), so **no external images are needed**.

```python
# src/recommender/cards.py — free, offline placeholder image
SERIES_COLOR = {"S":"#1428A0","S-Ultra":"#0C1E7F","S-FE":"#3B5BDB","Z-Flip":"#7048E8",
                "Z-Fold":"#5F3DC4","A":"#1098AD","M":"#0CA678","F":"#E8590C"}
def placeholder_svg(model_name, series):
    color = SERIES_COLOR.get(series, "#1428A0")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="220" height="300">
      <rect width="220" height="300" rx="24" fill="{color}"/>
      <rect x="24" y="24" width="172" height="252" rx="16" fill="#ffffff" opacity="0.10"/>
      <text x="110" y="160" fill="#fff" font-size="15" font-family="sans-serif"
            text-anchor="middle">{model_name}</text>
    </svg>'''
```

**Acceptance:** `streamlit run app/streamlit_app.py`; picking each persona shows the **same top-3 as the notebook**; free-text "photography under ₹50k" → camera-weighted, all ≤ ₹50k.
*(No per-phase commit — see Section 10.)*

---

## Phase 4 — AI layer + Responsible AI  *(Owner: Member 4; ~0.5–1 day)*

**Objective:** natural-language persona parsing (the one on-theme AI feature) that **always works offline**, plus the provenance panel.

**`nlp_parse.py` contract:** `parse(text) -> {"weights": {...4 keys sum→1}, "budget_max": int|None, "form_factor": "any|compact|foldable", "must_haves": [str]}`.
- If `config.GEMINI_ENABLED`: call Gemini with the Appendix C prompt, parse JSON, **validate** (all 4 weight keys, renormalize to sum 1.0, clamp budget to [5000, 200000]); on **any** exception or invalid output → fall back.
- **Deterministic fallback (default):** start `{camera:.25, performance:.25, battery:.25, value:.25}`; keyword boosts (+0.3): camera/photo/photography/pictures→camera; game/gaming/fps/performance/fast/smooth→performance; battery/backup/long-lasting/charge→battery; cheap/budget/value/affordable/worth→value. Regex `under|below ₹?\s?(\d+)\s?k?` → `budget_max`. "compact/small"→compact; "fold/flip/foldable"→foldable. Renormalize weights to sum 1.0.

**`explain.py`:** template — `"Great for {persona/goal}: strong {top_factor} ({s}/10) and {second_factor} ({s}/10), and at ₹{price:,} it fits your budget."` Add a **close-call note** when `top1.match - top2.match < 0.3`. Optional Gemini polish behind the same flag + fallback to the template.

**Responsible-AI panel (in the app):** show `real` vs `mock` counts, "Scores are transparent heuristics, not benchmarks," and "2026 models are projections." This is a graded Ch.4 asset — make it visible.

**Acceptance (the fallback drill — critical):** with **no** `GEMINI_API_KEY` and Wi-Fi **off**, free-text parsing + explanations still produce correct results. Bad input (empty / gibberish) → neutral weights, no crash.
*(No per-phase commit — see Section 10.)*

---

## Phase 5 — Polish, tests, presentation  *(Owner: all; ~0.5–1 day)*

- **Tests** (`tests/`): see Appendix D. `pytest -q` must be green.
- **Stretch (only if green):** live **weight sliders** (Member 3); **close-call flag** surfaced in the UI (Member 2).
- **Screenshots:** capture the app (persona result + free-text result + provenance panel) into `presentation/`.
- **Slide deck (brief Step 10):** personas; the WSM formula + the `7.5` worked example; a UI screenshot; the 3 EDA findings; one honest "where the AI needed guarding" note (Ch.4). Add the Appendix C Gemini prompt as your "how we made the dataset" slide.
- **Commit:** *(none per-phase — see Section 10.)*

---

## 10. The commit (the human runs this; the agent only prints it)

**One commit for the whole build.** The agent never commits and must not appear in author history.

```
feat: add Galaxy-Pick — persona-driven Galaxy phone recommender

Ranks 36 Galaxy models (2024-2026) for a shopper persona or a plain-English
request, returning a top-3 with a one-line reason for each. Runs fully offline:
no key, no network, no server, no database.

- data:     curated 2024-2026 seed (27 real / 9 projected, every 2026 row
            flagged spec_source=mock) -> phones.csv, built and validated by
            scripts/build_dataset.py
- engine:   src/recommender/ is the single source of truth, imported by both
            the notebook and the app: spec->score heuristics, four personas,
            and the Weighted Sum Model
- notebook: EDA (3 findings), feature engineering, personas, and the WSM
            worked example (7.5); runs top-to-bottom
- ai:       free-text parsing via Gemini when a key is present, deterministic
            keyword/regex parser otherwise; every call falls back, so the demo
            never depends on the network
- tests:    33 passing, including the offline fallback drill

The data forced two fixes to the scoring model:

camera_score ranks on series optics tier rather than megapixels. rear_camera_mp
takes only two values across the catalog (50 and 200) and every 200MP phone
costs >= Rs 1,39,999, so megapixels could not tell any two cameras apart below
that price -- and the WSM rated the cheapest phone the best for photography.

wsm.recommend() normalizes the in-budget pool before weighting. Influence in a
weighted sum is weight x spread, and value_score spanned the full 0-10 while
camera spanned ~3, so value outvoted camera at 2.5x less weight and every
persona collapsed onto the cheapest phone. match_scores() is unchanged, so the
7.5 worked example still holds.
```

*(The UI is not in this commit — Phase 3 is deferred until the Stitch design lands; `app/streamlit_app.py` is a working placeholder.)*

---

## 11. Frozen function signatures (agree Day 1; everyone codes to these)
```python
# scoring.py
def camera_score(rear_camera_mp: int, series: str) -> float
def performance_score(chipset: str, ram_gb: int, refresh_rate_hz: int) -> float
def battery_score(battery_mah: int, charging_w: int, screen_size_inch: float) -> float
def value_score_column(df) -> "pd.Series"   # needs the 3 other scores + price_inr

# personas.py
PERSONAS: dict          # name -> {"story", "weights", "budget_max"}

# wsm.py
def normalize_scores(df) -> "pd.DataFrame"   # all 4 criteria onto a common 0–10 scale
def match_scores(df, weights: dict) -> "pd.Series"
def recommend(df, weights: dict, budget_max: int | None = None,
              form_factor: str | None = None, top_n: int = 3) -> "pd.DataFrame"

# data.py
def load_phones(path=None) -> "pd.DataFrame"   # reads phones.csv AND validates it
def validate(df) -> "pd.DataFrame"             # raises if the row contract is broken
def provenance(df) -> dict                     # {"total","real","mock","mock_years"}

# cards.py
def placeholder_svg(model_name: str, series: str) -> str

# nlp_parse.py
def parse(text: str) -> dict   # {"weights","budget_max","form_factor","must_haves"}

# explain.py
def reason(row, weights: dict, persona_label: str | None = None,
           close_call: bool = False) -> str

# config.py
GEMINI_ENABLED: bool           # True only if GEMINI_API_KEY is set
```

---

# Appendix A — `data/raw/curated_seed.csv` (write verbatim)

```csv
model_name,series,launch_year,price_inr,ram_gb,storage_gb,chipset,rear_camera_mp,battery_mah,screen_size_inch,refresh_rate_hz,charging_w,segment,spec_source
Galaxy S24,S,2024,87559,8,256,Exynos 2400,50,4000,6.2,120,25,business,real
Galaxy S24+,S,2024,107559,8,256,Exynos 2400,50,4900,6.7,120,45,business,real
Galaxy S24 Ultra,S-Ultra,2024,147559,12,256,Snapdragon 8 Gen3,200,5000,6.8,120,45,photography,real
Galaxy S24 FE,S-FE,2024,67559,8,256,Exynos 2400e,50,4700,6.7,120,25,gaming,real
Galaxy Z Flip6,Z-Flip,2024,117559,8,256,Snapdragon 8 Gen3,50,4000,6.7,120,25,business,real
Galaxy Z Fold6,Z-Fold,2024,172559,8,256,Snapdragon 8 Gen3,50,4400,7.6,120,25,business,real
Galaxy S25,S,2025,88559,8,256,Snapdragon 8 Elite,50,4000,6.2,120,25,business,real
Galaxy S25+,S,2025,107559,8,256,Snapdragon 8 Elite,50,4900,6.7,120,45,business,real
Galaxy S25 Ultra,S-Ultra,2025,147559,12,256,Snapdragon 8 Elite,200,5000,6.9,120,45,photography,real
Galaxy Z Flip7,Z-Flip,2025,122559,8,256,Snapdragon 8 Elite,50,4300,6.8,120,25,business,real
Galaxy Z Fold7,Z-Fold,2025,182559,8,256,Snapdragon 8 Elite,200,4600,8.0,120,25,business,real
Galaxy A15 5G,A,2024,14999,6,128,Dimensity 6100+,50,5000,6.5,90,25,budget,real
Galaxy A25 5G,A,2024,19999,8,128,Exynos 1280,50,5000,6.5,120,25,budget,real
Galaxy A35 5G,A,2024,26999,8,128,Exynos 1380,50,5000,6.6,120,25,business,real
Galaxy A55 5G,A,2024,35999,8,128,Exynos 1480,50,5000,6.6,120,25,business,real
Galaxy M15 5G,M,2024,12999,6,128,Dimensity 6100+,50,6000,6.5,90,25,budget,real
Galaxy M35 5G,M,2024,18999,8,128,Exynos 1380,50,6000,6.6,120,25,budget,real
Galaxy M55 5G,M,2024,26999,8,128,Snapdragon 7 Gen1,50,5000,6.7,120,45,gaming,real
Galaxy F15 5G,F,2024,12499,6,128,Dimensity 6100+,50,6000,6.5,90,25,budget,real
Galaxy F55 5G,F,2024,26999,8,128,Snapdragon 7 Gen1,50,5000,6.7,120,45,gaming,real
Galaxy A16 5G,A,2025,16999,6,128,Dimensity 6300,50,5000,6.7,90,25,budget,real
Galaxy A26 5G,A,2025,21999,8,128,Exynos 1380,50,5000,6.7,120,25,budget,real
Galaxy A36 5G,A,2025,26999,8,128,Snapdragon 6 Gen3,50,5000,6.7,120,45,business,real
Galaxy A56 5G,A,2025,35999,8,128,Exynos 1580,50,5000,6.7,120,45,business,real
Galaxy M16 5G,M,2025,13999,6,128,Dimensity 6300,50,6000,6.7,90,25,budget,real
Galaxy M56 5G,M,2025,27999,8,128,Exynos 1580,50,5000,6.7,120,45,gaming,real
Galaxy F16 5G,F,2025,13499,6,128,Dimensity 6300,50,6000,6.7,90,25,budget,real
Galaxy S26,S,2026,89999,12,256,Snapdragon 8 Elite Gen2,50,4300,6.3,120,45,business,mock
Galaxy S26+,S,2026,109999,12,256,Snapdragon 8 Elite Gen2,50,4900,6.7,120,45,business,mock
Galaxy S26 Ultra,S-Ultra,2026,139999,12,512,Snapdragon 8 Elite Gen2,200,5200,6.9,120,65,photography,mock
Galaxy S26 FE,S-FE,2026,62999,8,128,Exynos 2500,50,4900,6.7,120,45,gaming,mock
Galaxy Z Flip8,Z-Flip,2026,119999,12,256,Snapdragon 8 Elite Gen2,50,4400,6.9,120,25,business,mock
Galaxy Z Fold8,Z-Fold,2026,184999,12,256,Snapdragon 8 Elite Gen2,200,4800,8.2,120,25,business,mock
Galaxy A57 5G,A,2026,37999,8,256,Exynos 1680,50,5000,6.7,120,45,business,mock
Galaxy A17 5G,A,2026,17999,6,128,Dimensity 6400,50,5000,6.7,90,25,budget,mock
Galaxy M57 5G,M,2026,28999,8,128,Exynos 1580,50,5000,6.7,120,45,gaming,mock
```
*36 rows: 27 real (2024–25) + 9 mock (2026). Prices are representative base MRP in INR.*

---

# Appendix B — Scoring formulas & personas (the source of truth)

### B.1 `scoring.py` (write verbatim)
```python
# src/recommender/scoring.py — deterministic, explainable spec → 0–10 scores.
CHIPSET_TIER = {
    "Snapdragon 8 Elite Gen2": 9.7,   # 2026 (mock)
    "Snapdragon 8 Elite": 9.5, "Snapdragon 8 Gen3": 9.2, "Snapdragon 8 Gen2": 8.9,
    "Exynos 2500": 8.7,               # 2026 (mock)
    "Exynos 2400": 8.5, "Exynos 2400e": 8.1,
    "Snapdragon 7 Gen1": 6.3, "Exynos 1680": 6.2,   # 1680 = 2026 (mock)
    "Exynos 1580": 6.0, "Exynos 1480": 5.6, "Snapdragon 6 Gen3": 5.4,
    "Exynos 1380": 5.2, "Exynos 1280": 4.6,
    "Dimensity 6400": 4.4,            # 2026 (mock)
    "Dimensity 6300": 4.2, "Dimensity 6100+": 4.0,
}
CHIPSET_DEFAULT = 4.0

# Optics tier is the PRIMARY camera signal, not megapixels — see the note below.
SERIES_OPTICS = {"S-Ultra": 9.0, "S": 8.0, "Z-Fold": 7.6, "S-FE": 7.2,
                 "Z-Flip": 7.0, "A": 5.8, "M": 5.2, "F": 5.0}
SERIES_OPTICS_DEFAULT = 5.0

def _clamp(x, lo=0.0, hi=10.0):
    return round(float(max(lo, min(hi, x))), 1)

def camera_score(rear_camera_mp, series):
    mp = rear_camera_mp
    base = SERIES_OPTICS.get(series, SERIES_OPTICS_DEFAULT)
    mp_bonus = 0.0 if mp <= 12 else 0.2 if mp <= 50 else 0.4 if mp <= 64 else 0.7 if mp <= 108 else 1.0
    return _clamp(base + mp_bonus)

def performance_score(chipset, ram_gb, refresh_rate_hz):
    base = CHIPSET_TIER.get(chipset, CHIPSET_DEFAULT)
    ram_bonus = max(-0.3, min(0.6, (ram_gb - 8) * 0.15))
    refresh_bonus = 0.3 if refresh_rate_hz >= 120 else 0.0
    return _clamp(base + ram_bonus + refresh_bonus)

def battery_score(battery_mah, charging_w, screen_size_inch):
    base = 5.0 + (battery_mah - 3700) / 2300.0 * 4.5
    charge_bonus = 0.6 if charging_w >= 45 else 0.0
    screen_penalty = -0.4 if screen_size_inch >= 7.0 else 0.0
    return _clamp(base + charge_bonus + screen_penalty)

def value_score_column(df):
    # emergent: spec-points per ₹10k, min-max scaled to 0–10 across the catalog
    raw = (df["camera_score"] + df["performance_score"] + df["battery_score"]) / (df["price_inr"] / 10000.0)
    lo, hi = raw.min(), raw.max()
    return ((raw - lo) / (hi - lo) * 10).round(1)
```

> **Why optics and not megapixels (this changed the model — keep it for the Ch.4 slide).**
> `rear_camera_mp` takes only **two distinct values across all 36 phones** (50 and 200), 31 of them 50MP, and every 200MP phone costs **≥ ₹1,39,999**. Scoring on megapixels therefore said a ₹12,499 F15 and a ₹87,559 S24 have the same camera, and couldn't separate *any* two phones below ₹1.4 lakh. A criterion that never varies can't influence a ranking, so `value_score` decided every persona by default and the WSM rated **the cheapest phone in the catalog as the best photography phone**. What actually differs between these cameras is sensor size, OIS, zoom and ISP — and those track the series tier, so that's what leads now, with MP demoted to a small bonus.

### B.2 Plain-English logic (paste into the notebook + slides)
- **camera_score:** series optics tier (Ultra 9.0 → S 8.0 → Fold 7.6 → FE 7.2 → Flip 7.0 → A 5.8 → M 5.2 → F 5.0) + a small megapixel bonus (50→+0.2, 64→+0.4, 108→+0.7, 200→+1.0). *Caveat: MP ≠ image quality, which is exactly why optics leads — but the tier is still our judgement, not a lab test.*
- **performance_score:** chipset tier (flagship Snapdragon/Exynos high, entry Dimensity/Exynos low) + RAM adjustment (6/8/12 GB → −0.3/0/+0.6) + 0.3 for 120 Hz.
- **battery_score:** capacity scaled 3700→6000 mAh onto 5.0→9.5, + 0.6 for ≥45 W charging, − 0.4 for big ≥7″ foldable screens.
- **value_score:** *emergent* — (camera+performance+battery) per ₹10,000, min-max scaled 0–10. Budget M/F models score high; flagships score low.

### B.3 Personas (`personas.py`, write verbatim — each weight vector sums to 1.0)
```python
# src/recommender/personas.py
PERSONAS = {
    "Priya — Photography enthusiast": {
        "story": "24, shoots daily. Wants the best camera; screen matters; gaming doesn't.",
        "weights": {"camera": 0.50, "performance": 0.10, "battery": 0.20, "value": 0.20},
        "budget_max": 80000},
    "Arjun — Mobile gamer": {
        "story": "21, competitive gamer. Raw performance + battery for long sessions.",
        "weights": {"camera": 0.10, "performance": 0.50, "battery": 0.30, "value": 0.10},
        "budget_max": 85000},
    "Meera — Budget-conscious student": {
        "story": "19, saving hard. Value-for-money and all-day battery on a tight budget.",
        "weights": {"camera": 0.15, "performance": 0.20, "battery": 0.30, "value": 0.35},
        "budget_max": 20000},
    "Rahul — Business all-rounder": {
        "story": "34, professional. Balanced, premium, reliable; strong battery + camera.",
        "weights": {"camera": 0.25, "performance": 0.30, "battery": 0.25, "value": 0.20},
        "budget_max": 140000},
}
```

### B.4 WSM + worked example
`match_score = camera×w_c + performance×w_p + battery×w_b + value×w_v`
Worked example (Priya, weights 0.5/0.1/0.2/0.2; a phone scoring camera=9, performance=6, battery=7, value=5):
`= 9×0.5 + 6×0.1 + 7×0.2 + 5×0.2 = 4.5 + 0.6 + 1.4 + 1.0 = 7.5`  → used in `test_wsm.py`.

> **The weighted sum needs normalized criteria (this also changed the model — Ch.4 slide material).**
> A criterion's real influence in a weighted sum is **weight × spread**, not weight alone. The four raw scores don't share a spread: `value_score` is min–max scaled and uses the full 0–10, while `camera_score` spans ~3. So value swung the ranking by **2.00** at weight 0.20 while camera swung it by only **1.50** at weight 0.50 — **value outvoted camera at 2.5× less weight**, and Priya (photography) and Meera (budget) got *identical* top-3s. The fix is standard multi-criteria decision analysis: **normalize the decision matrix** — the alternatives actually being compared, i.e. the in-budget pool — before applying weights. `match_scores()` stays a pure dot product, so the `7.5` worked example is unaffected. Raw scores are still what we *display*: "camera 7.4/10" is meaningful to a shopper, a pool-relative `0.0` is not.

```python
# src/recommender/wsm.py
SCORE_COLS = ["camera_score", "performance_score", "battery_score", "value_score"]
FACTORS = ["camera", "performance", "battery", "value"]
NEUTRAL_NORM = 5.0      # what a criterion is worth when every option ties on it

def normalize_scores(df):
    """Put all four criteria on a common 0–10 scale across the rows given."""
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
    # rank on the normalized pool, hand back the raw scores for display
    pool = pool.assign(match_score=match_scores(normalize_scores(pool), weights))
    return pool.sort_values("match_score", ascending=False).head(top_n)
```

**Expected top-3 (regenerate with the notebook if the data changes):**

| Persona | Top-3 |
|---|---|
| Priya — photography (≤₹80k) | S26 FE · S24 FE · M15 5G |
| Arjun — gamer (≤₹85k) | S26 FE · M35 5G · S24 FE |
| Meera — student (≤₹20k) | M15 5G · F15 5G · M35 5G |
| Rahul — business (≤₹1.4L) | S26 Ultra · S26+ · S25+ |
| *free text:* "photography under ₹50k" | A57 5G · A56 5G · A36 5G |

---

# Appendix C — Gemini dataset-generation prompt (for the presentation "how we made the data" slide)

> This is the prompt used to seed the mock portion; the team then human-curated the output into Appendix A. Include it to show Ch.2 prompt engineering.

```
Role: You are a mobile product data analyst.
Task: Generate a markdown table of Samsung Galaxy phones launched 2024–2026 with columns:
model_name, series, launch_year, price_inr, ram_gb, storage_gb, chipset, rear_camera_mp,
battery_mah, screen_size_inch, refresh_rate_hz, charging_w, target_segment.
Constraints:
- One row per model (no colour/storage variants).
- Cover budget (A/M/F), mid-range, flagship (S), and foldables (Z Flip/Fold).
- Use realistic 2024–2025 specs; for 2026 give plausible projected specs and mark them.
- target_segment ∈ {budget, gaming, business, photography}.
- Prices in INR, no phone above ₹200000 or below ₹10000.
Output: the markdown table only.
```
**Ch.4 note:** we did **not** trust the model blindly — we corrected chipset/price errors, deduplicated, and flagged every 2026 row as `spec_source=mock`.

### Optional live-parse prompt (`nlp_parse.py`, only if a key is set)
```
Convert the shopper request into JSON only (no prose), matching:
{"weights":{"camera":0-1,"performance":0-1,"battery":0-1,"value":0-1},
 "budget_max": <int INR or null>, "form_factor":"any|compact|foldable", "must_haves":[str]}
Rules: the four weights must sum to 1.0; if a need is unstated use 0.25 each; "50k"=50000.
Example: "best camera phone under 60k" ->
{"weights":{"camera":0.55,"performance":0.15,"battery":0.15,"value":0.15},
 "budget_max":60000,"form_factor":"any","must_haves":["camera"]}
Request: "<USER_TEXT>" ->
```

---

# Appendix D — Tests (write verbatim)
```python
# tests/test_scoring.py
import pandas as pd
from src.recommender import scoring

def test_scores_bounded_on_catalog():
    df = pd.read_csv("data/processed/phones.csv")
    for c in ["camera_score","performance_score","battery_score","value_score"]:
        assert df[c].between(0,10).all()

def test_camera_flagship_beats_budget():
    assert scoring.camera_score(200,"S-Ultra") > scoring.camera_score(50,"A")

def test_performance_monotonic_in_tier():
    assert scoring.performance_score("Snapdragon 8 Elite",8,120) > \
           scoring.performance_score("Dimensity 6300",8,120)
```
```python
# tests/test_wsm.py
import pandas as pd
from src.recommender import wsm, personas

def test_persona_weights_sum_to_one():
    for p in personas.PERSONAS.values():
        assert abs(sum(p["weights"].values()) - 1.0) < 1e-9

def test_worked_example_equals_7_5():
    df = pd.DataFrame([{"camera_score":9,"performance_score":6,"battery_score":7,"value_score":5}])
    w = {"camera":0.5,"performance":0.1,"battery":0.2,"value":0.2}
    assert float(wsm.match_scores(df, w).iloc[0]) == 7.5

def test_recommend_respects_budget():
    df = pd.read_csv("data/processed/phones.csv")
    w = {"camera":0.25,"performance":0.25,"battery":0.25,"value":0.25}
    out = wsm.recommend(df, w, budget_max=20000, top_n=3)
    assert (out["price_inr"] <= 20000).all() and len(out) <= 3
```

**Plus regression guards for the two model fixes** (in `tests/`, see the files themselves):
`test_camera_ranks_by_optics_not_megapixels`, `test_camera_discriminates_across_the_catalog`,
`test_normalize_puts_criteria_on_a_common_scale`, `test_normalize_is_neutral_when_a_criterion_cannot_discriminate`,
`test_personas_produce_distinct_recommendations`, `test_camera_persona_picks_the_best_camera_in_budget`,
`test_budget_persona_still_picks_on_value` — these fail if the WSM ever collapses onto "cheapest phone" again.
`tests/test_nlp_parse.py` runs the **fallback drill** as tests (bad input → neutral weights, no crash;
"photography under ₹50k" → camera-weighted and in budget; mock rows disclosed in the reason text).
A root `conftest.py` puts the repo root on `sys.path` so `from src.recommender import ...` resolves and
the relative `data/processed/phones.csv` paths work from anywhere. **33 tests.**

---

# Appendix E — Verification checklist (run before the presentation)
- [ ] `python scripts/build_dataset.py` → 36 rows (27 real / 9 mock), all asserts pass.
- [ ] Notebook *Restart & Run All* → no errors; worked example prints `7.5`; 3 EDA findings written.
- [ ] `streamlit run app/streamlit_app.py` → each persona's top-3 matches the notebook (see the B.4 table); "photography under ₹50k" → A57/A56/A36, all ≤ ₹50k.
- [ ] **Fallback drill:** unset `GEMINI_API_KEY` + Wi-Fi off → free-text + explanations still work.
- [ ] `pytest -q` → green (33).
- [ ] Screenshots captured; deck has personas, WSM + `7.5`, UI shot, 3 findings, one Ch.4 note.

**Environment gotcha (hit on the dev machine):** the plan assumes Anaconda. If `conda` isn't on PATH, install Miniconda — a bare system Python may have a numpy blocked by Windows Application Control, which breaks pandas on import.
