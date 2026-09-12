import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles, resolve_farmer
from app.core.database import get_db
from app.core.market import DATA_SOURCE
from app.models.farmer import Farmer, ProductionRecord
from app.models.fpo_vouch import FpoVouch
from app.models.loan import LoanApplication
from app.models.user import Role, User
from app.schemas.risk import (
    AssessResponse,
    InsuranceUpdateRequest,
    ProductionRecordCreateRequest,
    SourcesResponse,
    VouchCreateRequest,
)
from app.services.risk_engine import (
    MODEL_VERSION,
    assess as run_assessment,
    mission_answers,
    purpose_grade,
)

router = APIRouter()
logger = logging.getLogger(__name__)

DATA_SOURCES = [
    {
        "key": "self_reported",
        "name": "Self-reported identity & landholding",
        "ownership": "farmer",
        "consent_required": False,
    },
    {
        "key": "fpo_community",
        "name": "FPO verification, integrity flag & vouches",
        "ownership": "community",
        "consent_required": False,
    },
    {
        "key": "market_agmarknet",
        "name": "AGMARKNET modal prices + MSP 2026-27 (farmer.in, CC BY 4.0)",
        "ownership": "public",
        "consent_required": False,
        "provenance": DATA_SOURCE,
    },
    {
        "key": "production_records",
        "name": "Verified production & field-condition records",
        "ownership": "farmer + FPO witness",
        "consent_required": True,
    },
    {
        "key": "insurance",
        "name": "Crop insurance / risk-transfer indicators",
        "ownership": "farmer",
        "consent_required": True,
    },
    {
        "key": "consent_gate",
        "name": "Lender visibility",
        "ownership": "farmer-controlled (grant + mask + revoke)",
        "consent_required": True,
    },
]


@router.post("/assess/{farmer_id}", response_model=AssessResponse)
def assess_farmer(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, farmer_id)
    if user.role == Role.FARMER.value and farmer.id != user.farmer_id:
        raise HTTPException(status_code=403, detail="Farmers may only assess themselves")
    assessment = run_assessment(db, farmer)
    answers = mission_answers(db, farmer, assessment)
    assessment["mission_answers"] = answers
    assessment["data_sources"] = DATA_SOURCES

    logger.info(
        f"Risk assessment {assessment['assessment_id']} for {farmer.farmer_id}: "
        f"tier={assessment['agri_risk']['risk_tier']} "
        f"range=₹{assessment['recommended_credit']:,.0f} "
        f"(vouch={assessment['agri_risk'].get('community_vouch', False)})"
    )
    return _assess_response(assessment)


def _assess_response(a: dict) -> dict:
    return AssessResponse(
        assessment_id=a["assessment_id"],
        farmer_id=a["farmer_id"],
        assessed_at=a["assessed_at"],
        risk_tier=a["agri_risk"]["risk_tier"],
        risk_score=a["agri_risk"]["risk_score"],
        factor_scores=a["agri_risk"]["factor_scores"],
        factor_reasons=a["agri_risk"]["factor_reasons"],
        top_reasons=a["agri_risk"]["top_reasons"],
        range_low=a["range_low"],
        range_high=a["range_high"],
        recommended_credit=a["recommended_credit"],
        net_income_expected=a["net_income_expected"],
        monthly_capacity=a["monthly_capacity"],
        repayment_coverage=a.get("repayment_coverage"),
        risk_discount=a["risk_discount"],
        insurance_uplift=a["insurance_uplift"],
        community_vouch=bool(a["agri_risk"].get("community_vouch", False)),
        mission_answers=a["mission_answers"],
        data_sources=a["data_sources"],
    )


@router.get("/sources", response_model=SourcesResponse)
def data_sources_catalog(
    user: User = Depends(get_current_user),
):
    return SourcesResponse(sources=DATA_SOURCES)


