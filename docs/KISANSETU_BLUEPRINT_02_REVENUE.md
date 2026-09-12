# 2. Transparent Revenue & Flow-of-Funds Architecture

## 2.1 Money movement

```
 Bank (lender)        Platform (escrow)                Counterparty
     |                        |                              |
     | 1. loan approved       |                              |
     +------- principal L --->|                              |
     |                        | 2. T1 ~40%: vendors          |
     |                        +----(seeds/fertilizer)------>| Vendor
     |                        | 3. T2 ~60%: on crop stage + geotag + weather OK
     |                        +----(operations)------------>| Vendor/Farmer
     |                        |                              |
     |                        | 4. Farmer sells at mandi    |
     |                        |    (AGMARKNET floor price)  |
     |                        <--------- sale value --------| Buyer
     |                        | 5. Settlement:
     |                        |    - FPO facilitation 2%  -> FPO wallet
     |                        |    - platform settlement fee (value chain, NOT farmer)
     |                        | 6. EMI (principal+interest) -> Bank
     | <--------- EMI --------|    auto from escrow
     |                        | 7. residual surplus -> Farmer bank account
```

Farmer money flows only through: (a) input vendors they chose, (b) their sale proceeds, (c) their own bank account. The platform never interposes a fee account on the farmer side.

## 2.2 Worked numbers
- Principal `D = Rs 1,20,000`, contract rate `r = 11% p.a.`, tenure `n = 10 months`.
- Monthly annuity: `EMI = D*(r/12)*(1+r/12)^n / ((1+r/12)^n - 1) = Rs 12,617`. Total repaid = `10 * 12,617 = Rs 1,26,170`.
- **Farmer pays exactly principal + contract interest (Rs 6,170), nothing else.**
- Platform origination fee `k*D = 1.75% * 1,20,000 = Rs 2,100`, billed to the **bank** (B2B service fee out of bank spread, never booked against the farmer).
- Mandi: `3.5 acres * 18 q/acre * Rs 2,100/q = Rs 1,32,300` gross. Settlement: FPO facilitation 2% = Rs 2,646 (value chain) to FPO wallet; platform settlement micro-fee ~Rs 250 (value chain); EMI Rs 12,617 to bank; residual to farmer.

## 2.3 Mathematical proof the farmer is never charged hidden fees

Definitions:
- `L` = principal, `r_b` = bank contracted annual rate, `n` = tenure (months), `M(L,r_b,n)` = contract annuity.
- `k in [1.5%, 2.0%]` = B2B origination fee (paid by bank).
- `F_f` = farmer-facing fee vector.

**I1 (no borrower fee).** For every loan the consent artifact + KFS must satisfy `sum(F_f) = 0`. Enforced in code at consent-grant time:
```
assert sum(fee.amount for fee in farmer_fee_lines) == 0
```
Violations reject the grant.

**I2 (interest independence).** `d(EffectiveAPR_to_farmer)/dk = 0`. Because `M` depends only on `(L, r_b, n)` and `k` is charged to the bank:
```
EffectiveAPR_farmer = r_b
TotalFarmerOutflow   = sum_i M(L, r_b, n) = L + interest(L, r_b, n)
```

**I3 (disbursement integrity).** Net principal received equals gross: `NetDisbursed = L` with payees in {vendor, escrow, farmer-account}; no platform/processing/logistics haircut exists in `F_f`.

**I4 (settlement transparency).** Let `V` = gross mandi value, `c` = facilitation rate, `s` = settlement fee. Farmer ledger: `+V`, `-0` platform line, `-fpo facilitation` (stated value-chain charge), `-EMI`. Platform revenue `= k*L + s*(value chain)` is extractive only from banks and the value chain. Hence:
```
FarmerNetCashFlow = V*(1 - shown charges) - sum M(L, r_b, n)
```
Every `shown charge` appears in the settlement receipt, so the farmer's exposure is at most their contracted obligation `L + interest`.

**Corollary (no rate pressure).** Any lender wanting queue placement pays the same `k`; competition is on `r_b`, benefiting the farmer. Prepayment/exit is penalty-free.

## 2.4 RBI DLG compliance mapping
| DLG requirement | Implementation |
|---|---|
| No charges to borrower beyond interest | `sum(F_f) = 0` invariant + fee-schema validation |
| Key Fact Statement | Auto-generated KFS (EMI table, APR, amount, settlement lines) |
| Digital/audio consent with e-record | `data_consents.artifact_uri` + sha256 + language tag |
| Cooling-off / easy exit | Revoke consent anytime; prepayment without penalty |
| Loan only for stated purpose | Tranche rule engine pays vendors/escrow |
| Insurance premium pass-through in full | Claim lines never netted by platform fees |