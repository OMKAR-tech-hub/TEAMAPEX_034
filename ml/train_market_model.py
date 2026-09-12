"""
AGMARKNET Market Price Forecasting Model
Trains a lightweight Random Forest on price time-series features.

DATA: Uses demo/synthetic data by default.
Real data: download from data.gov.in AGMARKNET and pass via --data-path

IMPORTANT: This model predicts regional commodity price trends, NOT individual
farmer creditworthiness or loan default probability.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
import joblib
from datetime import datetime
import json

MODEL_PATH = os.path.join(os.path.dirname(__file__), "models", "market_price_model.joblib")
META_PATH  = os.path.join(os.path.dirname(__file__), "models", "market_price_model_meta.json")


# ─────────────────────────────────────────────
# 1. Build/load dataset
# ─────────────────────────────────────────────

def build_demo_dataset() -> pd.DataFrame:
    """
    Generate a synthetic AGMARKNET-style dataset for training.
    In real use, replace with actual CSV from data.gov.in.
    """
    np.random.seed(42)
    crops = {
        "wheat":   (2100, 120),
        "rice":    (2000, 150),
        "soybean": (4300, 300),
        "cotton":  (6200, 400),
        "maize":   (1850, 100),
    }
    records = []
    for crop, (base_price, volatility) in crops.items():
        # 3 years of weekly data
        for week in range(156):
            trend = week * 1.5  # slight upward trend
            seasonal = base_price * 0.05 * np.sin(2 * np.pi * week / 52)
            noise = np.random.normal(0, volatility * 0.3)
            price = base_price + trend + seasonal + noise
            records.append({
                "crop": crop,
                "week": week,
                "year": 2024 + week // 52,
                "modal_price": max(500, round(price, 2)),
            })

    df = pd.DataFrame(records)
    print(f"Demo dataset: {len(df)} records, {df['crop'].nunique()} crops")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create time-series features for price prediction.
    """
    df = df.sort_values(["crop", "week"]).copy()
    df_features = []

    for crop in df["crop"].unique():
        subset = df[df["crop"] == crop].copy().reset_index(drop=True)
        prices = subset["modal_price"]

        # Lag features
        subset["lag_1"]  = prices.shift(1)
        subset["lag_7"]  = prices.shift(7)
        subset["lag_14"] = prices.shift(14)

        # Rolling statistics
        subset["rolling_mean_4w"] = prices.rolling(4).mean()
        subset["rolling_std_4w"]  = prices.rolling(4).std()
        subset["rolling_mean_8w"] = prices.rolling(8).mean()

        # Price trend (pct change over 4 weeks)
        subset["price_trend_4w"] = prices.pct_change(4)

        # Crop encoding (ordinal for RF)
        crop_map = {"wheat": 0, "rice": 1, "soybean": 2, "cotton": 3, "maize": 4}
        subset["crop_encoded"] = crop_map.get(crop, 5)

        df_features.append(subset)

    result = pd.concat(df_features).dropna()
    return result


# ─────────────────────────────────────────────
# 2. Train
# ─────────────────────────────────────────────

def train():
    print("=" * 50)
    print("KisanSetu Market Price Model Training")
    print("=" * 50)

    # Load data
    data_path = os.path.join(os.path.dirname(__file__), "data", "agmarknet_demo.csv")
    if os.path.exists(data_path):
        print(f"Loading real data from {data_path}")
        df = pd.read_csv(data_path)
    else:
        print("Using DEMO/SYNTHETIC dataset (no real data CSV found)")
        df = build_demo_dataset()
        # Save demo CSV for reference
        os.makedirs(os.path.dirname(data_path), exist_ok=True)
        df.to_csv(data_path, index=False)
        print(f"Demo data saved to {data_path}")

    df_feat = engineer_features(df)
    print(f"Features engineered: {len(df_feat)} samples, {df_feat.shape[1]} columns")

    feature_cols = [
        "lag_1", "lag_7", "lag_14",
        "rolling_mean_4w", "rolling_std_4w", "rolling_mean_8w",
        "price_trend_4w", "crop_encoded", "week",
    ]
    X = df_feat[feature_cols]
    y = df_feat["modal_price"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    print(f"Train: {len(X_train)}, Test: {len(X_test)}")

    model = RandomForestRegressor(
        n_estimators=100,
        max_depth=8,
        min_samples_leaf=5,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    # Evaluate
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test, preds)
    r2  = r2_score(y_test, preds)
    print(f"\nTest MAE: ₹{mae:.1f}/quintal")
    print(f"Test R²:  {r2:.3f}")
    print("\nNOTE: These metrics are on DEMO/SYNTHETIC data only.")
    print("Do NOT cite these as real-world accuracy.")

    # Feature importance
    importance = dict(zip(feature_cols, model.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: -x[1])[:5]
    print("\nTop features:", top_features)

    # Save model
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"\nModel saved: {MODEL_PATH}")

    meta = {
        "model_name": "market_price_rf_v1",
        "model_version": "1.0-demo",
        "algorithm": "RandomForestRegressor",
        "trained_at": datetime.utcnow().isoformat(),
        "training_data_source": "DEMO/SYNTHETIC — not real AGMARKNET data",
        "feature_list": feature_cols,
        "test_mae_inr": round(mae, 2),
        "test_r2": round(r2, 3),
        "important_note": "Trained on synthetic data. Do not cite accuracy as real-world performance.",
        "prediction_target": "regional_commodity_modal_price",
        "what_this_is_not": "NOT individual farmer default prediction",
    }
    with open(META_PATH, "w") as f:
        json.dump(meta, f, indent=2)
    print(f"Model metadata saved: {META_PATH}")

    return model, meta


if __name__ == "__main__":
    model, meta = train()
    print("\n✓ Training complete.")
