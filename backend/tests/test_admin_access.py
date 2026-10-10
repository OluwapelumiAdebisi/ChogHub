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
