"""Sign-In With Ethereum (EIP-4361), verified without extra dependencies.

The frontend builds the standard SIWE message (e.g. with the `siwe` npm package),
the user signs it, and we check: signature recovers to the stated address,
domain and chain match, nonce was issued by us and not used, message not expired.
"""
from __future__ import annotations

import re
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from eth_account import Account
from eth_account.messages import encode_defunct
from sqlalchemy.orm import Session

from ..config import Settings
from ..models import AuthNonce, User

NONCE_TTL = timedelta(minutes=10)


class AuthError(Exception):
    pass


def issue_nonce(db: Session) -> str:
    nonce = secrets.token_hex(12)
    db.add(AuthNonce(nonce=nonce))
    db.commit()
    return nonce


def parse_siwe(message: str) -> dict:
    lines = message.split("\n")
    m = re.match(r"^(?P<domain>\S+) wants you to sign in with your Ethereum account:$", lines[0])
    if not m or len(lines) < 2:
        raise AuthError("Not a SIWE message")
    fields = {"domain": m["domain"], "address": lines[1].strip()}
    for line in lines[2:]:
        k, sep, v = line.partition(": ")
        if sep:
            fields[k.strip()] = v.strip()
    return fields


def verify_siwe(db: Session, s: Settings, message: str, signature: str) -> str:
    f = parse_siwe(message)
    if f["domain"] != s.siwe_domain:
        raise AuthError("Wrong domain")
    if int(f.get("Chain ID", -1)) != s.chain_id:
        raise AuthError("Wrong chain")
    exp = f.get("Expiration Time")
    if exp and datetime.fromisoformat(exp.replace("Z", "+00:00")) < datetime.now(timezone.utc):
        raise AuthError("Message expired")

    row = db.get(AuthNonce, f.get("Nonce", ""))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not row or row.used or now - row.created_at > NONCE_TTL:
        raise AuthError("Invalid or expired nonce")

    try:
        recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
    except Exception as e:  # malformed signature
        raise AuthError("Bad signature") from e
    if recovered.lower() != f["address"].lower():
        raise AuthError("Signature does not match address")

    row.used = True
    wallet = recovered.lower()
    if not db.get(User, wallet):
        db.add(User(wallet=wallet, is_admin=wallet in s.admin_set))
    db.commit()
    return wallet


def make_token(s: Settings, wallet: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=s.jwt_ttl_hours)
    return jwt.encode({"sub": wallet, "exp": exp}, s.jwt_secret, algorithm="HS256")


def read_token(s: Settings, token: str) -> str:
    try:
        return jwt.decode(token, s.jwt_secret, algorithms=["HS256"])["sub"]
    except jwt.PyJWTError as e:
        raise AuthError("Invalid session") from e
