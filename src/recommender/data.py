# src/recommender/data.py — load & validate data/processed/phones.csv.
import pandas as pd

from . import config

REQUIRED_COLS = [
    "model_name", "series", "launch_year", "price_inr", "launch_price_inr", "price_source",
    "ram_gb", "storage_gb", "chipset", "rear_camera_mp", "battery_mah", "screen_size_inch",
    "refresh_rate_hz", "charging_w", "segment", "spec_source",
    "camera_score", "performance_score", "battery_score", "value_score", "image_ref",
]
PRICE_SOURCES = {"launch_msrp", "depreciation_model"}
SPEC_SOURCES = {"real", "mock"}
SCORE_COLS = ["camera_score", "performance_score", "battery_score", "value_score"]


def load_phones(path=None):
    """Read the processed catalog and validate it. Raises if the contract is broken."""
    path = path or config.PHONES_CSV
    df = pd.read_csv(path)
    validate(df)
    return df


def validate(df):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"phones.csv missing columns: {missing}")
    if not set(df["launch_year"]).issubset({2024, 2025, 2026}):
        raise ValueError("launch_year must be within {2024, 2025, 2026}")
    # 2026 rows were projections until the line actually shipped; they now carry confirmed
    # spec sheets, so the old "every 2026 row must be mock" rule no longer describes reality.
    # What still must hold: nothing claims to be real without a source, and anything still
    # projected is labelled so the UI can warn about it.
    if not set(df["spec_source"]).issubset(SPEC_SOURCES):
        raise ValueError(f"spec_source must be one of {SPEC_SOURCES}")
    for c in SCORE_COLS:
        if not df[c].between(0, 10).all():
            raise ValueError(f"{c} outside [0,10]")
    if df[["model_name", "price_inr", "chipset"]].isna().any().any():
        raise ValueError("nulls in required columns")
    if not set(df["price_source"]).issubset(PRICE_SOURCES):
        raise ValueError(f"price_source must be one of {PRICE_SOURCES}")
    if not (df["price_inr"] <= df["launch_price_inr"]).all():
        raise ValueError("price_inr (street estimate) cannot exceed launch_price_inr")
    return df


def provenance(df):
    """Counts for the Responsible-AI panel: how much of the catalog is projected, and how
    many prices are modelled rather than quoted."""
    return {
        "total": int(len(df)),
        "real": int((df["spec_source"] == "real").sum()),
        "mock": int((df["spec_source"] == "mock").sum()),
        "mock_years": sorted(df.loc[df["spec_source"] == "mock", "launch_year"].unique().tolist()),
        "modelled_prices": int((df["price_source"] == "depreciation_model").sum()),
    }
