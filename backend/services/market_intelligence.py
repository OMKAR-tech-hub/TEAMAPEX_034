"""
Market Intelligence Service
Sources: AGMARKNET (demo dataset), NHB crop benchmarks, PMFBY weather risk.

DATA CAVEAT: Values below are a clearly-labelled DEMO/SYNTHETIC dataset.
They are NOT live government data. The source field says "DEMO/SYNTHETIC".
Real AGMARKNET data can be loaded via load_agmarknet_csv(path).
"""
from typing import Dict, List, Optional, Tuple
import statistics
import logging

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DEMO MARKET PRICE DATA  (AGMARKNET-style)
# Source: DEMO/SYNTHETIC — placeholder for real AGMARKNET CSV
# ─────────────────────────────────────────────
DEMO_MARKET_PRICES: List[Dict] = [
    # Wheat — Madhya Pradesh
    {"crop": "wheat", "market": "Bhopal Mandi", "district": "Bhopal", "state": "Madhya Pradesh",
     "modal_price": 2150, "min_price": 2050, "max_price": 2300, "date": "2026-03-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "wheat", "market": "Bhopal Mandi", "district": "Bhopal", "state": "Madhya Pradesh",
     "modal_price": 2180, "min_price": 2060, "max_price": 2320, "date": "2026-04-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "wheat", "market": "Indore Mandi", "district": "Indore", "state": "Madhya Pradesh",
     "modal_price": 2200, "min_price": 2080, "max_price": 2350, "date": "2026-03-15", "source": "DEMO/SYNTHETIC"},
    # Rice — Punjab
    {"crop": "rice", "market": "Amritsar Mandi", "district": "Amritsar", "state": "Punjab",
     "modal_price": 2100, "min_price": 1950, "max_price": 2250, "date": "2026-01-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "rice", "market": "Amritsar Mandi", "district": "Amritsar", "state": "Punjab",
     "modal_price": 2050, "min_price": 1900, "max_price": 2200, "date": "2026-02-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "rice", "market": "Ludhiana Mandi", "district": "Ludhiana", "state": "Punjab",
     "modal_price": 2120, "min_price": 2000, "max_price": 2270, "date": "2026-02-15", "source": "DEMO/SYNTHETIC"},
    # Soybean — Maharashtra
    {"crop": "soybean", "market": "Latur Mandi", "district": "Latur", "state": "Maharashtra",
     "modal_price": 4400, "min_price": 4200, "max_price": 4700, "date": "2026-01-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "soybean", "market": "Latur Mandi", "district": "Latur", "state": "Maharashtra",
     "modal_price": 4350, "min_price": 4150, "max_price": 4600, "date": "2026-02-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "soybean", "market": "Nagpur Mandi", "district": "Nagpur", "state": "Maharashtra",
     "modal_price": 4380, "min_price": 4100, "max_price": 4650, "date": "2026-02-15", "source": "DEMO/SYNTHETIC"},
    # Cotton — Gujarat
    {"crop": "cotton", "market": "Rajkot Mandi", "district": "Rajkot", "state": "Gujarat",
     "modal_price": 6200, "min_price": 5900, "max_price": 6600, "date": "2026-01-01", "source": "DEMO/SYNTHETIC"},
    {"crop": "cotton", "market": "Rajkot Mandi", "district": "Rajkot", "state": "Gujarat",
     "modal_price": 6350, "min_price": 6000, "max_price": 6700, "date": "2026-02-01", "source": "DEMO/SYNTHETIC"},
    # Maize — Karnataka
    {"crop": "maize", "market": "Davangere Mandi", "district": "Davangere", "state": "Karnataka",
     "modal_price": 1850, "min_price": 1700, "max_price": 2000, "date": "2026-01-15", "source": "DEMO/SYNTHETIC"},
    {"crop": "maize", "market": "Davangere Mandi", "district": "Davangere", "state": "Karnataka",
     "modal_price": 1900, "min_price": 1750, "max_price": 2050, "date": "2026-02-15", "source": "DEMO/SYNTHETIC"},
]

# ─────────────────────────────────────────────
# NHB CROP BENCHMARKS (yield quintals/acre)
# Source: DEMO/SYNTHETIC — real NHB data can be loaded via CSV
# ─────────────────────────────────────────────
NHB_BENCHMARKS: Dict[str, Dict] = {
    "wheat":   {"benchmark_yield": 16.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "rice":    {"benchmark_yield": 18.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "soybean": {"benchmark_yield": 8.0,  "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "cotton":  {"benchmark_yield": 7.5,  "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "maize":   {"benchmark_yield": 20.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "sugarcane":{"benchmark_yield": 280.0,"unit": "quintals/acre","source": "DEMO/SYNTHETIC", "year": 2025},
    "tomato":  {"benchmark_yield": 80.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "onion":   {"benchmark_yield": 60.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
    "default": {"benchmark_yield": 12.0, "unit": "quintals/acre", "source": "DEMO/SYNTHETIC", "year": 2025},
}

# ─────────────────────────────────────────────
# WEATHER / PMFBY RISK INDEX
# Source: DEMO/SYNTHETIC — real PMFBY district data can be loaded via CSV
# ─────────────────────────────────────────────
WEATHER_RISK: Dict[str, Dict] = {
    # (state, crop) -> risk data
    ("Madhya Pradesh", "wheat"):   {"risk_score": 72, "rainfall_risk": 25, "temperature_risk": 30, "source": "DEMO/SYNTHETIC"},
    ("Madhya Pradesh", "soybean"): {"risk_score": 65, "rainfall_risk": 40, "temperature_risk": 30, "source": "DEMO/SYNTHETIC"},
    ("Punjab", "rice"):            {"risk_score": 80, "rainfall_risk": 20, "temperature_risk": 20, "source": "DEMO/SYNTHETIC"},
    ("Punjab", "wheat"):           {"risk_score": 82, "rainfall_risk": 18, "temperature_risk": 20, "source": "DEMO/SYNTHETIC"},
    ("Maharashtra", "soybean"):    {"risk_score": 60, "rainfall_risk": 45, "temperature_risk": 35, "source": "DEMO/SYNTHETIC"},
    ("Gujarat", "cotton"):         {"risk_score": 58, "rainfall_risk": 50, "temperature_risk": 40, "source": "DEMO/SYNTHETIC"},
    ("Karnataka", "maize"):        {"risk_score": 68, "rainfall_risk": 35, "temperature_risk": 30, "source": "DEMO/SYNTHETIC"},
    "default":                     {"risk_score": 60, "rainfall_risk": 40, "temperature_risk": 35, "source": "DEMO/SYNTHETIC"},
}

# Cultivation cost estimates (₹/acre) — DEMO/SYNTHETIC
CULTIVATION_COST_PER_ACRE: Dict[str, float] = {
    "wheat": 12000, "rice": 18000, "soybean": 10000,
    "cotton": 22000, "maize": 11000, "sugarcane": 35000,
    "tomato": 45000, "onion": 30000, "default": 15000,
}


def get_market_prices(crop: str, state: Optional[str] = None, district: Optional[str] = None) -> List[Dict]:
    """Return demo market price records for a crop, optionally filtered."""
    crop_lower = crop.lower()
    results = [p for p in DEMO_MARKET_PRICES if p["crop"] == crop_lower]
    if state:
        results = [p for p in results if p["state"].lower() == state.lower()]
    if district:
        results = [p for p in results if p["district"].lower() == district.lower()]
    return results or [p for p in DEMO_MARKET_PRICES if p["crop"] == crop_lower]


def calculate_market_stats(crop: str, state: Optional[str] = None) -> Dict:
    """Compute price statistics from demo dataset."""
    prices_data = get_market_prices(crop, state)
    if not prices_data:
        return {
            "crop": crop, "data_available": False,
            "conservative_price": 1500, "average_price": 1500,
            "price_volatility": 0, "trend": "unknown",
            "market_stability_score": 50,
            "source": "DEMO/SYNTHETIC — no data found, using fallback",
        }
    modal_prices = [p["modal_price"] for p in prices_data]
    avg = statistics.mean(modal_prices)
    conservative = min(modal_prices)  # use minimum as conservative estimate
    try:
        stdev = statistics.stdev(modal_prices) if len(modal_prices) > 1 else 0
    except Exception:
        stdev = 0
    cv = (stdev / avg * 100) if avg > 0 else 0   # coefficient of variation %

    # Trend: simple first-vs-last
    trend = "stable"
    if len(modal_prices) >= 2:
        delta_pct = (modal_prices[-1] - modal_prices[0]) / modal_prices[0] * 100
        trend = "rising" if delta_pct > 3 else "falling" if delta_pct < -3 else "stable"

    # Market stability score: lower CV = more stable = higher score
    stability_score = max(0, min(100, 100 - cv * 2))

    return {
        "crop": crop,
        "data_available": True,
        "conservative_price": conservative,
        "average_price": round(avg, 2),
        "price_volatility_pct": round(cv, 2),
        "trend": trend,
        "market_stability_score": round(stability_score, 1),
        "num_records": len(prices_data),
        "source": prices_data[0]["source"],
        "data_caveat": "DEMO/SYNTHETIC dataset. Not live AGMARKNET data.",
    }


def get_benchmark_yield(crop: str) -> Dict:
    """Return NHB benchmark yield for crop."""
    crop_lower = crop.lower()
    return NHB_BENCHMARKS.get(crop_lower, NHB_BENCHMARKS["default"])


def get_weather_risk(state: str, crop: str) -> Dict:
    """Return weather/PMFBY risk index for state+crop."""
    key = (state, crop.lower())
    return WEATHER_RISK.get(key, WEATHER_RISK["default"])


def get_cultivation_cost(crop: str, area_acres: float) -> float:
    """Estimate cultivation cost."""
    crop_lower = crop.lower()
    cost_per_acre = CULTIVATION_COST_PER_ACRE.get(crop_lower, CULTIVATION_COST_PER_ACRE["default"])
    return cost_per_acre * area_acres


def load_agmarknet_csv(path: str):
    """
    Placeholder: load real AGMARKNET CSV data.
    Expected columns: commodity, market, district, state, modal_price, min_price, max_price, date
    When real data is available, parse it here and replace DEMO_MARKET_PRICES.
    """
    logger.info(f"load_agmarknet_csv called with {path} — real loader not yet implemented")
    raise NotImplementedError("Real AGMARKNET CSV loader — connect to data.gov.in download")
