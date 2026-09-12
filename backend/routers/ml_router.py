"""
ML endpoints — market price forecast, model info.
Integrates ML intelligence into Trust Passport as supporting context.
NOT a loan approval system.
"""
from fastapi import APIRouter, Depends, Query
from typing import Optional, List
import sys, os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.auth.dependencies import get_current_user
from backend.models import User

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/market-price/forecast")
def forecast_market_price(
    crop: str = Query(..., description="Crop name e.g. wheat, rice, soybean"),
    state: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    ML-powered market price forecast for a crop.
    Uses trained Random Forest on AGMARKNET-style data.
    IMPORTANT: Regional forecast only — NOT individual farmer income prediction.
    """
    try:
        from ml.predict import predict_market_price
        result = predict_market_price(crop)
    except Exception as e:
        logger.warning(f"ML predict failed: {e}, using fallback")
        from backend.services.market_intelligence import calculate_market_stats
        mkt = calculate_market_stats(crop, state)
        result = {
            "crop": crop,
            "predicted_price": mkt.get("average_price", 1500),
            "recent_average": mkt.get("average_price", 1500),
            "trend": mkt.get("trend", "unknown"),
            "method": "statistical_fallback",
            "model_available": False,
            "data_source": mkt.get("source", "DEMO/SYNTHETIC"),
            "note": f"ML model unavailable ({e}), using statistical fallback",
        }

    return {
        **result,
        "disclaimer": (
            "This is a regional commodity price forecast based on historical patterns. "
            "It is NOT a prediction of individual farmer income or loan repayment. "
            "Lenders must conduct their own due diligence."
        ),
    }


@router.get("/model-info")
def get_model_info(current_user: User = Depends(get_current_user)):
    """Return metadata about deployed ML models."""
    import json
    meta_path = os.path.join(
        os.path.dirname(__file__), '..', '..', 'ml', 'models', 'market_price_model_meta.json'
    )
    if os.path.exists(meta_path):
        with open(meta_path) as f:
            meta = json.load(f)
    else:
        meta = {"status": "not_trained", "note": "Run: python ml/train_market_model.py"}

    return {
        "models": [
            {
                "name": "market_price_rf_v1",
                "purpose": "Regional commodity price forecasting",
                "metadata": meta,
            }
        ],
        "important_note": (
            "KisanSetu ML models provide agricultural intelligence, not automatic credit decisions. "
            "No individual farmer default prediction is performed. "
            "All ML outputs are supplementary to the explainable Trust Passport scorecard."
        ),
    }


@router.get("/market-price/intelligence")
def get_market_intelligence(
    crop: str = Query(...),
    state: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
):
    """
    Combined market intelligence: statistical + ML forecast.
    Returns price stats, forecast, and stability assessment.
    """
    from backend.services.market_intelligence import calculate_market_stats, get_benchmark_yield
    stats = calculate_market_stats(crop, state)
    benchmark = get_benchmark_yield(crop)

    try:
        from ml.predict import predict_market_price
        forecast = predict_market_price(crop)
    except Exception:
        forecast = {"predicted_price": stats.get("average_price"), "method": "unavailable"}

    return {
        "crop": crop,
        "state": state,
        "market_statistics": stats,
        "ml_forecast": forecast,
        "nhb_benchmark": benchmark,
        "combined_insight": {
            "conservative_price": stats.get("conservative_price"),
            "forecast_price": forecast.get("predicted_price"),
            "market_stability_score": stats.get("market_stability_score"),
            "trend": stats.get("trend"),
            "use_for_credit_assessment": "conservative_price from AGMARKNET statistics (not ML forecast)",
        },
        "data_caveat": "DEMO/SYNTHETIC dataset. Connect real AGMARKNET CSV for live data.",
    }
