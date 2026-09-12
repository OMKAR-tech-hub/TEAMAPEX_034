"""
ML Prediction interface — loads saved models and generates predictions.
Used by the /ml API endpoints.
"""
import os, json
import numpy as np
from typing import Dict, Optional

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MARKET_MODEL_PATH = os.path.join(MODEL_DIR, "market_price_model.joblib")
MARKET_META_PATH  = os.path.join(MODEL_DIR, "market_price_model_meta.json")

_market_model = None
_market_meta = None

CROP_ENCODE = {"wheat": 0, "rice": 1, "soybean": 2, "cotton": 3, "maize": 4}

# Fallback recent prices from demo dataset
FALLBACK_PRICES = {
    "wheat": 2165, "rice": 2090, "soybean": 4377,
    "cotton": 6275, "maize": 1875,
}


def load_market_model():
    global _market_model, _market_meta
    if _market_model is None:
        if not os.path.exists(MARKET_MODEL_PATH):
            return None, None
        import joblib
        _market_model = joblib.load(MARKET_MODEL_PATH)
        if os.path.exists(MARKET_META_PATH):
            with open(MARKET_META_PATH) as f:
                _market_meta = json.load(f)
    return _market_model, _market_meta


def predict_market_price(
    crop: str,
    recent_prices: Optional[list] = None,
    week: int = 100,
) -> Dict:
    """
    Predict next-week price for a crop using the trained model.
    Falls back to demo average if model not trained yet.
    """
    model, meta = load_market_model()

    crop_lower = crop.lower()
    fallback = FALLBACK_PRICES.get(crop_lower, 1800)

    if model is None:
        return {
            "crop": crop,
            "predicted_price": fallback,
            "method": "fallback_average",
            "model_available": False,
            "note": "ML model not trained yet. Run: python ml/train_market_model.py",
            "data_source": "DEMO/SYNTHETIC",
        }

    # Build feature vector from recent prices or use simulated
    if recent_prices and len(recent_prices) >= 14:
        prices = recent_prices
    else:
        # Simulate using fallback
        prices = [fallback + np.random.normal(0, 50) for _ in range(20)]

    lag_1  = prices[-1]
    lag_7  = prices[-7]  if len(prices) >= 7  else fallback
    lag_14 = prices[-14] if len(prices) >= 14 else fallback

    import pandas as pd
    series = pd.Series(prices)
    rolling_mean_4w = series.rolling(4).mean().iloc[-1]
    rolling_std_4w  = series.rolling(4).std().iloc[-1]
    rolling_mean_8w = series.rolling(8).mean().iloc[-1] if len(prices) >= 8 else fallback
    price_trend_4w  = (prices[-1] - prices[-5]) / prices[-5] if len(prices) >= 5 else 0

    X = [[
        lag_1, lag_7, lag_14,
        rolling_mean_4w, rolling_std_4w if not np.isnan(rolling_std_4w) else 0,
        rolling_mean_8w if not np.isnan(rolling_mean_8w) else fallback,
        price_trend_4w, CROP_ENCODE.get(crop_lower, 5), week,
    ]]
    pred = float(model.predict(X)[0])
    trend = "rising" if pred > lag_1 * 1.02 else "falling" if pred < lag_1 * 0.98 else "stable"

    return {
        "crop": crop,
        "predicted_price": round(pred, 2),
        "recent_average": round(float(np.mean(prices[-4:])), 2),
        "trend": trend,
        "method": "random_forest",
        "model_available": True,
        "model_version": meta.get("model_version", "unknown") if meta else "unknown",
        "trained_at": meta.get("trained_at") if meta else None,
        "training_data_source": meta.get("training_data_source", "DEMO/SYNTHETIC") if meta else "DEMO/SYNTHETIC",
        "important_note": "Regional price forecast only. NOT individual farmer income prediction.",
        "data_source": "DEMO/SYNTHETIC",
    }
