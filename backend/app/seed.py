"""Create demo FPO and Bank accounts so every role can be exercised."""

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User, Role


def seed() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        demo_accounts = [
            ("fpo_krishak", "Krishak Vahini FPO", Role.FPO),
            ("bank_gramin", "Gramin Vikas Bank", Role.BANK),
        ]
        for username, name, role in demo_accounts:
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                print(f"Already exists: {username}")
                continue
            db.add(
                User(
                    username=username,
                    password_hash=hash_password("demo@1234"),
                    role=role.value,
                    name=name,
                )
            )
            print(f"Created {role.value}: {username} / demo@1234")
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed()