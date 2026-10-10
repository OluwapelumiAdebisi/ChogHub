from fastapi import Depends, Header, HTTPException

from .config import Settings, get_settings
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


def is_admin(s: Settings, wallet: str | None) -> bool:
    """ADMIN_WALLETS decides, every request. Remove a wallet there and it loses access at once."""
    return bool(wallet) and wallet.lower() in s.admin_set


def admin_wallet(wallet: str = Depends(current_wallet), s: Settings = Depends(get_settings)) -> str:
    if not is_admin(s, wallet):
        raise HTTPException(403, "Admins only")
    return wallet
