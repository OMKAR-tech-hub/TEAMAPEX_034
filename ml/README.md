# KisanSetu ML Pipeline

## Philosophy
- ML provides **supporting agricultural intelligence**, not automatic loan decisions.
- No individual farmer default prediction without legitimate labelled default data.
- All ML outputs are clearly labelled with model version, training source, and uncertainty.

## Models

### 1. Market Price Forecasting (`train_market_model.py`)
- Trains on AGMARKNET-style price data
- Features: lag-1, lag-7, lag-14, rolling mean, rolling std, price trend, commodity/market encoding
- Algorithm: Random Forest Regressor (lightweight, interpretable)
- Output: predicted_price, trend, model_version
- Saved: `ml/models/market_price_model.joblib`

### 2. Agricultural Risk Index (`train_risk_model.py`)
- Transparent risk index based on engineered features
- Does NOT predict individual loan default (no valid labels)
- Features: weather risk, irrigation type, crop type, FPO membership, season
- Algorithm: Rule-based scoring + Random Forest for enhancement
- Output: risk_score (0-100), risk_factors

## Data
- `ml/data/agmarknet_demo.csv` — DEMO/SYNTHETIC market price data
- Real AGMARKNET data: download from https://data.gov.in/catalog/current-daily-price-various-commodities-various-markets-mandi

## Training
```bash
python ml/train_market_model.py
python ml/train_risk_model.py
```

## Integration
ML endpoints:
- `POST /ml/market-price/forecast` — price prediction for crop
- `GET /ml/model-info` — model metadata

## Important Notes
- NEVER claim ML accuracy without proper validation
- NEVER claim these models predict individual default
- Always expose model version and training data source
- ML outputs are supplementary to the explainable scorecard
