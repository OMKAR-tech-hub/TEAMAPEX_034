"""
KisanSetu Demo Data Seeder
Run: python -m backend.seed_demo

Demo credentials:
  farmer@kisansetu.demo  / Demo@1234
  fpo@kisansetu.demo     / Demo@1234
  lender@kisansetu.demo  / Demo@1234
  admin@kisansetu.demo   / Demo@1234

All external data (market prices, benchmarks) is DEMO/SYNTHETIC.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime, timedelta
from backend.database import SessionLocal, engine, Base
from backend.models import (
    User, UserRole, Farmer, Farm, CropSeason, ProductionRecord, SalesRecord,
    FPO, FPOManager, FPOMembership, MembershipStatus,
    Verification, VerificationStatus,
    Lender, CreditApplication, ApplicationStatus,
    TrustPassport, Consent, DataAccessLog, AuditLog,
)
from backend.auth.security import get_password_hash

DEMO_PASSWORD = "Demo@1234"
DEMO_NOTE = "DEMO/SYNTHETIC — not real government data"


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Skip if already seeded
        if db.query(User).filter(User.email == "farmer@kisansetu.demo").first():
            print("Demo data already exists. Skipping seed.")
            db.close()
            return

        print("Seeding demo data...")

        # ─────────────────────────────────────────────
        # ADMIN
        # ─────────────────────────────────────────────
        admin = User(
            email="admin@kisansetu.demo",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.ADMIN, is_active=True,
        )
        db.add(admin)
        db.flush()

        # ─────────────────────────────────────────────
        # FPO
        # ─────────────────────────────────────────────
        fpo = FPO(
            name="Madhya Pradesh Kisan Samridhi FPO",
            registration_number="FPO-MP-2021-001",
            district="Sehore", state="Madhya Pradesh",
            contact_person="Ramesh Verma",
            phone="9876543210",
            email="fpo@kisansetu.demo",
        )
        db.add(fpo)
        db.flush()

        fpo_user = User(
            email="fpo@kisansetu.demo",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.FPO_MANAGER, is_active=True,
        )
        db.add(fpo_user)
        db.flush()

        fpo_mgr = FPOManager(
            user_id=fpo_user.id,
            fpo_id=fpo.id,
            name="Ramesh Verma",
            phone="9876543210",
        )
        db.add(fpo_mgr)
        db.flush()

        # ─────────────────────────────────────────────
        # LENDER
        # ─────────────────────────────────────────────
        lender_user = User(
            email="lender@kisansetu.demo",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.LENDER, is_active=True,
        )
        db.add(lender_user)
        db.flush()

        lender = Lender(
            user_id=lender_user.id,
            organization_name="MP Gramin Bank",
            lender_type="regional_rural_bank",
            license_number="RRB-MP-2001",
            district="Sehore", state="Madhya Pradesh",
            contact_person="Sunita Sharma",
            phone="9812345678",
        )
        db.add(lender)
        db.flush()

        # ─────────────────────────────────────────────
        # PRIMARY DEMO FARMER — Arjun Patel (compelling profile)
        # ─────────────────────────────────────────────
        farmer_user = User(
            email="farmer@kisansetu.demo",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            role=UserRole.FARMER, is_active=True,
        )
        db.add(farmer_user)
        db.flush()

        arjun = Farmer(
            user_id=farmer_user.id,
            name="Arjun Patel",
            phone="9001234567",
            address="Village Chandpur, Post Sehore",
            village="Chandpur", district="Sehore", state="Madhya Pradesh",
            date_of_birth=datetime(1985, 6, 15),
            gender="male",
            farm_size=7.5,
        )
        db.add(arjun)
        db.flush()

        # Farms
        farm1 = Farm(
            farmer_id=arjun.id, farm_name="Patel Farm - Field A",
            village="Chandpur", district="Sehore", state="Madhya Pradesh",
            total_area_acres=5.0, soil_type="black cotton",
            irrigation_type="borewell drip",
        )
        farm2 = Farm(
            farmer_id=arjun.id, farm_name="Patel Farm - Field B",
            village="Chandpur", district="Sehore", state="Madhya Pradesh",
            total_area_acres=2.5, soil_type="red loam",
            irrigation_type="canal",
        )
        db.add_all([farm1, farm2])
        db.flush()

        # Crop Seasons
        s1 = CropSeason(farm_id=farm1.id, crop_name="wheat", season="rabi", year=2024,
                        area_sown_acres=5.0, expected_yield_quintals=80.0, actual_yield_quintals=78.5,
                        sowing_date=datetime(2023, 11, 10), expected_harvest_date=datetime(2024, 3, 20))
        s2 = CropSeason(farm_id=farm1.id, crop_name="soybean", season="kharif", year=2024,
                        area_sown_acres=5.0, expected_yield_quintals=42.0, actual_yield_quintals=40.0,
                        sowing_date=datetime(2024, 6, 20), expected_harvest_date=datetime(2024, 10, 15))
        s3 = CropSeason(farm_id=farm2.id, crop_name="wheat", season="rabi", year=2025,
                        area_sown_acres=2.5, expected_yield_quintals=40.0, actual_yield_quintals=41.0,
                        sowing_date=datetime(2024, 11, 12), expected_harvest_date=datetime(2025, 3, 25))
        db.add_all([s1, s2, s3])
        db.flush()

        # Production Records — 3 seasons of history
        pr1 = ProductionRecord(
            farmer_id=arjun.id, crop_season_id=s1.id,
            crop_type="wheat", quantity=78.5, unit="quintals",
            season="rabi", year=2024, area_acres=5.0,
            verified=True, fpo_verified=True,
            verified_by="Ramesh Verma (FPO)",
            verification_date=datetime(2024, 4, 1),
            data_source="fpo_verified",
        )
        pr2 = ProductionRecord(
            farmer_id=arjun.id, crop_season_id=s2.id,
            crop_type="soybean", quantity=40.0, unit="quintals",
            season="kharif", year=2024, area_acres=5.0,
            verified=True, fpo_verified=True,
            verified_by="Ramesh Verma (FPO)",
            verification_date=datetime(2024, 11, 1),
            data_source="fpo_verified",
        )
        pr3 = ProductionRecord(
            farmer_id=arjun.id, crop_season_id=s3.id,
            crop_type="wheat", quantity=41.0, unit="quintals",
            season="rabi", year=2025, area_acres=2.5,
            verified=False, fpo_verified=False,
            data_source="farmer_provided",
        )
        db.add_all([pr1, pr2, pr3])
        db.flush()

        # Sales Records
        sr1 = SalesRecord(
            farmer_id=arjun.id, production_record_id=pr1.id,
            crop_name="wheat", quantity_sold=70.0, unit="quintals",
            price_per_unit=2100.0, total_amount=147000.0,
            market_name="Sehore Mandi", district="Sehore", state="Madhya Pradesh",
            sale_date=datetime(2024, 4, 10), buyer_type="mandi",
            verified=True, fpo_verified=True, verified_by="Ramesh Verma (FPO)",
            data_source="fpo_verified",
        )
        sr2 = SalesRecord(
            farmer_id=arjun.id, production_record_id=pr2.id,
            crop_name="soybean", quantity_sold=38.0, unit="quintals",
            price_per_unit=4350.0, total_amount=165300.0,
            market_name="Bhopal Mandi", district="Bhopal", state="Madhya Pradesh",
            sale_date=datetime(2024, 11, 20), buyer_type="private",
            verified=False, fpo_verified=False,
            data_source="farmer_provided",
        )
        db.add_all([sr1, sr2])
        db.flush()

        # FPO Membership
        membership = FPOMembership(
            farmer_id=arjun.id, fpo_id=fpo.id,
            membership_date=datetime(2022, 4, 1),
            membership_number="FPO-MP-001-2022-0042",
            status=MembershipStatus.ACTIVE,
            verified=True, verified_by="Ramesh Verma",
            verification_date=datetime(2022, 4, 2),
        )
        db.add(membership)
        db.flush()

        # Verifications
        v1 = Verification(
            farmer_id=arjun.id, fpo_id=fpo.id,
            verification_type="production", record_type="production", record_id=pr1.id,
            status=VerificationStatus.VERIFIED,
            requested_by="Ramesh Verma (FPO)",
            verified_by="Ramesh Verma", verification_date=datetime(2024, 4, 1),
            notes="Verified via mandi receipt and field visit",
        )
        v2 = Verification(
            farmer_id=arjun.id, fpo_id=fpo.id,
            verification_type="production", record_type="production", record_id=pr2.id,
            status=VerificationStatus.VERIFIED,
            requested_by="Ramesh Verma (FPO)",
            verified_by="Ramesh Verma", verification_date=datetime(2024, 11, 1),
            notes="Verified via mandi receipt",
        )
        v3 = Verification(
            farmer_id=arjun.id, fpo_id=fpo.id,
            verification_type="sales", record_type="sales", record_id=sr1.id,
            status=VerificationStatus.VERIFIED,
            verified_by="Ramesh Verma", verification_date=datetime(2024, 4, 11),
        )
        db.add_all([v1, v2, v3])
        db.flush()

        # ─────────────────────────────────────────────
        # 4 ADDITIONAL FARMERS
        # ─────────────────────────────────────────────
        other_farmers_data = [
            ("Meena Devi", "meena.devi@demo.farm", "rice", "Punjab", "Amritsar", 3.5),
            ("Suresh Kumar", "suresh.kumar@demo.farm", "cotton", "Gujarat", "Rajkot", 6.0),
            ("Laxmi Bai", "laxmi.bai@demo.farm", "maize", "Karnataka", "Davangere", 4.0),
            ("Raju Yadav", "raju.yadav@demo.farm", "wheat", "Madhya Pradesh", "Bhopal", 2.5),
        ]
        demo_farmers = []
        for name, email, crop, state, district, acres in other_farmers_data:
            u = User(
                email=email, hashed_password=get_password_hash(DEMO_PASSWORD),
                role=UserRole.FARMER, is_active=True,
            )
            db.add(u)
            db.flush()
            f = Farmer(
                user_id=u.id, name=name, phone=f"900{len(demo_farmers)+2:07d}",
                village=f"Village {district}", district=district, state=state,
                farm_size=acres,
            )
            db.add(f)
            db.flush()
            # Single farm
            fm = Farm(
                farmer_id=f.id, farm_name=f"{name}'s Farm",
                district=district, state=state, total_area_acres=acres,
                irrigation_type="borewell" if state != "Punjab" else "canal",
            )
            db.add(fm)
            db.flush()
            # Single production record
            pr = ProductionRecord(
                farmer_id=f.id, crop_type=crop, quantity=acres * 10,
                unit="quintals", season="kharif", year=2024, area_acres=acres,
                verified=False, fpo_verified=False, data_source="farmer_provided",
            )
            db.add(pr)
            # Add to FPO if MP
            if state == "Madhya Pradesh":
                mbr = FPOMembership(
                    farmer_id=f.id, fpo_id=fpo.id,
                    membership_date=datetime(2023, 6, 1),
                    status=MembershipStatus.ACTIVE,
                    verified=True, verified_by="Ramesh Verma",
                    verification_date=datetime(2023, 6, 2),
                )
                db.add(mbr)
            demo_farmers.append(f)
        db.flush()

        # ─────────────────────────────────────────────
        # CREDIT APPLICATIONS
        # ─────────────────────────────────────────────
        app1 = CreditApplication(
            farmer_id=arjun.id, lender_id=lender.id,
            amount_requested=150000.0,
            purpose="Rabi wheat seed, fertilizer and drip irrigation repair",
            lender_type="regional_rural_bank",
            status=ApplicationStatus.UNDER_REVIEW,
            application_date=datetime(2025, 9, 1),
        )
        app2 = CreditApplication(
            farmer_id=demo_farmers[0].id,
            amount_requested=80000.0,
            purpose="Kharif paddy cultivation inputs",
            lender_type="cooperative",
            status=ApplicationStatus.PENDING,
            application_date=datetime(2025, 9, 5),
        )
        db.add_all([app1, app2])
        db.flush()

        # ─────────────────────────────────────────────
        # CONSENT (Arjun grants lender access)
        # ─────────────────────────────────────────────
        consent = Consent(
            farmer_id=arjun.id, lender_id=lender.id,
            data_fields_granted=["trust_passport", "production_records", "sales_records", "fpo_verification"],
            purpose="Credit assessment for Rabi 2025 crop loan",
            granted_at=datetime(2025, 9, 2),
            expires_at=datetime(2025, 12, 31),
            is_active=True,
            request_message="We are assessing your loan application. Please grant access to your farm records.",
        )
        db.add(consent)
        db.flush()

        # Data access log
        log = DataAccessLog(
            farmer_id=arjun.id, consent_id=consent.id,
            accessor_user_id=lender_user.id,
            accessor_role="lender",
            accessor_name="MP Gramin Bank",
            fields_accessed=["trust_passport", "production_records"],
            purpose="Initial credit assessment review",
            accessed_at=datetime(2025, 9, 3),
            previous_hash="GENESIS",
            current_hash="demo_hash_001",
        )
        db.add(log)

        db.commit()

        # Generate Trust Passport for Arjun via the engine
        from backend.services.passport_engine import generate_trust_passport
        db.refresh(arjun)
        passport = generate_trust_passport(arjun, db)
        print(f"✓ Trust Passport generated for Arjun Patel: score={passport.overall_creditworthiness}")

        db.commit()
        print("\n✓ Demo data seeded successfully!")
        print("─" * 50)
        print("Demo credentials (password: Demo@1234 for all):")
        print("  Farmer : farmer@kisansetu.demo")
        print("  FPO    : fpo@kisansetu.demo")
        print("  Lender : lender@kisansetu.demo")
        print("  Admin  : admin@kisansetu.demo")
        print("─" * 50)

    except Exception as e:
        db.rollback()
        print(f"✗ Seed failed: {e}")
        import traceback; traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    seed()
