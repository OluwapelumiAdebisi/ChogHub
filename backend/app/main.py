from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .config import get_settings
from .db import init_db
from .deps import chain_dep
from .routers import admin, auth, hub

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="ChogHub API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth.router)
app.include_router(hub.router)
app.include_router(admin.router)


@app.get("/health")
def health():
    return {"ok": True, "network": settings.network, "chain_mode": settings.chain_mode}


# ---- dev-only helpers for the in-memory chain (CHAIN_MODE=fake) ----

class DevMintIn(BaseModel):
    wallet: str
    token_id: int
    hat: str = "Pirate Hat"


class DevSendIn(BaseModel):
    wallet: str
    tx: dict


if settings.chain_mode == "fake":

    @app.post("/dev/mint", tags=["dev"])
    def dev_mint(body: DevMintIn, chain=Depends(chain_dep)):
        chain.mint(body.wallet, body.token_id, {"hat": body.hat, "mood": "Chaotic", "background": "Purple"})
        chain.fund(body.wallet, 50)
        return {"ok": True}

    @app.post("/dev/send", tags=["dev"])
    def dev_send(body: DevSendIn, chain=Depends(chain_dep)):
        """Stands in for the wallet signing and sending an unsigned tx."""
        if not body.tx.get("value"):
            raise HTTPException(400, "Missing value")
        return {"tx_hash": chain.simulate_send(body.tx, body.wallet)}
