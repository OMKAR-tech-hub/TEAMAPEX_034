# KisanSetu — Farmer Trust Passport
**IBM National Hackathon 2026 Finals | Team APEX_034**

> Portable Agricultural Economic Identity for transparent credit access.
> The farmer owns the data. The FPO verifies. The lender decides. KisanSetu explains.

---

## Quick Start

### Backend
```bash
# From project root
.\backend\venv_new\Scripts\python.exe -m uvicorn backend.main:app --reload --port 8000

# Seed demo data (first time)
.\backend\venv_new\Scripts\python.exe -m backend.seed_demo

# Run tests
.\backend\venv_new\Scripts\python.exe -m pytest tests/ -v
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### ML
```bash
# Train market price model
.\backend\venv_new\Scripts\python.exe ml\train_market_model.py
```

---

## Demo Credentials (password: `Demo@1234` for all)

| Role | Email |
|------|-------|
| 🌾 Farmer | farmer@kisansetu.demo |
| 🤝 FPO Manager | fpo@kisansetu.demo |
| 🏦 Lender | lender@kisansetu.demo |
| ⚙️ Admin | admin@kisansetu.demo |

---

## The Six Demo Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | Who is a trustworthy borrower? | Trust Passport + Overall Creditworthiness (Arjun Patel: **83.8/100**) |
| 2 | How much credit can safely be extended? | Safe Credit Limit: **₹2,32,200** (formula-based) |
| 3 | What should the credit be used for? | Recommended: seeds, fertilizer, irrigation |
| 4 | Can the farmer repay? | Net Income ₹2.45L, Repayment Coverage shown |
| 5 | How does the community reduce risk? | FPO verified 3 records; membership since 2022 |
| 6 | How does the farmer retain control? | Consent Management + hash-chained Data Access History |

---

## Architecture

```
backend/
├── main.py                  # FastAPI app, all routers registered
├── models.py                # SQLAlchemy ORM (15 tables)
├── schemas.py               # Pydantic v2 request/response models
├── config.py                # Settings (scoring weights etc.)
├── database.py              # SQLite engine + session
├── auth/
│   ├── security.py          # JWT, bcrypt
│   └── dependencies.py      # get_current_user, role guards
├── routers/
│   ├── auth.py              # register, login, /me
│   ├── farmers.py           # farmer profile CRUD
│   ├── farms.py             # farms, crop seasons, production, sales
│   ├── credit.py            # credit applications
│   ├── verification.py      # verification CRUD
│   ├── fpo.py               # FPO management + verification
│   ├── passport.py          # Trust Passport + What-If
│   ├── consent.py           # consent grant/revoke + access history
│   ├── lender.py            # lender portal (consent-gated)
│   └── ml_router.py         # ML market price forecast
├── services/
│   ├── passport_engine.py   # 5-component transparent scorecard
│   └── market_intelligence.py  # AGMARKNET/NHB/PMFBY data service
└── seed_demo.py             # Demo data seeder

ml/
├── train_market_model.py    # RF price model training
├── predict.py               # inference interface
├── data/agmarknet_demo.csv  # DEMO/SYNTHETIC dataset
└── models/                  # trained model + metadata

frontend/src/
├── pages/
│   ├── Login.jsx
│   ├── FarmerDashboard.jsx
│   ├── TrustPassport.jsx    # Main demo screen
│   ├── WhatIf.jsx           # Slider-based simulator
│   ├── ConsentManagement.jsx
│   ├── DataAccessHistory.jsx
│   ├── FPODashboard.jsx
│   ├── LenderDashboard.jsx
│   └── CreditApplication.jsx
└── components/
    ├── Layout.jsx
    └── ScoreBar.jsx

tests/
├── test_auth.py             # registration, login, JWT
├── test_passport.py         # scoring formula, safe credit limit
├── test_consent_lender.py   # consent enforcement, what-if mutation guard
└── test_hash_chain.py       # tamper-evident log verification
```

---

## Trust Passport Formula

```
Overall = 0.25 × Production Stability
        + 0.20 × Market Stability
        + 0.25 × Repayment Capacity
        + 0.15 × Agricultural Risk
        + 0.15 × FPO Community

Safe Credit Limit = Acreage × NHB Benchmark Yield × Conservative AGMARKNET Price × Risk Haircut

Risk Haircut:  90–100 → 1.00  |  75–89 → 0.90  |  60–74 → 0.75  |  45–59 → 0.60  |  <45 → 0.45
```

---

## API Docs
After starting backend: http://localhost:8000/docs

---

## Important Caveats
- Market/benchmark data is **DEMO/SYNTHETIC** — not live government data
- ML model trained on synthetic data — **do not cite accuracy as real-world**
- FPO membership is a **verification/trust layer only** — FPO does NOT guarantee loans
- KisanSetu provides an **explainable assessment** — the lender makes the final decision
- No individual farmer default prediction is performed

---

## What Remains for ML Phase
- Connect real AGMARKNET CSV from data.gov.in
- Connect real NHB benchmark data
- Train on multi-year historical price data
- Add risk model with real PMFBY district data
- Integrate forecast confidence intervals into passport
