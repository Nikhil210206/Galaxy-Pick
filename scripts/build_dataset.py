# scripts/build_dataset.py
from pathlib import Path
import pandas as pd
import sys
sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))
from recommender import scoring

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/curated_seed.csv"
OUT = ROOT / "data/processed/phones.csv"


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
    for c in ["camera_score", "performance_score", "battery_score", "value_score"]:
        assert df[c].between(0, 10).all(), f"{c} out of [0,10]"
    assert df[["model_name", "price_inr", "chipset"]].notna().all().all()

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} — {len(df)} models "
          f"({(df.spec_source=='real').sum()} real / {(df.spec_source=='mock').sum()} mock)")


if __name__ == "__main__":
    main()
