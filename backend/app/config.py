"""Settings. One switch (NETWORK) flips between the testnet demo and mainnet."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

NETWORKS = {
    "testnet": {
        "chain_id": 10143,
        "rpc_url": "https://testnet-rpc.monad.xyz",
        "explorer": "https://testnet.monadvision.com",
    },
    "mainnet": {
        "chain_id": 143,
        "rpc_url": "https://rpc.monad.xyz",
        "explorer": "https://monadvision.com",
    },
}

# Official CHOG token on Monad mainnet.
MAINNET_CHOG_TOKEN = "0x350035555E10d9AfAF1566AaebfCeD5BA6C27777"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    network: str = "testnet"
    rpc_url: str | None = None  # override the public RPC

    # "web3" talks to the chain; "fake" is an in-memory chain for local dev and tests.
    chain_mode: str = "fake"

    chog_nft_address: str = "0x0000000000000000000000000000000000000001"
    chog_token_address: str = "0x0000000000000000000000000000000000000002"
    chog_vendor_address: str = "0x0000000000000000000000000000000000000003"
    chog_registry_address: str = "0x0000000000000000000000000000000000000004"

    attester_private_key: str | None = None

    database_url: str = "sqlite:///./choghub.db"
    seed_demo: bool = True  # load the demo events and quests on startup if missing
    jwt_secret: str = "dev-only-change-me-to-a-long-random-string"
    jwt_ttl_hours: int = 24
    siwe_domain: str = "localhost:3000"
    cors_origins: str = "http://localhost:3000"

    admin_wallets: str = ""  # comma-separated, lowercase or checksummed

    anthropic_api_key: str | None = None
    agent_model: str = "claude-sonnet-5-5"
    agent_max_tool_rounds: int = 6

    max_spend_mon: float = 5.0  # cap per prepared transaction
    slippage_bps: int = 100  # 1%

    @property
    def chain_id(self) -> int:
        return NETWORKS[self.network]["chain_id"]

    @property
    def effective_rpc_url(self) -> str:
        return self.rpc_url or NETWORKS[self.network]["rpc_url"]

    @property
    def explorer(self) -> str:
        return NETWORKS[self.network]["explorer"]

    @property
    def admin_set(self) -> set[str]:
        return {a.strip().lower() for a in self.admin_wallets.split(",") if a.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
