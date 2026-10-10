"""Only wallets in ADMIN_WALLETS can use admin features, and removing one revokes access at once."""
import os

os.environ.setdefault("CHAIN_MODE", "fake")

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from eth_account import Account  # noqa: E402
from eth_account.messages import encode_defunct  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

ADMIN = Account.create()
HOLDER = Account.create()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path}/admin.db")
    monkeypatch.setenv("ADMIN_WALLETS", ADMIN.address)
    get_settings.cache_clear()
    from sqlalchemy.orm import sessionmaker

    from app import db as dbmod
    from app import main

    engine = dbmod.make_engine(f"sqlite:///{tmp_path}/admin.db")
    monkeypatch.setattr(dbmod, "engine", engine)
    monkeypatch.setattr(dbmod, "SessionLocal", sessionmaker(bind=engine, expire_on_commit=False))
    main.app.dependency_overrides[get_settings] = get_settings
    with TestClient(main.app) as c:
        yield c
    main.app.dependency_overrides.clear()
    get_settings.cache_clear()


def login(c, acct):
    s = c.get("/auth/nonce").json()
    now = datetime.now(timezone.utc)
    msg = (
        f"{s['domain']} wants you to sign in with your Ethereum account:\n{acct.address}\n\nSign in\n\n"
        f"URI: http://{s['domain']}\nVersion: 1\nChain ID: {s['chain_id']}\nNonce: {s['nonce']}\n"
        f"Issued At: {now.isoformat().replace('+00:00', 'Z')}\n"
        f"Expiration Time: {(now + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')}"
    )
    sig = Account.sign_message(encode_defunct(text=msg), acct.key).signature.to_0x_hex()
    r = c.post("/auth/verify", json={"message": msg, "signature": sig}).json()
    return r, {"Authorization": f"Bearer {r['token']}"}


def test_admin_and_holder(client, monkeypatch):
    r, h_admin = login(client, ADMIN)
    assert r["is_admin"] is True
    assert client.get("/auth/me", headers=h_admin).json()["is_admin"] is True
    assert client.get("/admin/submissions", headers=h_admin).status_code == 200

    r, h_holder = login(client, HOLDER)
    assert r["is_admin"] is False
    assert client.get("/auth/me", headers=h_holder).json()["is_admin"] is False
    assert client.get("/admin/submissions", headers=h_holder).status_code == 403
    ev = {"slug": "sneaky", "title": "Sneaky", "starts_at": "2026-12-01T10:00:00"}
    assert client.post("/admin/events", headers=h_holder, json=ev).status_code == 403


def test_removing_from_admin_wallets_revokes_access(client, monkeypatch):
    from app.config import get_settings

    _, h_admin = login(client, ADMIN)
    assert client.get("/admin/submissions", headers=h_admin).status_code == 200
    monkeypatch.setenv("ADMIN_WALLETS", "")
    get_settings.cache_clear()
    assert client.get("/auth/me", headers=h_admin).json()["is_admin"] is False
    assert client.get("/admin/submissions", headers=h_admin).status_code == 403


def test_admin_creates_quest_holders_complete_it(client):
    _, h_admin = login(client, ADMIN)
    _, h_holder = login(client, HOLDER)
    client.post("/dev/mint", json={"wallet": HOLDER.address, "token_id": 77, "hat": "Crown"})

    q = {"slug": "post-your-chog", "title": "Post your Chog", "description": "Share it on X.",
         "verify_type": "manual", "achievement_slug": "chog-influencer", "achievement_name": "Chog Influencer",
         "achievement_icon": "mic", "trait_requirement": {"hat": "Crown"}}
    # holders can't create quests
    assert client.post("/admin/quests", headers=h_holder, json=q).status_code == 403
    r = client.post("/admin/quests", headers=h_admin, json=q)
    assert r.status_code == 200, r.text
    qid = r.json()["id"]

    # it shows up for holders, they submit, admin approves, badge lands
    assert any(x["id"] == qid for x in client.get("/quests?token_id=77").json()["quests"])
    assert client.post(f"/quests/{qid}/submit", headers=h_holder,
                       json={"token_id": 77, "proof_url": "https://x.com/me/1"}).json()["status"] == "submitted"
    sub = client.get("/admin/submissions", headers=h_admin).json()["submissions"][0]
    assert client.post(f"/admin/submissions/{sub['id']}/review", headers=h_admin, json={"approve": True}).json()["status"] == "approved"
    assert "Chog Influencer" in [a["name"] for a in client.get("/chogs/77").json()["achievements"]]
    listed = {x["id"]: x for x in client.get("/admin/quests", headers=h_admin).json()["quests"]}
    assert listed[qid]["completed"] == 1

    # pausing hides it from holders; holders can't pause
    assert client.patch(f"/admin/quests/{qid}", headers=h_holder, json={"active": False}).status_code == 403
    assert client.patch(f"/admin/quests/{qid}", headers=h_admin, json={"active": False}).json()["active"] is False
    assert all(x["id"] != qid for x in client.get("/quests").json()["quests"])
    # the badge already earned stays
    assert "Chog Influencer" in [a["name"] for a in client.get("/chogs/77").json()["achievements"]]


