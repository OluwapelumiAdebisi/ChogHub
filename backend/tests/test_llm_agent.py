"""The Claude path: valid conversation shape, tool loop, and fallback with a visible error."""
import os
from types import SimpleNamespace

os.environ.setdefault("CHAIN_MODE", "fake")

import anthropic  # noqa: E402
import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402


@pytest.fixture()
def ctx(tmp_path):
    from sqlalchemy.orm import sessionmaker

    from app.db import init_db, make_engine
    from app.seed_data import seed
    from app.services import ecosystem as eco
    from app.services.agent import AgentContext
    from app.services.chain import FakeChain

    engine = make_engine(f"sqlite:///{tmp_path}/llm.db")
    init_db(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(db)
    chain = FakeChain()
    wallet = "0x00000000000000000000000000000000000000bb"
    chain.mint(wallet, 1)
    settings = get_settings().model_copy(update={"anthropic_api_key": "sk-test"})
    yield AgentContext(db=db, chain=chain, settings=settings, wallet=wallet, chog=eco.sync_chog(db, chain, 1))
    db.close()


class FakeClient:
    """Answers with one tool call, then text. Records what it was sent."""

    def __init__(self, *a, **k):
        self.calls = []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        FakeClient.last = self
        msgs = kw["messages"]
        assert msgs[0]["role"] == "user", "conversation must start with the user"
        for a, b in zip(msgs, msgs[1:]):
            assert a["role"] != b["role"], "roles must alternate"
        if len(self.calls) == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[
                SimpleNamespace(type="tool_use", id="t1", name="get_ecosystem_today", input={})])
        return SimpleNamespace(stop_reason="end_turn", content=[SimpleNamespace(type="text", text="Start with Meme Wars!")])


def test_greeting_first_history_is_valid(ctx, monkeypatch):
    from app.services import agent

    monkeypatch.setattr(anthropic, "Anthropic", FakeClient)
    history = [
        {"role": "assistant", "content": "Chog #1 here. What are we getting up to?"},
        {"role": "user", "content": "what should I do first"},
    ]
    out = agent.chat(ctx, history)
    assert out["reply"] == "Start with Meme Wars!"
    assert out["tools_used"] == ["get_ecosystem_today"]


def test_api_failure_falls_back_and_is_reported(ctx, monkeypatch):
    from app.services import agent

    class Broken:
        def __init__(self, *a, **k):
            self.messages = self

        def create(self, **kw):
            raise RuntimeError("model not found: claude-nope")

    monkeypatch.setattr(anthropic, "Anthropic", Broken)
    out = agent.chat(ctx, [{"role": "user", "content": "what should I do first"}])
    assert "Here's what's on" in out["reply"]  # rules agent answered
    assert agent.LAST_AGENT_ERROR["message"].startswith("model not found")
