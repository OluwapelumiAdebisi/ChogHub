"""Demo data: three events, four quests. Safe to re-run (skips existing slugs).
Runs automatically on startup when SEED_DEMO=true (the default).
"""
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Achievement, Event, Quest, utcnow


def seed(db: Session) -> None:
    now = utcnow().replace(minute=0, second=0, microsecond=0)

    events = [
        dict(slug="chog-meme-wars", title="Chog Meme Wars",
             description="Make the funniest Chog meme. Community votes, judges pick the winners.",
             starts_at=now + timedelta(hours=2), ends_at=now + timedelta(days=7), kind="online",
             visibility="holder", capacity=500, prize_text="50,000 CHOG prize pool"),
        dict(slug="community-call", title="Chog Community Call",
             description="Monthly call with the Chog team on X Spaces: roadmap, Q&A, shout-outs.",
             starts_at=now + timedelta(hours=20), ends_at=now + timedelta(hours=21), kind="spaces",
             visibility="public", link="https://x.com/"),
        dict(slug="weekly-holder-challenge", title="Weekly Holder Challenge",
             description="A new mini-challenge for holders every week. This week: show your Chog in the wild.",
             starts_at=now, ends_at=now + timedelta(days=6), kind="online", visibility="holder"),
    ]
    by_slug = {}
    for e in events:
        row = db.scalar(select(Event).where(Event.slug == e["slug"])) or Event(**e)
        db.add(row)
        by_slug[e["slug"]] = row
    db.flush()

    achievements = {
        "meme-warrior": ("Chog Meme Warrior", "Entered a meme in Chog Meme Wars", "frog", "quest"),
        "caller": ("On the Call", "Joined a Chog community call", "mic", "quest"),
        "first-chog": ("First CHOG", "Bought CHOG through your Chog agent", "coin", "quest"),
        "pirate-plunder": ("Pirate Plunder", "Completed the pirate-only treasure hunt", "anchor", "quest"),
    }
    ach = {}
    for slug, (name, desc, icon, kind) in achievements.items():
        row = db.scalar(select(Achievement).where(Achievement.slug == slug)) or Achievement(
            slug=slug, name=name, description=desc, icon=icon, kind=kind)
        db.add(row)
        ach[slug] = row
    db.flush()

    quests = [
        dict(slug="meme-quest", title="Create a Chog meme",
             description="Post a Chog meme on X and submit the link.", verify_type="manual",
             event_id=by_slug["chog-meme-wars"].id, achievement_id=ach["meme-warrior"].id),
        dict(slug="join-the-call", title="Join the community call",
             description="Register your Chog for the next community call.", verify_type="auto_event",
             event_id=by_slug["community-call"].id, achievement_id=ach["caller"].id),
        dict(slug="first-buy", title="Buy your first CHOG",
             description="Ask your Chog to buy any amount of CHOG and confirm it.", verify_type="auto_buy",
             achievement_id=ach["first-chog"].id),
        dict(slug="pirate-hunt", title="Pirate treasure hunt",
             description="Only Chogs with a Pirate Hat. Find the hidden word in the Chog Discord and submit it.",
             verify_type="manual", trait_requirement={"hat": "Pirate Hat"},
             achievement_id=ach["pirate-plunder"].id),
    ]
    for q in quests:
        if not db.scalar(select(Quest).where(Quest.slug == q["slug"])):
            db.add(Quest(**q))
    db.commit()
