# src/recommender/data.py — load & validate data/processed/phones.csv.
import pandas as pd

from . import config

REQUIRED_COLS = [
    "model_name", "series", "launch_year", "price_inr", "ram_gb", "storage_gb",
    "chipset", "rear_camera_mp", "battery_mah", "screen_size_inch",
    "refresh_rate_hz", "charging_w", "segment", "spec_source",
    "camera_score", "performance_score", "battery_score", "value_score", "image_ref",
]
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
    if not (df.loc[df["launch_year"] == 2026, "spec_source"] == "mock").all():
        raise ValueError("every 2026 row must be spec_source=mock")
    for c in SCORE_COLS:
        if not df[c].between(0, 10).all():
            raise ValueError(f"{c} outside [0,10]")
    if df[["model_name", "price_inr", "chipset"]].isna().any().any():
        raise ValueError("nulls in required columns")
    return df


def provenance(df):
    """Counts for the Responsible-AI panel: how much of the catalog is projected."""
    return {
        "total": int(len(df)),
        "real": int((df["spec_source"] == "real").sum()),
        "mock": int((df["spec_source"] == "mock").sum()),
        "mock_years": sorted(df.loc[df["spec_source"] == "mock", "launch_year"].unique().tolist()),
    }
