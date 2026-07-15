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

    # The seed's price_inr is launch MSRP. Age it to CATALOG_YEAR: price_inr becomes what a
    # shopper would actually pay today, and the MSRP is kept so the UI can show the drop.
    df = df.rename(columns={"price_inr": "launch_price_inr"})
    df["price_inr"] = df.apply(
        lambda r: scoring.current_price_inr(r["launch_price_inr"], r["launch_year"], r["series"]), axis=1)
    df["price_source"] = df["launch_year"].map(
        lambda y: "launch_msrp" if y >= scoring.CATALOG_YEAR else "depreciation_model")

    df["camera_score"] = df.apply(lambda r: scoring.camera_score(r["rear_camera_mp"], r["series"], r["launch_year"]), axis=1)
    df["performance_score"] = df.apply(lambda r: scoring.performance_score(r["chipset"], r["ram_gb"], r["refresh_rate_hz"]), axis=1)
    df["battery_score"] = df.apply(lambda r: scoring.battery_score(r["battery_mah"], r["charging_w"], r["screen_size_inch"]), axis=1)
    df["value_score"] = scoring.value_score_column(df)   # reads the aged price, not MSRP
    df["image_ref"] = df.apply(lambda r: f"placeholder:{r['series']}:{r['model_name']}", axis=1)

    # validation
    assert 30 <= len(df) <= 50, f"unexpected row count {len(df)}"
    assert set(df["launch_year"]).issubset({2024, 2025, 2026})
    # An unknown chipset scores CHIPSET_DEFAULT (the lowest tier) rather than raising, so a
    # typo or a new silicon generation would quietly rank a flagship last. Fail loudly.
    unknown = sorted(set(df["chipset"]) - set(scoring.CHIPSET_TIER))
    assert not unknown, f"chipsets missing from CHIPSET_TIER (would score {scoring.CHIPSET_DEFAULT}): {unknown}"
    for c in ["camera_score", "performance_score", "battery_score", "value_score"]:
        assert df[c].between(0, 10).all(), f"{c} out of [0,10]"
    assert df[["model_name", "price_inr", "chipset"]].notna().all().all()
    assert (df["price_inr"] <= df["launch_price_inr"]).all(), "aged price above MSRP"
    assert (df.loc[df.launch_year == scoring.CATALOG_YEAR, "price_inr"]
            == df.loc[df.launch_year == scoring.CATALOG_YEAR, "launch_price_inr"]).all(), \
        "current-year models must sit at MSRP"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT, index=False)
    print(f"Wrote {OUT} — {len(df)} models "
          f"({(df.spec_source=='real').sum()} real / {(df.spec_source=='mock').sum()} mock)")


if __name__ == "__main__":
    main()
