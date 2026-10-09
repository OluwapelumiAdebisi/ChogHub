"""Everything that touches Monad.

Two implementations share one interface:
- Web3Chain: real RPC calls (testnet demo or mainnet).
- FakeChain: in-memory chain for local dev without RPC, and for tests.

The backend never sends a user's transaction. It only builds unsigned calldata
for the wallet to sign, and verifies the receipt afterwards. The single key it
holds is the attester key that writes reputation to ChogRegistry.
"""
from __future__ import annotations

import json
import secrets
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from ..config import Settings, get_settings

ABI_DIR = Path(__file__).resolve().parent.parent / "abi"
WEI = 10**18
KIND_INDEX = {"quest": 0, "win": 1, "contribution": 2}


def _abi(name: str) -> list:
    return json.loads((ABI_DIR / f"{name}.json").read_text())


def slug_to_bytes32(slug: str) -> bytes:
    from eth_utils import keccak

    return keccak(text=slug)


def int_to_bytes32(n: int) -> bytes:
    return n.to_bytes(32, "big")


@dataclass
class BuyResult:
    wallet: str
    mon_in_wei: int
    chog_out_wei: int


class ChainService(Protocol):
    collection: str
    chain_id: int

    def owner_of(self, token_id: int) -> str | None: ...
    def tokens_of_owner(self, wallet: str) -> list[int]: ...
    def traits_of(self, token_id: int) -> dict: ...
    def image_of(self, token_id: int) -> str | None: ...
    def balances(self, wallet: str) -> dict: ...
    def quote_mon_for_chog(self, chog_wei: int) -> int: ...
    def build_buy_tx(self, wallet: str, chog_wei: int, min_out_wei: int, value_wei: int) -> dict: ...
    def verify_buy(self, tx_hash: str, wallet: str) -> BuyResult | None: ...
    def record_achievement(self, token_id: int, slug: str, kind: str, ref: int) -> str | None: ...
    def record_event(self, token_id: int, slug: str, ref: int) -> str | None: ...
    def registry_stats(self, token_id: int) -> dict: ...


# --------------------------------------------------------------------------- fake


