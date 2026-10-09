from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from .config import Settings, get_settings
from .db import get_db
from .models import User
from .services.auth import AuthError, read_token
from .services.chain import ChainService, get_chain


def chain_dep() -> ChainService:
    return get_chain()


def _bearer(authorization: str | None) -> str | None:
    if authorization and authorization.lower().startswith("bearer "):
        return authorization[7:]
    return None


def current_wallet(authorization: str | None = Header(default=None), s: Settings = Depends(get_settings)) -> str:
    token = _bearer(authorization)
    if not token:
        raise HTTPException(401, "Sign in with your wallet first")
    try:
        return read_token(s, token)
    except AuthError as e:
        raise HTTPException(401, str(e)) from e


def optional_wallet(authorization: str | None = Header(default=None), s: Settings = Depends(get_settings)) -> str | None:
    token = _bearer(authorization)
    if not token:
        return None
    try:
        return read_token(s, token)
    except AuthError:
        return None


def admin_wallet(wallet: str = Depends(current_wallet), db: Session = Depends(get_db),
                 s: Settings = Depends(get_settings)) -> str:
    user = db.get(User, wallet)
    if wallet not in s.admin_set and not (user and user.is_admin):
        raise HTTPException(403, "Admins only")
    return wallet
