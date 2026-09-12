# 1. Feature Breakdown (User Stories + Acceptance Criteria)

## a) Farmer

### 1a.1 Consent Gateway
- **US:** As a farmer, I want to review and grant/revoke access to my Trust Passport through an audio+digital consent artifact in my local language, so no lender, FPO, or platform sees my data without my explicit permission.
- **AC (Given/When/Then):**
  - G: a lender requests my passport. W: I open the Consent Gateway. T: I see exactly which attributes (name, mobile, acreage, score) are shared and which are masked; I record/replay an audio artifact; consent is stored with a hash and expiry.
  - G: I revoke consent. W: I press Revoke. T: the lender view returns 403 within the same request cycle (proven in baseline demo).
  - G: consent expires or is revoked. W: bank re-requests. T: bank sees nothing until a new consent is granted.
  - G: a grant contains an origination-fee or penalty clause. W: gateway validates against fee policy. T: grant is rejected with an RBI-DLG fee-rule error.

### 1a.2 Safe Credit Limit Visualizer
- **US:** As a farmer, I want to see how my Safe Credit Limit is computed and simulate changes (acreage, crop, season), so I understand and trust the number before borrowing.
- **AC:**
  - G: my passport exists. W: I open the visualizer. T: I see `Safe Credit = Acreage x NHB Yield x AGMARKNET Price x (1 - Risk Haircut)` with every input shown.
  - G: I change acreage/crop via slider. W: Recompute. T: limit, the 6 component scores, and credit tier update deterministically.
  - G: a crop-loss event exists for my cycle. W: visualizer renders. T: red "recalibrated" badge appears; limit is haircut by loss ratio.
  - G: any view. T: no CTA pressuring immediate borrowing; a "talk to your FPO" contact is the only CTA.

### 1a.3 Harvest Repayment Tracker
- **US:** As a farmer, I want every mandi sale to settle against my loan automatically and watch my balance shrink with receipts, so repayment is transparent and never forced.
- **AC:**
  - G: I sell produce at a mandi with AGMARKNET floor price. W: escrow settlement posts. T: gross sale, FPO facilitation %, platform settlement fee, principal+interest paid, new outstanding balance itemized line-by-line.
  - G: an installment is due. T: tracker shows exact EMI and confirms auto-payment from escrow surplus; residual goes to my bank account.
  - G: a PMFBY/weather loss event is declared. T: installment is paused (moratorium); claim-linked status appears.
  - G: any point. T: farmer ledger shows zero platform fee lines (RBI DLG invariant).

## b) FPO

### 1b.1 Attestation Dashboard
- **US:** As an FPO field officer, I want to attest member onboarding and maintain the member-integrity flag with an audit trail, so banks trust aggregator-level integrity.
- **AC:**
  - G: an onboarding claim arrives. W: I open the dashboard. T: I see demographics + landholding + prior attestations; I set `member_integrity_flag` on/off; every action is logged with my user id, timestamp, non-editable post-hoc.
  - G: an attestation is contested. T: it moves to a re-attestation queue, blocked from silent overwrite.
  - G: separation of duties. T: manual attestation is a staff action; vouching is a member action; never the same person class.

### 1b.2 Member Vouching Engine
- **US:** As an FPO member, I want to vouch for a peer's character and farm practice in a stake-weighted, capped way, so attestation has social proof without letting any single person inflate credit.
- **AC:**
  - G: I vouch for member X. W: I submit score 1-5 + statement. T: conflict-of-interest check (board vouching a relative) rejects/excludes it; vouch is weighted by my on-time repayment history and moves only the attestation score, never the Safe Credit Limit directly.
  - G: I vouch twice for same member in one season. T: second vouch rejected (quota per member per crop cycle).
  - G: reciprocal-vouching bursts detected. T: both flagged `suspect`, frozen, routed to committee review.

### 1b.3 Facilitation Fee Wallet
- **US:** As an FPO, I want a wallet that accrues facilitation fees only from value-chain settlements (buyers/suppliers), not farmers, so my revenue is visibly non-extractive.
- **AC:**
  - G: a mandi settlement occurs. W: escrow processes. T: `fpo_facilitation_amt` (2% of sales value) credits the wallet; farmer settlement line shows this as a non-borrower cost.
  - G: I withdraw. T: wallet balance + withdrawal logged; wallet can never be debited from a farmer installment.
  - G: fee changes. T: rate is config-driven and disclosed in every settlement receipt.

## c) Bank

### 1c.1 Pre-Assessed Origination Queue
- **US:** As a bank credit officer, I want a consent-verified queue of pre-underwritten farmers (PSL-tagged), so I can originate loans faster with lower verification cost.
- **AC:**
  - G: farmer has passport + active consent to my bank. T: they appear in my pipeline with Safe Credit Limit, tier, village, PSL category; only consent-granted attributes visible (masked stay masked).
  - G: consent revoked. T: row leaves queue immediately.
  - G: I select and approve. T: loan created under the underwrite snapshot; no recomputation drift.

### 1c.2 Tranche Rule Engine
- **US:** As a bank ops head, I want disbursements split into milestone tranches paid directly to vendors/escrow, so funds serve the stated agricultural purpose.
- **AC:**
  - G: loan approved. T: plan generated (T1 input vendor -> T2 staged milestone -> T3 post-harvest) with release rules (crop stage + geotag + weather OK).
  - G: risk event (drought/pest) fires mid-season. T: engine BLOCKS pending tranches; moratorium proposal raised.
  - G: rule passes. T: release automatic, logged, farmer notified; payee always vendor/escrow, never a platform fee account.

### 1c.3 PSL Compliance Exporter
- **US:** As a compliance team, I want to export the Priority Sector Lending portfolio with RBI category mappings, so reporting/PSLC submissions are turnkey.
- **AC:**
  - G: I filter by period + category (Agri <= 2L, Small & Marginal Farmers). W: export. T: CSV/XLSX with anonymized farmer IDs, category, disbursement, outstanding, consent-confirmations; export log row created with filter snapshot + file URI.
  - G: re-export same period. T: new version stamped; old versions immutable.