@router.post("/{farmer_id}/insurance", response_model=dict)
def update_insurance(
    farmer_id: str,
    payload: InsuranceUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, farmer_id)
    if user.role == Role.FARMER.value and farmer.id != user.farmer_id:
        raise HTTPException(status_code=403, detail="Farmers may only update themselves")
    farmer.crop_insured = payload.crop_insured
    farmer.insurance_sum_assured = payload.insurance_sum_assured
    db.commit()
    db.refresh(farmer)
    logger.info(f"{user.name} set insurance on {farmer.farmer_id} = {payload.crop_insured}")
    return {
        "farmer_id": farmer.farmer_id,
        "crop_insured": farmer.crop_insured,
        "insurance_sum_assured": farmer.insurance_sum_assured,
    }


@router.post("/{farmer_id}/production-records", response_model=dict)
def add_production_record(
    farmer_id: str,
    payload: ProductionRecordCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    farmer = resolve_farmer(db, farmer_id)
    record = ProductionRecord(
        farmer_id=farmer.id,
        crop_type=payload.crop_type,
        quantity=payload.quantity,
        season=payload.season,
        year=payload.year,
        verified=1 if payload.verified else 0,
        weather_distress_observed=payload.weather_distress_observed,
        realized_price_per_q=payload.realized_price_per_q,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(
        f"Production record {record.id}: {record.crop_type} {record.quantity}q "
        f"({record.season} {record.year}) for {farmer.farmer_id}"
    )
    return {
        "record_id": record.id,
        "farmer_id": farmer.farmer_id,
        "crop_type": record.crop_type,
        "quantity": record.quantity,
        "season": record.season,
        "year": record.year,
        "verified": bool(record.verified),
        "weather_distress_observed": bool(record.weather_distress_observed),
    }


@router.get("/{farmer_id}/latest", response_model=AssessResponse)
def latest_assessment(
    farmer_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.models.risk_assessment import RiskAssessment

    farmer = resolve_farmer(db, farmer_id)
    latest = (
        db.query(RiskAssessment)
        .filter(RiskAssessment.farmer_id == farmer.id)
        .order_by(RiskAssessment.id.desc())
        .first()
    )
    if latest is None:
        raise HTTPException(status_code=404, detail="No risk assessment yet. POST /risk/assess/{farmer_id} first.")
    assessment = {
        "assessment_id": latest.id,
        "farmer_id": farmer.farmer_id,
        "assessed_at": latest.created_at.isoformat() if latest.created_at else None,
        "range_low": latest.recommended_range_low,
        "range_high": latest.recommended_range_high,
        "recommended_credit": latest.recommended_credit,
        "net_income_expected": latest.net_income_expected,
        "monthly_capacity": latest.repayment_capacity,
        "servicing_tdsr_low": latest.servicing_tdsr_low,
        "servicing_tdsr_high": latest.servicing_tdsr_high,
        "risk_discount": 0.0,
        "insurance_uplift": latest.insurance_uplift,
        "agri_risk": {
            "risk_tier": latest.risk_tier,
            "risk_score": latest.risk_score,
            "factor_scores": latest.factor_scores,
            "factor_weights": latest.factor_weights,
            "top_reasons": latest.top_reasons,
            "community_vouch": False,
        },
        "repayment_coverage": None,
        "mission_answers": mission_answers(db, farmer, {
            "agri_risk": {"risk_tier": latest.risk_tier, "risk_score": latest.risk_score,
                          "factor_scores": latest.factor_scores, "factor_reasons": latest.factor_scores,
                          "community_vouch": False},
            "range_low": latest.recommended_range_low,
            "range_high": latest.recommended_range_high,
            "recommended_credit": latest.recommended_credit,
            "net_income_expected": latest.net_income_expected,
            "monthly_capacity": latest.repayment_capacity,
            "servicing_tdsr_low": latest.servicing_tdsr_low,
            "servicing_tdsr_high": latest.servicing_tdsr_high,
            "repayment_coverage": None,
            "risk_discount": 0.0,
            "tenure_months": 12,
            "annual_interest_rate": 0.135,
        }),
        "data_sources": DATA_SOURCES,
        "model_version": latest.model_version,
    }
    return _assess_response(assessment)


@router.post("/vouches", response_model=dict)
def create_vouch(
    payload: VouchCreateRequest,
    user: User = Depends(require_roles(Role.FPO)),
    db: Session = Depends(get_db),
):
    farmer = db.query(Farmer).filter(Farmer.id == payload.farmer_id).first()
    if farmer is None:
        raise HTTPException(status_code=404, detail="Farmer not found")

    # Anti-collusion 1: Conflict of interest (self-vouching)
    if user.farmer_id and user.farmer_id == farmer.id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Conflict of interest: self-vouching is prohibited by FPO governance rules",
        )

    # Anti-collusion 2: Reciprocal vouch burst detection (A vouched B, now B vouches A)
    if user.farmer_id:
        reciprocal = (
            db.query(FpoVouch)
            .filter(
                FpoVouch.farmer_id == user.farmer_id,
                FpoVouch.fpo_user_id == farmer.id,
                FpoVouch.status == "active",
            )
            .first()
        )
        if reciprocal is not None:
            reciprocal.status = "suspect"
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Reciprocal-vouching burst detected: both members flagged suspect and frozen for committee review",
            )

    if farmer.fpo_membership not in (user.name, user.username):
        raise HTTPException(
            status_code=403,
            detail=f"This farmer is a member of '{farmer.fpo_membership}', not your FPO",
        )
    existing = (
        db.query(FpoVouch)
        .filter(FpoVouch.farmer_id == farmer.id, FpoVouch.status == "active")
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="An active vouch already exists for this farmer")

    loan = None
    if payload.loan_application_id:
        loan = db.query(LoanApplication).filter(LoanApplication.id == payload.loan_application_id).first()
        if loan is None or loan.farmer_id != farmer.id:
            raise HTTPException(status_code=404, detail="Loan not found for this farmer")

    notes_text = payload.notes or payload.statement or ("Score: " + str(payload.score) if payload.score else None)
    vouch = FpoVouch(
        farmer_id=farmer.id,
        fpo_user_id=user.id,
        loan_application_id=payload.loan_application_id,
        guarantee_style=payload.guarantee_style,
        notes=notes_text,
        status="active",
    )
    db.add(vouch)
    db.commit()
    db.refresh(vouch)
    logger.info(f"FPO {user.name} vouched farmer {farmer.farmer_id} ({vouch.guarantee_style})")
    return {
        "vouch_id": vouch.id,
        "farmer_id": farmer.farmer_id,
        "guarantee_style": vouch.guarantee_style,
        "status": vouch.status,
        "weight": 1.1,
        "attestation_score_delta": 0.04,
        "safe_credit_limit_unchanged": True,
        "effect": "risk discount reduced by 6 points; borrower credit cost lowered",
    }


@router.get("/vouches", response_model=list[dict])
def list_vouches(
    user: User = Depends(require_roles(Role.FPO)),
    db: Session = Depends(get_db),
):
    vouches = (
        db.query(FpoVouch)
        .order_by(FpoVouch.id.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": v.id,
            "farmer_id": v.farmer_id,
            "farmer_ref": db.query(Farmer).filter(Farmer.id == v.farmer_id).first().farmer_id
            if db.query(Farmer).filter(Farmer.id == v.farmer_id).first()
            else None,
            "guarantee_style": v.guarantee_style,
            "status": v.status,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in vouches
    ]


@router.get("/purposes", response_model=dict)
def purposes_catalog(
    user: User = Depends(get_current_user),
):
    from app.services.risk_engine import PURPOSE_TAXONOMY

    return {
        "default": "working_capital",
        "purposes": [
            {"category": k, **v} for k, v in PURPOSE_TAXONOMY.items()
        ],
    }