@dataclass
class FakeChain:
    """Deterministic in-memory chain. Mirrors the contracts' rules closely enough
    for tests: ownership, traits, a fixed-rate vendor and a duplicate-guarded registry."""

    collection: str = "0x0000000000000000000000000000000000000001"
    chain_id: int = 10143
    chog_per_mon: int = 1_000
    owners: dict[int, str] = field(default_factory=dict)
    traits: dict[int, dict] = field(default_factory=dict)
    mon: dict[str, int] = field(default_factory=dict)
    chog: dict[str, int] = field(default_factory=dict)
    sent: dict[str, BuyResult] = field(default_factory=dict)
    achievements: dict[int, set[str]] = field(default_factory=dict)
    events: dict[int, set[str]] = field(default_factory=dict)
    stats: dict[int, dict] = field(default_factory=dict)

    # --- test helpers
    def mint(self, wallet: str, token_id: int, traits: dict | None = None) -> None:
        self.owners[token_id] = wallet.lower()
        self.traits[token_id] = traits or {"hat": "Pirate Hat", "mood": "Chaotic", "background": "Purple"}

    def transfer(self, token_id: int, to: str) -> None:
        self.owners[token_id] = to.lower()

    def fund(self, wallet: str, mon: float) -> None:
        self.mon[wallet.lower()] = int(mon * WEI)

    def simulate_send(self, tx: dict, sender: str) -> str:
        """Pretend the wallet signed and sent `tx`; returns a tx hash."""
        sender = sender.lower()
        value = int(tx["value"])
        out = value * self.chog_per_mon
        self.mon[sender] = self.mon.get(sender, 0) - value
        self.chog[sender] = self.chog.get(sender, 0) + out
        h = "0x" + secrets.token_hex(32)
        self.sent[h] = BuyResult(sender, value, out)
        return h

    # --- interface
    def owner_of(self, token_id: int) -> str | None:
        return self.owners.get(token_id)

    def tokens_of_owner(self, wallet: str) -> list[int]:
        return sorted(t for t, o in self.owners.items() if o == wallet.lower())

    def traits_of(self, token_id: int) -> dict:
        return self.traits.get(token_id, {})

    def image_of(self, token_id: int) -> str | None:
        return None

    def balances(self, wallet: str) -> dict:
        w = wallet.lower()
        return {"mon_wei": self.mon.get(w, 0), "chog_wei": self.chog.get(w, 0)}

    def quote_mon_for_chog(self, chog_wei: int) -> int:
        return -(-chog_wei // self.chog_per_mon)  # ceil

    def build_buy_tx(self, wallet: str, chog_wei: int, min_out_wei: int, value_wei: int) -> dict:
        return {"to": "0x0000000000000000000000000000000000000003", "data": "0x", "value": str(value_wei), "chainId": self.chain_id}

    def verify_buy(self, tx_hash: str, wallet: str) -> BuyResult | None:
        r = self.sent.get(tx_hash)
        return r if r and r.wallet == wallet.lower() else None

    def record_achievement(self, token_id: int, slug: str, kind: str, ref: int) -> str | None:
        got = self.achievements.setdefault(token_id, set())
        if slug in got:
            return None
        got.add(slug)
        s = self.stats.setdefault(token_id, {"quests": 0, "events": 0, "wins": 0, "contributions": 0})
        s[{"quest": "quests", "win": "wins", "contribution": "contributions"}[kind]] += 1
        return "0x" + secrets.token_hex(32)

    def record_event(self, token_id: int, slug: str, ref: int) -> str | None:
        got = self.events.setdefault(token_id, set())
        if slug in got:
            return None
        got.add(slug)
        s = self.stats.setdefault(token_id, {"quests": 0, "events": 0, "wins": 0, "contributions": 0})
        s["events"] += 1
        return "0x" + secrets.token_hex(32)

    def registry_stats(self, token_id: int) -> dict:
        return self.stats.get(token_id, {"quests": 0, "events": 0, "wins": 0, "contributions": 0})


# --------------------------------------------------------------------------- web3


class Web3Chain:
    def __init__(self, s: Settings):
        from web3 import Web3

        self.w3 = Web3(Web3.HTTPProvider(s.effective_rpc_url, request_kwargs={"timeout": 20}))
        self.chain_id = s.chain_id
        cs = Web3.to_checksum_address
        self.collection = cs(s.chog_nft_address)
        self.nft = self.w3.eth.contract(address=self.collection, abi=_abi("MockChog"))
        self.token = self.w3.eth.contract(address=cs(s.chog_token_address), abi=_abi("MockChogToken"))
        self.vendor = self.w3.eth.contract(address=cs(s.chog_vendor_address), abi=_abi("ChogVendor"))
        self.registry = self.w3.eth.contract(address=cs(s.chog_registry_address), abi=_abi("ChogRegistry"))
        self.attester = None
        if s.attester_private_key:
            self.attester = self.w3.eth.account.from_key(s.attester_private_key)
        self._cs = cs

    # --- reads
    def owner_of(self, token_id: int) -> str | None:
        try:
            return self.nft.functions.ownerOf(token_id).call().lower()
        except Exception:
            return None

    def tokens_of_owner(self, wallet: str) -> list[int]:
        w = self._cs(wallet)
        try:
            n = self.nft.functions.balanceOf(w).call()
            return [self.nft.functions.tokenOfOwnerByIndex(w, i).call() for i in range(min(n, 50))]
        except Exception:
            # Collection is not ERC721Enumerable (e.g. the official mainnet Chog):
            # the frontend passes token IDs explicitly and we verify with ownerOf.
            return []

    def traits_of(self, token_id: int) -> dict:
        try:
            hat, mood, bg = self.nft.functions.traitsOf(token_id).call()
            return {"hat": hat, "mood": mood, "background": bg}
        except Exception:
            meta = self._metadata(token_id) or {}
            return {a.get("trait_type", "").lower(): a.get("value") for a in meta.get("attributes", [])}

    def image_of(self, token_id: int) -> str | None:
        meta = self._metadata(token_id) or {}
        return meta.get("image")

    def _metadata(self, token_id: int) -> dict | None:
        import base64

        try:
            uri = self.nft.functions.tokenURI(token_id).call()
        except Exception:
            return None
        prefix = "data:application/json;base64,"
        if uri.startswith(prefix):
            return json.loads(base64.b64decode(uri[len(prefix):]))
        if uri.startswith("ipfs://"):
            uri = "https://ipfs.io/ipfs/" + uri[len("ipfs://"):]
        try:
            import httpx

            return httpx.get(uri, timeout=8).json()
        except Exception:
            return None

    def balances(self, wallet: str) -> dict:
        w = self._cs(wallet)
        return {
            "mon_wei": self.w3.eth.get_balance(w),
            "chog_wei": self.token.functions.balanceOf(w).call(),
        }

    def quote_mon_for_chog(self, chog_wei: int) -> int:
        return self.vendor.functions.quote(chog_wei).call()

    # --- user transaction (unsigned)
    def build_buy_tx(self, wallet: str, chog_wei: int, min_out_wei: int, value_wei: int) -> dict:
        data = self.vendor.encode_abi("buy", args=[min_out_wei])
        return {"to": self.vendor.address, "data": data, "value": str(value_wei), "chainId": self.chain_id}

    def verify_buy(self, tx_hash: str, wallet: str) -> BuyResult | None:
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
        if receipt.status != 1 or receipt.to is None or receipt.to.lower() != self.vendor.address.lower():
            return None
        if receipt["from"].lower() != wallet.lower():
            return None
        from web3.logs import DISCARD

        for log in self.vendor.events.Bought().process_receipt(receipt, errors=DISCARD):
            return BuyResult(log.args.buyer.lower(), log.args.monIn, log.args.chogOut)
        return None

    # --- attester writes
    def _send(self, fn) -> str | None:
        if not self.attester:
            return None  # no key configured: off-chain only
        tx = fn.build_transaction(
            {
                "from": self.attester.address,
                "nonce": self.w3.eth.get_transaction_count(self.attester.address, "pending"),
                "chainId": self.chain_id,
            }
        )
        signed = self.attester.sign_transaction(tx)
        h = self.w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = self.w3.eth.wait_for_transaction_receipt(h, timeout=60)
        return receipt.transactionHash.to_0x_hex() if receipt.status == 1 else None

    def record_achievement(self, token_id: int, slug: str, kind: str, ref: int) -> str | None:
        k = self.registry.functions.key(self.collection, token_id).call()
        if self.registry.functions.hasAchievement(k, slug_to_bytes32(slug)).call():
            return None
        fn = self.registry.functions.recordAchievement(
            self.collection, token_id, slug_to_bytes32(slug), KIND_INDEX[kind], int_to_bytes32(ref)
        )
        return self._send(fn)

    def record_event(self, token_id: int, slug: str, ref: int) -> str | None:
        k = self.registry.functions.key(self.collection, token_id).call()
        if self.registry.functions.attendedEvent(k, slug_to_bytes32(slug)).call():
            return None
        fn = self.registry.functions.recordEvent(self.collection, token_id, slug_to_bytes32(slug), int_to_bytes32(ref))
        return self._send(fn)

    def registry_stats(self, token_id: int) -> dict:
        q, e, w, c = self.registry.functions.statsOf(self.collection, token_id).call()
        return {"quests": q, "events": e, "wins": w, "contributions": c}


# --------------------------------------------------------------------------- factory

_fake_singleton: FakeChain | None = None


def get_fake_chain() -> FakeChain:
    global _fake_singleton
    if _fake_singleton is None:
        _fake_singleton = FakeChain()
    return _fake_singleton


@lru_cache
def _web3_chain() -> Web3Chain:
    return Web3Chain(get_settings())


def get_chain() -> ChainService:
    return get_fake_chain() if get_settings().chain_mode == "fake" else _web3_chain()
