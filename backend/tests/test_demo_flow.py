"""Runs the whole demo script against the in-memory chain:
sign in -> greeting -> today -> join event -> meme quest + admin approval ->
agent prepares a buy -> wallet sends -> confirm -> sell the Chog -> new owner inherits history."""
import os
from datetime import datetime, timedelta, timezone

os.environ.update(CHAIN_MODE="fake", DATABASE_URL="sqlite:///./test_choghub.db", ANTHROPIC_API_KEY="",
                  SIWE_DOMAIN="localhost:3000", NETWORK="testnet")

import pytest  # noqa: E402
from eth_account import Account  # noqa: E402
from eth_account.messages import encode_defunct  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import get_settings  # noqa: E402

ALICE = Account.create()
BOB = Account.create()
ADMIN = Account.create()


@pytest.fixture(scope="module")
def client():
    if os.path.exists("test_choghub.db"):
        os.remove("test_choghub.db")
    get_settings.cache_clear()
    os.environ["ADMIN_WALLETS"] = ADMIN.address.lower()
    get_settings.cache_clear()
    from app import main
    from app.db import SessionLocal, init_db
    from app.seed_data import seed

    init_db()
    with SessionLocal() as db:
        seed(db)
    with TestClient(main.app) as c:
        yield c
    os.remove("test_choghub.db")


def siwe_login(c: TestClient, acct) -> dict:
    nonce = c.get("/auth/nonce").json()["nonce"]
    issued = datetime.now(timezone.utc)
    msg = (
        "localhost:3000 wants you to sign in with your Ethereum account:\n"
        f"{acct.address}\n\nSign in to ChogHub\n\n"
        "URI: http://localhost:3000\nVersion: 1\nChain ID: 10143\n"
        f"Nonce: {nonce}\nIssued At: {issued.isoformat().replace('+00:00', 'Z')}\n"
        f"Expiration Time: {(issued + timedelta(minutes=5)).isoformat().replace('+00:00', 'Z')}"
    )
    sig = Account.sign_message(encode_defunct(text=msg), acct.key).signature.to_0x_hex()
    r = c.post("/auth/verify", json={"message": msg, "signature": sig})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def chat(c, h, token_id, text):
    r = c.post("/agent/chat", headers=h, json={"token_id": token_id, "messages": [{"role": "user", "content": text}]})
    assert r.status_code == 200, r.text
    return r.json()


def test_full_demo(client):
    c = client
    alice = ALICE.address.lower()
    c.post("/dev/mint", json={"wallet": alice, "token_id": 742, "hat": "Pirate Hat"})

    # Scene 1 — meet your Chog
    h = siwe_login(c, ALICE)
    chogs = c.get("/me/chogs", headers=h).json()["chogs"]
    assert [x["token_id"] for x in chogs] == [742]
    g = c.get("/agent/greeting", params={"token_id": 742}, headers=h).json()
    assert "Chog #742" in g["message"] and not g["inherited_history"]

    # Scene 2 — what's happening today
    out = chat(c, h, 742, "What's happening in the Chog ecosystem today?")
    assert "Chog Meme Wars" in out["reply"]

    # Scene 3 — join an event (holder-gated)
    events = c.get("/events").json()["events"]
    meme_wars = next(e for e in events if e["slug"] == "chog-meme-wars")
    call = next(e for e in events if e["slug"] == "community-call")
    assert c.post(f"/events/{meme_wars['id']}/join", headers=h, json={"token_id": 742}).json()["joined"]
    # joining the call through the agent auto-completes the "join the call" quest
    out = chat(c, h, 742, f"Register me for event {call['id']}")
    assert "You're in" in out["reply"]

    # Scene 4 — meme quest, then admin approval writes the achievement on-chain
    quests = {q["slug"]: q for q in c.get("/quests", params={"token_id": 742}).json()["quests"]}
    assert quests["join-the-call"]["status"] == "approved"
    r = c.post(f"/quests/{quests['meme-quest']['id']}/submit", headers=h,
               json={"token_id": 742, "proof_url": "https://x.com/alice/status/1"})
    assert r.json()["status"] == "submitted"
    ha = siwe_login(c, ADMIN)
    subs = c.get("/admin/submissions", headers=ha).json()["submissions"]
    r = c.post(f"/admin/submissions/{subs[0]['id']}/review", headers=ha, json={"approve": True})
    assert r.json()["status"] == "approved" and r.json()["onchain_tx"]

    # Scene 5 — agent prepares a buy; the wallet (simulated) signs; backend verifies
    out = chat(c, h, 742, "Buy me 10 CHOG")
    assert len(out["actions"]) == 1
    card = out["actions"][0]
    assert card["params"]["chog_amount"] == 10 and card["params"]["mon_cost"] == pytest.approx(0.01)
    tx_hash = c.post("/dev/send", json={"wallet": alice, "tx": card["tx"]}).json()["tx_hash"]
    done = c.post(f"/actions/{card['id']}/confirm", headers=h, json={"tx_hash": tx_hash}).json()
    assert done["status"] == "confirmed" and done["result"]["chog_received"] == 10

    # Scene 6 — profile shows the day's work
    p = c.get("/chogs/742").json()
    assert p["stats"]["events_attended"] == 2
    assert p["stats"]["quests_completed"] == 3  # call (auto), meme (approved), first buy (auto)
    assert p["stats"]["onchain"]["quests"] == 3 and p["stats"]["onchain"]["events"] == 2
    assert chat(c, h, 742, "How much CHOG do I own?")["reply"].endswith("10 CHOG.")

    # The twist — sell the Chog; the new owner inherits public history, not private memory
    from app.services.chain import get_fake_chain

    get_fake_chain().transfer(742, BOB.address)
    assert c.post("/agent/chat", headers=h, json={"token_id": 742, "messages": [
        {"role": "user", "content": "hi"}]}).status_code == 403  # Alice lost control
    hb = siwe_login(c, BOB)
    g = c.get("/agent/greeting", params={"token_id": 742}, headers=hb).json()
    assert g["inherited_history"] and "previous owner" in g["message"]
    assert c.get("/chogs/742").json()["owner_count"] == 2


def test_guards(client):
    c = client
    carol = Account.create()
    h = siwe_login(c, carol)
    # no Chog -> can't join holder events or chat
    ev = c.get("/events").json()["events"][0]
    assert c.post(f"/events/{ev['id']}/join", headers=h, json={"token_id": 742}).status_code == 403
    # trait-gated quest
    c.post("/dev/mint", json={"wallet": carol.address, "token_id": 9, "hat": "Crown"})
    pirate = next(q for q in c.get("/quests").json()["quests"] if q["slug"] == "pirate-hunt")
    r = c.post(f"/quests/{pirate['id']}/submit", headers=h, json={"token_id": 9, "proof_text": "ahoy"})
    assert r.status_code == 403 and "Pirate Hat" in r.json()["detail"]
    # spend cap
    out = chat(c, h, 9, "buy 1000000 chog")
    assert out["actions"] == [] and "limit" in out["reply"]
    # replayed SIWE nonce / bad auth
    assert c.get("/me/chogs").status_code == 401
    # non-admin can't review
    assert c.get("/admin/submissions", headers=h).status_code == 403