@pytest.mark.parametrize("patch,expect", [
    ({"verify_type": "auto_event"}, "Pick the event"),
    ({"event_id": 999}, "doesn't exist"),
    ({"trait_requirement": {"hat": "Laser Eyes"}}, "Unknown trait"),
    ({"achievement_icon": "skull"}, ""),
    ({"slug": "meme-quest"}, "already exists"),
    ({"achievement_slug": "meme-warrior"}, "already belongs to another quest"),
])
def test_bad_quests_are_refused(client, patch, expect):
    from app import db as dbmod
    from app.seed_data import seed

    with dbmod.SessionLocal() as db:
        seed(db)
    _, h_admin = login(client, ADMIN)
    q = {"slug": "new-quest", "title": "New quest", "achievement_slug": "new-badge", "achievement_name": "New badge", **patch}
    r = client.post("/admin/quests", headers=h_admin, json=q)
    assert r.status_code in (409, 422), r.text
    assert expect in r.text


def _event(client, h_admin, slug, visibility, capacity=None):
    body = {"slug": slug, "title": slug.replace("-", " ").title(), "starts_at": "2027-01-01T10:00:00",
            "visibility": visibility, "capacity": capacity}
    r = client.post("/admin/events", headers=h_admin, json=body)
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_holder_events_need_a_chog_open_events_dont(client):
    _, h_admin = login(client, ADMIN)
    _, h_fan = login(client, HOLDER)  # signed in, but holds no Chog yet
    holders = _event(client, h_admin, "holders-party", "holder")
    open_ev = _event(client, h_admin, "open-mic", "public")

    # no Chog: refused from the holders-only event, welcome at the open one
    r = client.post(f"/events/{holders}/join", headers=h_fan, json={})
    assert r.status_code == 403 and "holders only" in r.json()["detail"]
    r = client.post(f"/events/{open_ev}/join", headers=h_fan, json={})
    assert r.status_code == 200 and r.json()["with_chog"] is False and r.json()["onchain_tx"] is None
    assert client.post(f"/events/{open_ev}/join", headers=h_fan, json={}).status_code == 200  # twice is fine
    ev = client.get(f"/events/{open_ev}", headers=h_fan).json()
    assert ev["joined"] is True and ev["participants"] == 1
    assert client.get(f"/events/{open_ev}").json()["joined"] is False  # anonymous viewer

    # claiming someone else's Chog doesn't work either
    client.post("/dev/mint", json={"wallet": ADMIN.address, "token_id": 5})
    r = client.post(f"/events/{holders}/join", headers=h_fan, json={"token_id": 5})
    assert r.status_code == 403 and "does not hold" in r.json()["detail"]

    # with their own Chog they get in, recorded on-chain against the token
    client.post("/dev/mint", json={"wallet": HOLDER.address, "token_id": 6})
    r = client.post(f"/events/{holders}/join", headers=h_fan, json={"token_id": 6})
    assert r.status_code == 200 and r.json()["with_chog"] is True and r.json()["onchain_tx"]
    assert client.get("/chogs/6").json()["stats"]["events_attended"] == 1


def test_capacity_counts_everyone(client):
    _, h_admin = login(client, ADMIN)
    _, h_fan = login(client, HOLDER)
    tiny = _event(client, h_admin, "tiny-meetup", "public", capacity=1)
    assert client.post(f"/events/{tiny}/join", headers=h_fan, json={}).status_code == 200
    client.post("/dev/mint", json={"wallet": ADMIN.address, "token_id": 8})
    r = client.post(f"/events/{tiny}/join", headers=h_admin, json={"token_id": 8})
    assert r.status_code == 409 and "full" in r.json()["detail"]
