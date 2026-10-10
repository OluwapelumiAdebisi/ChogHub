from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..deps import current_wallet, is_admin
from ..schemas import VerifyIn
from ..services.auth import AuthError, issue_nonce, make_token, verify_siwe

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/nonce")
def nonce(db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    return {"nonce": issue_nonce(db), "domain": s.siwe_domain, "chain_id": s.chain_id}


@router.post("/verify")
def verify(body: VerifyIn, db: Session = Depends(get_db), s: Settings = Depends(get_settings)):
    try:
        wallet = verify_siwe(db, s, body.message, body.signature)
    except AuthError as e:
        raise HTTPException(401, str(e)) from e
    return {"token": make_token(s, wallet), "wallet": wallet, "is_admin": is_admin(s, wallet)}


@router.get("/me")
def me(wallet: str = Depends(current_wallet), s: Settings = Depends(get_settings)):
    """Who the session belongs to, and whether they're an admin right now."""
    return {"wallet": wallet, "is_admin": is_admin(s, wallet)}
