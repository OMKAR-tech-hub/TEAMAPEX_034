# 5. Edge Cases & Safeguards

## 5.1 Mid-season drought / pest wipeout

Scenario: crop cycle status `growing`; PMFBY/Weather OGD declares `loss_ratio = 0.6` (severe).

State machine (per crop cycle + loan):
1. `risk_event` row inserted `action='recalibrate'`; `credit_profiles.weather_loss_ratio` updated.
2. All pending `disbursement_tranches` (status `scheduled`) -> **blocked**. No new vendor payments.
3. Installment: EMI pausing proposed as `moratorium`; `loan_applications.status` stays `active` but flag `moratorium=True` surfaced in Farmer Harvest Repayment Tracker (auto-pause, claim-linked status shown).
4. Re-evaluation: Safe Credit Limit recomputed as
   `rem <= acreage * expected_yield_q * (1 - loss_ratio) * agmarknet_price * (1 - risk_haircut)`.
   If exposed/committed > new safe limit, drawdown is frozen; borrower sees the recalibration via visualizer "recalibrated" badge.
5. PMFBY claim: `risk_events.pmfby_claim_ref` captured; claim proceeds settle 100% against outstanding before any EMI resumes. Platform takes no cut on claim money (DLG).
6. Recovery: on `harvesting` + NDVI/geotag OK, tranche engine may release residual funding for rescue inputs only.

Safeguards:
- All transitions logged; a re-run of the same risk event is idempotent (event-key = cycle_id+event_type+year+week).
- `blocked` tranches require 2-person authorization to reverse.

## 5.2 FPO board favoritism / fraudulent vouching

Attack: board member vouches a relative; a clique of members mutually vouches to inflate attestation score; FPO mass-attests members it never met.

Controls:
1. **Conflict-of-interest at write time.** `fpo_memberships.conflict_of_interest` = relation declaration (self-declared + staff-supervised); vouches by conflicted users are `rejected` — enforced at `POST /fpo/vouch` (`422`).
2. **Bounded influence.** A vouch changes the attestation score component only, weighted by vouchers own on-time-repayment history (`weight`). Vouch can never move `safe_credit_limit` directly. Cap: 1 vouch per member per crop cycle, max `N_v` weighted vouchers per member.
3. **Reciprocal-vouch detection.** In a rolling window (90 days), if A vouches B and B vouches A, both are flagged `suspect`; a clique of >= K mutual vouchers (`K=3`) freezes all and routes to committee review. Suspicious bursts trigger score `sigma = total_vouch_attestation_delta` cap per member.
4. **Assertion-distance metric.** FPOs whose attested member counts exceed NHB/PMFBY-implied farm counts for the district by a margin trigger audit: ratio `attested_farmers / district_farmers >> percentile_90` raises `member_integrity_flag=false` for the FPO cohort and reduces the FPO trust multiplier for 6 months.
5. **Separation of duties + staff attestation quota.** Staff attestations are logged with user id + timestamp and immutable; board cannot edit staff attestations.
6. **Synthetic test invariants** (to be wired as unit tests):
   - `test_vouch_by_conflicted_user_rejected`
   - `test_reciprocal_scheme_frozen`
   - `test_vouch_never_changes_safe_credit_limit`
   - `test_mass_attestation_flag_audit`
   - `test_loss_event_blocks_pending_tranches`
   - `test_farmer_ledger_has_zero_platform_fee_lines`