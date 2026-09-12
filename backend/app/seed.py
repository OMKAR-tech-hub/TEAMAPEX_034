"""Create a rich, complete demo ecosystem for Kisan Setu.

Seeds:
1. Demo FPO: fpo_krishak / demo@1234 (Krishak Vahini FPO)
2. Demo Bank: bank_gramin / demo@1234 (Gramin Vikas Bank)
3. Demo Farmer: 9876543210 / demo@1234 (Ramesh Patel, 3.5 acres, Paddy, Kharif)
4. Production Records: verified historical yields (2024, 2025)
5. FPO Verification: attested with member_integrity_flag=True
6. Trust Passport: precomputed with deterministic credit limit & component scores
7. Consent Grant: active consent to bank_gramin with masked mobile
8. Evaluated Underwrite & Loan: active loan application with scheduled milestone tranches
9. FPO Social Vouch: active peer/FPO social guarantee
"""
from datetime import datetime

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import (
    ConsentLog,
    CreditProfile,
    DisbursementTranche,
    Farmer,
    FPOVerification,
    FpoVouch,
    LoanApplication,
    ProductionRecord,
    Role,
    TrustPassport,
    User,
)
from app.services.credit_engine import build_passport_record
from app.services.loan_service import build_tranche_plan, psl_tag
from app.services.underwrite_service import evaluate_underwrite


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # 1. Seed FPO Account
        fpo_user = db.query(User).filter(User.username == "fpo_krishak").first()
        if not fpo_user:
            fpo_user = User(
                username="fpo_krishak",
                password_hash=hash_password("demo@1234"),
                role=Role.FPO.value,
                name="Krishak Vahini FPO",
                wallet_balance=2500.0,
            )
            db.add(fpo_user)
            db.flush()
            print("Created FPO: fpo_krishak / demo@1234")
        else:
            print("FPO already exists: fpo_krishak")

        # 2. Seed Bank Account
        bank_user = db.query(User).filter(User.username == "bank_gramin").first()
        if not bank_user:
            bank_user = User(
                username="bank_gramin",
                password_hash=hash_password("demo@1234"),
                role=Role.BANK.value,
                name="Gramin Vikas Bank",
            )
            db.add(bank_user)
            db.flush()
            print("Created Bank: bank_gramin / demo@1234")
        else:
            print("Bank already exists: bank_gramin")

        # 3. Seed Demo Farmer Profile & User
        farmer_mobile = "9876543210"
        farmer = db.query(Farmer).filter(Farmer.mobile == farmer_mobile).first()
        if not farmer:
            farmer = Farmer(
                farmer_id="FAR-DEMO01",
                name="Ramesh Patel",
                mobile=farmer_mobile,
                village="Krishnapur",
                district="Nashik",
                state="Maharashtra",
                acreage=3.5,
                primary_crop="paddy",
                crop_season="Kharif",
                fpo_membership="Krishak Vahini FPO",
                crop_insured=True,
                insurance_sum_assured=150000.0,
                farm_experience_years=8,
            )
            db.add(farmer)
            db.flush()
            print(f"Created Farmer profile: {farmer.farmer_id} ({farmer.name})")

        farmer_user = db.query(User).filter(User.username == farmer_mobile).first()
        if not farmer_user:
            farmer_user = User(
                username=farmer_mobile,
                password_hash=hash_password("demo@1234"),
                role=Role.FARMER.value,
                name=farmer.name,
                farmer_id=farmer.id,
            )
            db.add(farmer_user)
            db.flush()
            print(f"Created Farmer login: {farmer_mobile} / demo@1234")
        else:
            print(f"Farmer user already exists: {farmer_mobile}")

        # 4. Seed Historical Production Records
        existing_records = db.query(ProductionRecord).filter(ProductionRecord.farmer_id == farmer.id).count()
        if existing_records == 0:
            p1 = ProductionRecord(
                farmer_id=farmer.id,
                crop_type="paddy",
                quantity=60.0,
                season="Kharif",
                year=2024,
                verified=1,
                weather_distress_observed=False,
                realized_price_per_q=3600.0,
            )
            p2 = ProductionRecord(
                farmer_id=farmer.id,
                crop_type="paddy",
                quantity=64.0,
                season="Kharif",
                year=2025,
                verified=1,
                weather_distress_observed=False,
                realized_price_per_q=3750.0,
            )
            db.add_all([p1, p2])
            db.flush()
            print("Seeded verified production records for 2024 & 2025")

        # 5. Seed FPO Verification
        existing_verif = db.query(FPOVerification).filter(FPOVerification.farmer_id == farmer.id).first()
        if not existing_verif:
            verif = FPOVerification(
                farmer_id=farmer.id,
                fpo_name=fpo_user.name,
                verification_status="verified",
                member_integrity_flag=True,
                verified_by=fpo_user.name,
                notes="Verified landholding, soil condition, and active FPO participation.",
                verification_date=datetime.utcnow(),
            )
            db.add(verif)
            db.flush()
            print("Seeded FPO Verification (status=verified, member_integrity=True)")

        # 6. Seed Trust Passport
        existing_passport = db.query(TrustPassport).filter(TrustPassport.farmer_id == farmer.id).first()
        if not existing_passport:
            record, _ = build_passport_record(db, farmer.id)
            passport = TrustPassport(**record)
            db.add(passport)
            db.flush()
            print(f"Computed Trust Passport: Limit Rs {passport.safe_credit_limit:,.0f} (Tier: {passport.credit_tier})")

        # 7. Seed Consent to Bank
        existing_consent = (
            db.query(ConsentLog)
            .filter(ConsentLog.farmer_id == farmer.id, ConsentLog.bank_user_id == bank_user.id)
            .first()
        )
        if not existing_consent:
            consent = ConsentLog(
                farmer_id=farmer.id,
                bank_user_id=bank_user.id,
                bank_name=bank_user.name,
                attributes=["name", "mobile", "village", "district", "acreage", "crop", "passport"],
                masked_attributes=["mobile"],
                granted=True,
                granted_at=datetime.utcnow(),
            )
            db.add(consent)
            db.flush()
            print("Granted Bank Consent with mobile attribute masking")

        # 8. Seed Underwriting Profile & Loan with Milestone Tranches
        existing_profile = db.query(CreditProfile).filter(CreditProfile.farmer_id == farmer.id).first()
        if not existing_profile:
            uw_result = evaluate_underwrite(
                db,
                farmer,
                requested_amount=100000.0,
                tenure_months=12,
                annual_interest_rate=0.11,
                origination_fee_rate=0.0175,
                purpose_category="input_finance",
            )
            print(f"Evaluated Underwrite: Safe Limit Rs {uw_result['safe_credit_limit']:,.0f}")

        existing_loan = db.query(LoanApplication).filter(LoanApplication.farmer_id == farmer.id).first()
        if not existing_loan:
            profile = db.query(CreditProfile).filter(CreditProfile.farmer_id == farmer.id).order_by(CreditProfile.id.desc()).first()
            loan = LoanApplication(
                application_uid="LN-DEMO001",
                farmer_id=farmer.id,
                credit_profile_id=profile.id if profile else None,
                principal=100000.0,
                tenure_months=12,
                annual_interest_rate=0.11,
                origination_fee_rate=0.0175,
                purpose_category="input_finance",
                purpose_note="Kharif paddy hybrid seeds, organic fertilizer, and irrigation setup",
                status="approved",
                decided_by=bank_user.name,
                decided_at=datetime.utcnow(),
                underwrite_snapshot={
                    "safe_credit_limit": profile.safe_credit_limit if profile else 115000.0,
                    "credit_tier": profile.credit_tier if profile else "High",
                    "risk_haircut": profile.risk_haircut if profile else 0.15,
                    "agri_risk_tier": profile.agri_risk_tier if profile else "low",
                    "model_version": "kisansetu-v1",
                },
            )
            loan.psl_category, loan.psl_eligible = psl_tag(loan, farmer)
            db.add(loan)
            db.flush()

            for tranche in build_tranche_plan(loan):
                db.add(tranche)
            db.flush()
            print("Seeded Loan LN-DEMO001 with 3 Milestone Disbursement Tranches (T1, T2, T3)")

        # 9. Seed FPO Social Vouch
        existing_vouch = db.query(FpoVouch).filter(FpoVouch.farmer_id == farmer.id).first()
        if not existing_vouch:
            vouch = FpoVouch(
                farmer_id=farmer.id,
                fpo_user_id=fpo_user.id,
                guarantee_style="first_loss",
                notes="Farmer has 100% on-time mandi delivery record and exemplary agronomic discipline.",
                status="active",
            )
            db.add(vouch)
            db.flush()
            print("Seeded FPO Social Vouch (guarantee_style=first_loss)")

        db.commit()
        print("\n=== Demo Seeding Complete! ===")
        print("Accounts ready for testing:")
        print("  Farmer: 9876543210 / demo@1234 (Ramesh Patel)")
        print("  FPO:    fpo_krishak / demo@1234 (Krishak Vahini FPO)")
        print("  Bank:   bank_gramin / demo@1234 (Gramin Vikas Bank)")
    finally:
        db.close()


if __name__ == "__main__":
    seed()