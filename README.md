# Kisan Setu — Farmer Trust Passport Baseline

A functional monolithic baseline for **Kisan Setu**: farmers build a portable agricultural
economic identity (the Trust Passport), FPOs verify them, and banks get consent-gated views
with attribute masking. No external data integrations — all crop yields and benchmark prices
are internal mock configurations.

## Stack

- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic v2 (SQLite in dev, PostgreSQL-ready)
- **Frontend**: React SPA + Vite + Tailwind CSS with role-based navigation (Farmer, FPO, Bank)
- **Credit Engine**: deterministic pure-Python service (no randomness, no third-party APIs)

## Repository Layout

```
backend/
  .env                     # environment configuration (create from .env.example)
  requirements.txt
  app/
    main.py                # FastAPI entry point (uvicorn app.main:app)
    seed.py                # creates demo FPO + Bank accounts
    core/                  # config, database, security, mock market data
    models/                # User, Farmer, FPOVerification, TrustPassport, ConsentLog
    schemas/               # Pydantic request/response models
    services/              # credit engine + consent-gated bank view (masking)
    api/
      deps.py              # auth dependencies (Bearer token, role guards)
      routes/              # auth, farmers, fpo, passports, consents, bank
frontend/
  src/
    api.js                 # axios client with token interceptor
    context/AuthContext.jsx
    components/Navbar.jsx, ScoreBar.jsx
    pages/Login.jsx, Register.jsx, FarmerDashboard.jsx, FPODashboard.jsx, BankDashboard.jsx
```

## Quick Start

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows  |  source venv/bin/activate  (Linux/macOS)
pip install -r requirements.txt
python -m app.seed             # optional: demo FPO + Bank logins
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API docs: http://127.0.0.1:8000/docs
- `backend/.env` already exists for dev. For real deployments copy `.env.example` and set a
  strong `SECRET_KEY` and your `DATABASE_URL` (PostgreSQL/MySQL).

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000. Vite proxies `/api` and `/uploads` to the backend on :8000.

## Demo Accounts

| Role   | Username      | Password   |
| ------ | ------------- | ---------- |
| Farmer | (any 10-digit mobile you register) | chosen at registration |
| FPO    | `fpo_krishak` | `demo@1234` |
| Bank   | `bank_gramin` | `demo@1234` |

## Credit Engine

Pure Python, fully deterministic:

```
Safe Credit Limit   = Acreage * Yield_per_acre * Benchmark_price * (1 - Risk Haircut)
Repayment Coverage  = Net Income / Repayment Demand
```

- **Yield & price**: internal mock table in `app/core/market.py` (paddy, wheat, cotton, maize, ...).
- **Risk haircut**: base 20%; 15% when FPO-verified with member integrity, 35% when rejected.
- **Six component scores** (0–100): identity, landholding, production, verification, repayment, stability.
- Execution: `POST /api/v1/passports/compute/{farmer_id}` stores the result in `TrustPassport`.

## Key API Endpoints

| Method | Endpoint | Description |
| ------ | -------- | ----------- |
| POST | `/api/v1/auth/register/farmer` | Register farmer + login account |
| POST | `/api/v1/auth/register/fpo` / `/bank` | Register FPO / bank account |
| POST | `/api/v1/auth/login` | Obtain JWT (`role` in payload) |
| GET/PUT/DELETE | `/api/v1/farmers/{id}` | Farmer profile CRUD |
| POST | `/api/v1/fpo/verifications` | FPO submits a verification |
| PUT | `/api/v1/fpo/verifications/{id}` | Update status + member integrity flag |
| POST | `/api/v1/passports/compute/{farmer_id}` | Trigger deterministic credit calculation |
| GET | `/api/v1/passports/{farmer_id}` | Latest Trust Passport |
| POST | `/api/v1/consents` | Farmer grants a bank access (attributes + masking) |
| PUT | `/api/v1/consents/{id}` | Grant / revoke consent |
| GET | `/api/v1/bank/farmers/{farmer_id}/view` | Consent-gated, masked bank view |

## Workflow

1. **Farmer** registers → identity + landholding (`acreage`) + crop season.
2. **FPO** logs in, submits a verification, sets the `member_integrity_flag`.
3. **Farmer** triggers the credit engine → Trust Passport with safe credit limit and 6 scores.
4. **Farmer** grants a bank consent, selecting attributes and which ones to mask.
5. **Bank** opens `.../view` and sees only the consented (and masked) attributes
   (e.g. `mobile` → `xxxxxx3210`). Revoking consent blocks the bank immediately (403).

## Security Notes

- Passwords hashed with bcrypt; short-lived JWT with role claim; role-guarded endpoints.
- Bank access is strictly consent-gated and revoked consents return 403.
- `.env` is git-ignored; never commit real secrets. Use `.env.example` for provisioning.

## Testing

Backend is exercised end-to-end via an integration harness (register → verify → compute →
consent → view → revoke). Example:

```bash
python -m app.seed
```

then drive the API through Swagger at http://127.0.0.1:8000/docs or the React UI at :3000.