# ChogHub

**We didn't give an NFT utility. We gave the NFT a job.**

ChogHub is one place to own, use and interact with your Chog on Monad. Connect your wallet and your Chog wakes up as an AI agent: it finds events, runs quests and prepares on-chain actions for you to sign. Every quest, event and achievement is recorded on-chain against the NFT's token ID, so when a Chog is sold its reputation goes with it while the old owner's private chats stay behind.

```
choghub/
├── contracts/   Foundry: MockChog (ERC-721), MockChogToken (ERC-20), ChogVendor, ChogRegistry
├── backend/     FastAPI: SIWE auth, events, quests, agent with tools, chain service
└── web/         Next.js 14 + wagmi + RainbowKit + Tailwind
```

## How it fits together

- **The NFT is the account.** Sign-In With Ethereum proves the wallet; every write re-checks `ownerOf` for the chosen Chog.
- **ChogRegistry** stores reputation keyed by `(collection, tokenId)`, written only by the backend's attester key. It works with any ERC-721, including the official Chog collection on mainnet.
- **The agent can only prepare transactions.** "Buy me 10 CHOG" returns a confirm card; the owner signs in their own wallet; the backend verifies the receipt and the `Bought` event before reporting success. A per-action spend cap and slippage floor apply.
- **Memory has two layers.** Public history follows the token. Private memory is keyed by `(Chog, owner)`, so a new owner starts fresh but is greeted with the Chog's past.

## Run it locally in 2 minutes (no chain needed)

The backend has an in-memory chain (`CHAIN_MODE=fake`) so you can build UI without RPC or test MON.

```bash
# API
cd backend
pip install -r requirements.txt
cp .env.example .env            # set ADMIN_WALLETS to your wallet address
uvicorn app.main:app --reload --port 8000

# Web (new terminal)
cd web
npm install
cp .env.example .env.local
npm run dev                     # http://localhost:3000
```

Connect a wallet, sign in, click **Mint a test Chog**, and talk to it. In fake mode the confirm card is simulated by the backend instead of your wallet.

## Run against Monad testnet

1. Install Foundry and get testnet MON from the faucet at https://testnet.monad.xyz.
2. Create two keys: a deployer, and an attester for the backend (send it ~0.5 MON).
3. Deploy:
   ```bash
   cd contracts
   forge install foundry-rs/forge-std OpenZeppelin/openzeppelin-contracts@v5.1.0 --no-git
   forge test
   ATTESTER_ADDRESS=0xYourAttester forge script script/Deploy.s.sol \
     --rpc-url monad_testnet --broadcast --private-key $DEPLOYER_KEY
   ```
4. Copy the four printed addresses into `backend/.env`, set `CHAIN_MODE=web3` and `ATTESTER_PRIVATE_KEY`, then restart the API.
5. In the app, **Mint a test Chog** sends a real `mint()` from your wallet.

To try it fully locally instead, run `anvil --chain-id 10143`, deploy with `--rpc-url http://127.0.0.1:8545`, set `RPC_URL=http://127.0.0.1:8545` in the backend and `NEXT_PUBLIC_NETWORK=local` in the web app.

## Deploying (testnet demo)

**Backend on Railway**
1. New project → Deploy from GitHub repo → this repo. In the service settings set **Root Directory** to `backend`. Railway reads `backend/railway.json` for the start command and health check.
2. Add a **PostgreSQL** database to the project, then on the backend service add the variable `DATABASE_URL` = `${{Postgres.DATABASE_URL}}`.
3. Add the rest of the variables from `backend/.env.example`: `NETWORK=testnet`, `CHAIN_MODE=web3`, the four contract addresses, `ATTESTER_PRIVATE_KEY`, a long random `JWT_SECRET`, `ADMIN_WALLETS`, and optionally `ANTHROPIC_API_KEY`.
4. Settings → Networking → **Generate Domain**. Check `https://<that domain>/health`.

**Website on Vercel**
1. Add New → Project → import this repo, set **Root Directory** to `web`.
2. Environment variables: `NEXT_PUBLIC_API_URL` = the Railway URL, `NEXT_PUBLIC_NETWORK=testnet`, and optionally `NEXT_PUBLIC_WALLETCONNECT_PROJECT_ID`.
3. Deploy, then go back to Railway and set `SIWE_DOMAIN` to the Vercel host (e.g. `choghub.vercel.app`, no `https://`) and `CORS_ORIGINS` to the full Vercel URL (`https://choghub.vercel.app`).

Demo events and quests load on first boot (`SEED_DEMO=true`).

## Switching to mainnet

Set `NETWORK=mainnet`, point `CHOG_NFT_ADDRESS` at the official Chog collection and `CHOG_TOKEN_ADDRESS` at CHOG (`0x350035555E10d9AfAF1566AaebfCeD5BA6C27777`), and deploy only the registry with `REGISTRY_ONLY=true`. Buying on mainnet needs a DEX adapter in `services/chain.py` (`build_buy_tx` / `verify_buy`); the vendor is testnet-only.

## The agent

With `ANTHROPIC_API_KEY` set, the agent is Claude with eight tools (`get_ecosystem_today`, `list_events`, `list_quests`, `get_chog_profile`, `get_balances`, `join_event`, `start_quest`, `prepare_buy_chog`). Without a key, or if the API fails mid-demo, a rules-based fallback answers the demo questions from the same tools.

## Tests

```bash
cd contracts && forge test                 # 6 tests: mint limits, vendor, registry, history follows the token
cd backend && python -m pytest -q          # full demo flow + guards against the in-memory chain
cd backend && PYTHONPATH=. python scripts/web3_smoke.py <user_key>   # real chain path (Anvil or testnet)
```

## Demo script (2 minutes)

1. Connect and sign in: Chog #742 appears with its traits.
2. "What's happening in the Chog ecosystem today?"
3. Join Chog Meme Wars (holder check passes).
4. Submit the meme quest; approve it from `/admin`; the sticker slaps onto the passport.
5. "Buy me 10 CHOG" → confirm card → sign → "Received 10 CHOG".
6. Transfer the Chog to a second wallet: the new owner is greeted with its history.
7. Close: "We didn't give an NFT utility. We gave the NFT a job."
