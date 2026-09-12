"""Loan lifecycle services: tranche plan, escrow settlement, risk recalibration.

Revenue invariants (RBI DLG): the farmer is never charged a fee. The FPO
facilitation fee and platform settlement fee are value-chain charges deducted
from the mandi sale proceeds before the EMI and residual are computed.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.credit_profile import CreditProfile
from app.models.farmer import Farmer
from app.models.loan import DisbursementTranche, LoanApplication, RiskEvent, Settlement
from app.models.user import User
from app.services.underwrite_service import annual_emi

FPO_FACILITATION_RATE = 0.02  # value-chain fee -> FPO wallet
PLATFORM_SETTLEMENT_FEE_RATE = 0.0015  # value-chain settlement micro-fee

TRANCHES = [
    # (no, label, share, payee_type, payee_ref, release rule)
    (1, "T1 Inputs", 0.40, "vendor", "seeds-fertilizer-vendor", "crop_planted_geotag_ok"),
    (2, "T2 Staged milestone", 0.50, "vendor", "operations-vendor", "crop_stage_advanced_weather_ok"),
    (3, "T3 Post-harvest", 0.10, "farmer", "farmer-bank-account", "harvest_expected_geotag_ok"),
]

LOSS_RATIOS = {"mild": 0.20, "moderate": 0.40, "severe": 0.60}
SEVERITY_ACTIONS = {"mild": "pause", "moderate": "block_tranches", "severe": "moratorium"}


def build_tranche_plan(loan: LoanApplication) -> list[DisbursementTranche]:
    tranches = []
    for no, label, share, payee_type, payee_ref, rule in TRANCHES:
        tranches.append(
            DisbursementTranche(
                loan_application_id=loan.id,
                tranche_no=no,
                label=label,
                amount=round(loan.principal * share, 2),
                payee_type=payee_type,
                payee_ref=payee_ref,
                status="scheduled",
                release_rule={"rule": rule, "required": ["no_risk_event"], "paid_to": payee_type},
            )
        )
    return tranches


def psl_tag(loan: LoanApplication, farmer: Farmer) -> tuple[str, bool]:
    if loan.principal <= 200000 and farmer.acreage <= 5.0:
        return "Small & Marginal Farmer - Agri <= 2L", True
    if loan.principal <= 200000:
        return "Agri <= 2L", True
    return "Agri (above 2L)", True


def loan_to_dict(db: Session, loan: LoanApplication) -> dict:
    farmer = db.get(Farmer, loan.farmer_id)
    emi = annual_emi(loan.principal, loan.annual_interest_rate, loan.tenure_months)
    total_payable = round(emi * loan.tenure_months, 2)
    return {
        "id": loan.id,
        "application_uid": loan.application_uid,
        "farmer_id": farmer.farmer_id if farmer else None,
        "farmer_name": farmer.name if farmer else None,
        "principal": loan.principal,
        "tenure_months": loan.tenure_months,
        "annual_interest_rate": loan.annual_interest_rate,
        "origination_fee_rate": loan.origination_fee_rate,
        "purpose_category": loan.purpose_category,
        "purpose_note": loan.purpose_note,
        "agri_risk_tier": (loan.underwrite_snapshot or {}).get("agri_risk_tier"),
        "status": loan.status,
        "psl_category": loan.psl_category,
        "psl_eligible": loan.psl_eligible,
        "amount_disbursed": loan.amount_disbursed,
        "amount_repaid": loan.amount_repaid,
        "emi_paused": loan.emi_paused,
        "monthly_emi": emi,
        "total_payable": total_payable,
        "outstanding": round(max(0.0, total_payable - loan.amount_repaid), 2),
        "repayment_progress": round(min(100.0, (loan.amount_repaid / total_payable) * 100), 1)
        if total_payable > 0
        else 0.0,
        "decided_by": loan.decided_by,
        "decided_at": loan.decided_at.isoformat() if loan.decided_at else None,
        "tranches": [
            {
                "id": t.id,
                "tranche_no": t.tranche_no,
                "label": t.label,
                "amount": t.amount,
                "payee_type": t.payee_type,
                "payee_ref": t.payee_ref,
                "status": t.status,
                "released_at": t.released_at.isoformat() if t.released_at else None,
            }
            for t in loan.tranches
        ],
        "settlements": [
            {
                "id": s.id,
                "sale_value": s.sale_value,
                "crop": s.crop,
                "fpo_facilitation_amt": s.fpo_facilitation_amt,
                "platform_settlement_fee": s.platform_settlement_fee,
                "emi_paid": s.emi_paid,
                "residual_to_farmer": s.residual_to_farmer,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in loan.settlements
        ],
        "risk_events": [
            {
                "id": r.id,
                "event_type": r.event_type,
                "severity": r.severity,
                "loss_ratio": r.loss_ratio,
                "action": r.action,
                "declared_at": r.declared_at.isoformat() if r.declared_at else None,
            }
            for r in loan.risk_events
        ],
    }


def create_loan(
    db: Session,
    farmer: Farmer,
    credit_profile: CreditProfile,
    principal: float,
    tenure_months: int,
    annual_interest_rate: float,
    origination_fee_rate: float = 0.0175,
    purpose_category: str = "working_capital",
    purpose_note: str = None,
) -> LoanApplication:
    loan = LoanApplication(
        application_uid=f"LN-{uuid.uuid4().hex[:8].upper()}",
        farmer_id=farmer.id,
        credit_profile_id=credit_profile.id,
        principal=principal,
        tenure_months=tenure_months,
        annual_interest_rate=annual_interest_rate,
        origination_fee_rate=origination_fee_rate,
        purpose_category=purpose_category,
        purpose_note=purpose_note,
        status="underwritten",
        underwrite_snapshot={
            "safe_credit_limit": credit_profile.safe_credit_limit,
            "credit_tier": credit_profile.credit_tier,
            "risk_haircut": credit_profile.risk_haircut,
            "agri_risk_tier": credit_profile.agri_risk_tier,
            "model_version": credit_profile.model_version,
        },
    )
    loan.psl_category, loan.psl_eligible = psl_tag(loan, farmer)
    db.add(loan)
    db.commit()
    db.refresh(loan)
    return loan


def approve_loan(db: Session, loan: LoanApplication, by: User) -> LoanApplication:
    loan.status = "approved"
    loan.decided_by = by.name
    loan.decided_at = __import__("datetime").datetime.utcnow()
    for tranche in build_tranche_plan(loan):
        db.add(tranche)
    db.commit()
    db.refresh(loan)
    return loan


def release_tranche(db: Session, loan: LoanApplication, tranche: DisbursementTranche) -> DisbursementTranche:
    if tranche.status != "scheduled":
        raise ValueError(f"Tranche {tranche.tranche_no} is {tranche.status}, not releasable")
    blocking = (
        db.query(RiskEvent)
        .filter(
            RiskEvent.loan_application_id == loan.id,
            RiskEvent.action.in_(["block_tranches", "moratorium"]),
            RiskEvent.declared_at.isnot(None),
        )
        .order_by(RiskEvent.id.desc())
        .first()
    )
    if blocking is not None:
        raise ValueError(
            f"Tranche release blocked by active risk event: {blocking.event_type}/{blocking.action}"
        )
    tranche.status = "released"
    tranche.released_at = __import__("datetime").datetime.utcnow()
    loan.amount_disbursed = round(loan.amount_disbursed + tranche.amount, 2)
    loan.status = "disbursing" if loan.status in ("approved", "underwritten", "disbursing") else loan.status
    db.commit()
    db.refresh(tranche)
    return tranche


def process_settlement(
    db: Session,
    loan: LoanApplication,
    sale_value: float,
    crop: str = None,
    agmarknet_price_per_q: float = None,
) -> Settlement:
    emi = annual_emi(loan.principal, loan.annual_interest_rate, loan.tenure_months)
    total_payable = round(emi * loan.tenure_months, 2)
    remaining = round(max(0.0, total_payable - loan.amount_repaid), 2)

    fpo_fee = round(sale_value * FPO_FACILITATION_RATE, 2)
    platform_fee = round(sale_value * PLATFORM_SETTLEMENT_FEE_RATE, 2)
    chain_value = sale_value - fpo_fee - platform_fee

    if loan.emi_paused:
        emi_paid = 0.0
    else:
        emi_paid = round(min(remaining, chain_value), 2)

    residual = round(chain_value - emi_paid, 2)

    loan.amount_repaid = round(loan.amount_repaid + emi_paid, 2)
    if total_payable > 0 and loan.amount_repaid >= total_payable - 0.01:
        loan.status = "repaid"

    settlement = Settlement(
        loan_application_id=loan.id,
        sale_value=round(sale_value, 2),
        crop=crop,
        agmarknet_price_per_q=agmarknet_price_per_q,
        fpo_facilitation_amt=fpo_fee,
        platform_settlement_fee=platform_fee,
        emi_paid=emi_paid,
        residual_to_farmer=residual,
        receipt_json={
            "line_items": [
                {"item": "gross mandi sale", "amount": round(sale_value, 2), "paid_to": "farmer escrow"},
                {"item": "FPO facilitation (value chain)", "amount": fpo_fee, "paid_to": "FPO wallet"},
                {"item": "platform settlement fee (value chain)", "amount": platform_fee, "paid_to": "platform"},
                {"item": "loan EMI (principal + interest)", "amount": emi_paid, "paid_to": "lender"},
                {"item": "residual to farmer", "amount": residual, "paid_to": "farmer bank account"},
            ],
            "farmer_fees_total": 0.0,
            "rbi_dlg_invariant": "farmer_charged_zero",
        },
    )
    db.add(settlement)
    db.commit()

    fpo_handle = None
    if loan.farmer is not None:
        fpo_handle = loan.farmer.fpo_membership
    fpo_user = None
    if fpo_handle:
        fpo_user = (
            db.query(User)
            .filter(
                User.role == "fpo",
                ((User.username == fpo_handle) | (User.name == fpo_handle)),
            )
            .first()
        )
    if fpo_user is None:
        fpo_user = (
            db.query(User)
            .filter(User.role == "fpo", User.farmer_id.is_(None))
            .order_by(User.id)
            .first()
        )
    if fpo_user is not None:
        fpo_user.wallet_balance = round(fpo_user.wallet_balance + fpo_fee, 2)
        db.commit()
    db.refresh(loan)
    db.refresh(settlement)
    return settlement


def declare_risk_event(
    db: Session,
    loan: LoanApplication,
    event_type: str,
    severity: str,
    loss_ratio: float = None,
) -> RiskEvent:
    loss = loss_ratio if loss_ratio is not None else LOSS_RATIOS.get(severity, 0.40)
    action = SEVERITY_ACTIONS.get(severity, "recalibrate")
    if severity == "severe":
        loan.emi_paused = True
    elif severity == "mild":
        loan.emi_paused = True
    else:
        loan.emi_paused = False

    event = RiskEvent(
        loan_application_id=loan.id,
        event_type=event_type,
        severity=severity,
        loss_ratio=loss,
        action=action,
    )
    db.add(event)

    if action in ("block_tranches", "moratorium"):
        for tranche in loan.tranches:
            if tranche.status == "scheduled":
                tranche.status = "blocked"
        if action == "moratorium":
            loan.status = "active"

    profile = (
        db.query(CreditProfile)
        .filter(CreditProfile.id == loan.credit_profile_id)
        .first()
    )
    if profile is not None:
        profile.weather_loss_ratio = loss
        profile.safe_credit_limit = round(
            profile.safe_credit_limit * (1.0 - loss), 2
        )
        db.commit()
    db.commit()
    db.refresh(event)
    return event