# 4. REST API Contracts

Base: `/api/v1`. All responses envelope: `{ "ok": bool, "data": {...}, "errors": [...] }`.

## 4.1 POST /api/v1/underwrite/evaluate
Compute/recompute a farmer's credit profile deterministically.

```
Request:
{
  "farmer_id": 7,
  "crop_cycle_id": 12,
  "requested_amount": 120000,
  "tenure_months": 10
}

200 Response:
{
  "ok": true,
  "data": {
    "credit_profile_id": 401,
    "safe_credit_limit": 112455.00,
    "credit_tier": "High",
    "repayment_coverage": 1.62,
    "risk_haircut": 0.15,
    "component_scores": {
      "identity": 0.9, "landholding": 0.8, "production": 0.85,
      "verification": 0.9, "repayment": 0.9, "stability": 0.8
    },
    "model_version": "kisansetu-v1",
    "inputs": {
      "acreage": 3.5, "crop": "paddy",
      "nhb_yield_q_per_acre": 18, "agmarknet_price_per_q": 2100,
      "weather_loss_ratio": 0.0
    },
    "breakdown": {
      "gross_value": 132300.00,
      "formula": "acreage * yield * price * (1 - risk_haircut)"
    }
  }
}
```
Errors: `404 farmer/crop_cycle not found`, `422 requested_amount > safe_credit_limit`.

## 4.2 POST /api/v1/consent/grant
Farmer grants consent; enforces `sum(farmer_fees) == 0` (RBI DLG).

```
Request:
{
  "farmer_id": 7,
  "counterparty_type": "lender",
  "counterparty_id": 3,
  "purpose": "credit-origination",
  "attributes": ["name","village","safe_credit_limit","credit_tier"],
  "masked_attributes": ["mobile"],
  "language": "hi",
  "expires_at": "2027-03-31T18:30:00Z"
}

200 Response:
{
  "ok": true,
  "data": {
    "consent_uid": "8f3c...",
    "status": "active",
    "artifact_uri": "/uploads/consent/8f3c.wav",
    "artifact_hash": "<sha256>",
    "fee_assertion": {"farmer_fees_total": 0},
    "revoked_at": null
  }
}
```
Error: `422 farmer_fees_total != 0 -> fee-policy violated`.

### POST /api/v1/consent/revoke
`{"consent_uid": "8f3c..."}` -> revokes; bank view immediately returns 403.

## 4.3 POST /api/v1/fpo/vouch
Member vouching with stake weighting + fraud checks.

```
Request:
{
  "farmer_id": 7,
  "fpo_id": 2,
  "attestor_user_id": 19,
  "score": 5,
  "statement": "Good agronomic practices",
  "season": "Kharif", "year": 2026
}

200 Response:
{
  "ok": true,
  "data": {
    "vouch_id": 9001,
    "status": "active",
    "weight": 1.1,
    "attestation_score_delta": 0.04,
    "safe_credit_limit_unchanged": true
  }
}
```
Errors: `409 duplicate vouch this season`, `422 conflict_of_interest`, `409 reciprocal-vouch burst (suspect)`.

## 4.4 GET /api/v1/lender/pipeline
Consent-gated origination queue.

```
Request params:
  lender_id=3
  status=queued
  psl_category=Agri_2L
  consent_active_only=true

200 Response:
{
  "ok": true,
  "data": {
    "items": [
      {
        "farmer_ref": "F-7",
        "village": "Krishnapur",
        "mobile": "xxxxxx3210",
        "safe_credit_limit": 112455.00,
        "credit_tier": "High",
        "repayment_coverage": 1.62,
        "psl_category": "Agri_2L",
        "psl_eligible": true,
        "consent_uid": "8f3c...",
        "consent_status": "active"
      }
    ],
    "count": 1,
    "pagination": {"page": 1, "size": 50}
  }
}
```
Masking: any attribute not in `data_consents.attributes` (or in `masked_attributes`) is rendered masked/hidden.