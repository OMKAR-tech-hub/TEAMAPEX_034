# KisanSetu — End-to-End Technical Blueprint (v1)

> FinTech monolith: Farmer -> FPO -> Bank. Non-extractive revenue only.
> Compliance base: RBI Digital Lending Guidelines (DLG) — zero charges to the farmer borrower.
> Data: AGMARKNET 2.0, NHB, PMFBY/Weather OGD, PM-KISAN/ICAR (contract-first adapters; offline mock fallback = existing `backend/app/core/market.py`).

## Codebase mapping
| Blueprint entity | Existing code |
|---|---|
| `credit_profiles` | `trust_passports` (approx.) |
| `data_consents` | `consent_logs` |
| `fpo_attestations` | `fpo_verifications` |
| Safe Credit Limit engine | `backend/app/services/credit_engine.py` |

## Sections
1. [Features + User Stories / Acceptance Criteria](KISANSETU_BLUEPRINT_01_FEATURES.md)
2. [Revenue & Flow-of-Funds Architecture + Math Proof](KISANSETU_BLUEPRINT_02_REVENUE.md)
3. [PostgreSQL Schema](KISANSETU_BLUEPRINT_03_SCHEMA.sql)
4. [REST API Contracts](KISANSETU_BLUEPRINT_04_API.md)
5. [Edge Cases & Safeguards](KISANSETU_BLUEPRINT_05_EDGE.md)