"""Load the demo events and quests by hand: python seed.py"""
from app.db import SessionLocal, init_db
from app.seed_data import seed

if __name__ == "__main__":
    init_db()
    with SessionLocal() as db:
        seed(db)
    print("Seeded demo events, quests and achievements.")
