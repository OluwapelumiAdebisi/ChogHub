"""Smoke-test Web3Chain against a running node with the contracts deployed.
Usage: CHAIN_MODE=web3 RPC_URL=... CHOG_*_ADDRESS=... ATTESTER_PRIVATE_KEY=... python scripts/web3_smoke.py <user_private_key>"""
import sys

from app.config import get_settings
from app.services.chain import WEI, Web3Chain

s = get_settings()
chain = Web3Chain(s)
user = chain.w3.eth.account.from_key(sys.argv[1])
w = user.address.lower()

ids = chain.tokens_of_owner(w)
print("tokens_of_owner:", ids)
tid = ids[0]
print("owner_of:", chain.owner_of(tid) == w, "traits:", chain.traits_of(tid))
print("image is data URI:", (chain.image_of(tid) or "")[:26])

want = 10 * WEI
cost = chain.quote_mon_for_chog(want)
tx = chain.build_buy_tx(w, want, want * 99 // 100, cost)
print("quote MON:", cost / WEI)
full = {"to": tx["to"], "data": tx["data"], "value": int(tx["value"]), "chainId": tx["chainId"],
        "from": user.address, "nonce": chain.w3.eth.get_transaction_count(user.address),
        "gas": 200_000, "gasPrice": chain.w3.eth.gas_price}
h = chain.w3.eth.send_raw_transaction(user.sign_transaction(full).raw_transaction).to_0x_hex()
res = chain.verify_buy(h, w)
print("verify_buy:", res.chog_out_wei / WEI, "CHOG for", res.mon_in_wei / WEI, "MON")
print("verify_buy wrong wallet ->", chain.verify_buy(h, "0x000000000000000000000000000000000000dead"))
print("balances:", {k: v / WEI for k, v in chain.balances(w).items()})

print("record_achievement tx:", bool(chain.record_achievement(tid, "meme-warrior", "quest", 1)))
print("duplicate ->", chain.record_achievement(tid, "meme-warrior", "quest", 1))
print("record_event tx:", bool(chain.record_event(tid, "event:chog-meme-wars", 1)))
print("registry_stats:", chain.registry_stats(tid))
