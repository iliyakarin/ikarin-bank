import sys
from database import SessionLocal, User, Account
from main import get_password_hash

db = SessionLocal()
email = "alice3@example.com"
if not db.query(User).filter_by(email=email).first():
    user = User(
        first_name="Alice",
        last_name="Test",
        email=email,
        password_hash=get_password_hash("[REDACTED]")
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    account = Account(
        user_id=user.id,
        balance=1000.00,
        reserved_balance=0.00
    )
    db.add(account)
    db.commit()
    print("User created")
else:
    print("User exists")
db.close()
