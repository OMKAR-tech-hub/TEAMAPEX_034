"""Market reference data for the credit engine.

Prices are REAL AGMARKNET modal (wholesale) prices per quintal, sourced from
farmer.in's India Crop Modal Price Dataset (CC BY 4.0, updated 2026-09-12,
source: Agmarknet / data.gov.in via Farmer.in).
MSP values are from the India MSP 2026-27 dataset (CACP / Ministry of Agriculture).

Yield benchmarks remain internal deterministic defaults (field-level estimate
per acre) until an NHB/UPAg yield adapter is wired in.

Offline and deterministic: zero third-party API calls at runtime.
"""

MOCK_CROP_MARKET: dict = {
    # crop: agmarknet modal Rs/q + MSP Rs/q ('' = no MSP)
    "paddy": {"yield_per_acre": 18.0, "benchmark_price": 3700.0, "modal_price": 3700.0, "msp": 2441.0},
    "wheat": {"yield_per_acre": 15.0, "benchmark_price": 2600.0, "modal_price": 2600.0, "msp": 2585.0},
    "cotton": {"yield_per_acre": 4.5, "benchmark_price": 8650.0, "modal_price": 8650.0, "msp": 8267.0},
    "sugarcane": {"yield_per_acre": 140.0, "benchmark_price": 350.0, "modal_price": 350.0, "msp": 355.0},
    "maize": {"yield_per_acre": 20.0, "benchmark_price": 2300.0, "modal_price": 2300.0, "msp": 2410.0},
    "soybean": {"yield_per_acre": 8.5, "benchmark_price": 5740.0, "modal_price": 5740.0, "msp": 5708.0},
    "groundnut": {"yield_per_acre": 9.0, "benchmark_price": 7093.0, "modal_price": 7093.0, "msp": 7517.0},
    "tur": {"yield_per_acre": 4.0, "benchmark_price": 7400.0, "modal_price": 7400.0, "msp": 8450.0},
    "moong": {"yield_per_acre": 3.5, "benchmark_price": 6000.0, "modal_price": 6000.0, "msp": 8780.0},
    "vegetables": {"yield_per_acre": 60.0, "benchmark_price": 2940.0, "modal_price": 2940.0, "msp": None},
    "other": {"yield_per_acre": 12.0, "benchmark_price": 2500.0, "modal_price": 2500.0, "msp": None},
}

# Production cost as a fraction of gross income (upfront + operations + harvest).
PRODUCTION_COST_RATIO: float = 0.40

# Share of repayment demand that must be covered before the score plateaus.
COVERAGE_SCALE: float = 33.33

# Fertile acreage needed to reach a full landholding score.
FULL_LANDHOLDING_ACRES: float = 5.0

# Market-price risk bands per crop (0 = very stable, 100 = highly volatile).
# Staple staples (rice/wheat/sugarcane) sit on MSP floors; perishables and
# pulses trade without strong support and swing more at the mandi.
CROP_RISK_BANDS: dict = {
    "sugarcane": {"volatility": 15},
    "paddy": {"volatility": 20},
    "wheat": {"volatility": 20},
    "maize": {"volatility": 30},
    "cotton": {"volatility": 40},
    "soybean": {"volatility": 45},
    "groundnut": {"volatility": 50},
    "tur": {"volatility": 55},
    "moong": {"volatility": 55},
    "vegetables": {"volatility": 75},
    "other": {"volatility": 55},
}

DATA_SOURCE: str = "AGMARKNET modal prices via Farmer.in (CC BY 4.0, 2026-09-12); MSP 2026-27 (CACP/DA&FW)"


def normalize_crop(crop: str) -> str:
    return crop.strip().lower()


def get_market_reference(crop: str) -> dict:
    key = normalize_crop(crop)
    if key not in MOCK_CROP_MARKET:
        key = "other"
    entry = MOCK_CROP_MARKET[key]
    return {
        "yield_per_acre": entry["yield_per_acre"],
        "benchmark_price": entry["benchmark_price"],
        "modal_price": entry.get("modal_price", entry["benchmark_price"]),
        "msp": entry.get("msp"),
        "source": DATA_SOURCE,
    }


def get_market_risk(crop: str) -> dict:
    key = normalize_crop(crop)
    if key not in MOCK_CROP_MARKET:
        key = "other"
    entry = MOCK_CROP_MARKET[key]
    modal = entry.get("modal_price", entry["benchmark_price"])
    msp = entry.get("msp")
    msp_gap_ratio = round(modal / msp, 3) if msp else None
    return {
        "crop": key,
        "volatility": CROP_RISK_BANDS.get(key, CROP_RISK_BANDS["other"])["volatility"],
        "modal_price": modal,
        "msp": msp,
        "msp_gap_ratio": msp_gap_ratio,  # modal price as multiple of the MSP floor (>1 = support held)
        "has_msp_floor": bool(msp),
    }