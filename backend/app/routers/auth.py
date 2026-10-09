from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..db import get_db
from ..models import User
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
    user = db.get(User, wallet)
    return {"token": make_token(s, wallet), "wallet": wallet,
            "is_admin": wallet in s.admin_set or bool(user and user.is_admin)}
