"""The no-LLM agent should understand everyday phrasing, not just exact commands."""
import os

os.environ.setdefault("CHAIN_MODE", "fake")
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402

from app.config import get_settings  # noqa: E402


@pytest.fixture(scope="module")
def ctx():
    if os.path.exists("test_rules.db"):
        os.remove("test_rules.db")
    get_settings.cache_clear()
    from sqlalchemy.orm import sessionmaker

    from app.db import init_db, make_engine
    from app.seed_data import seed
    from app.services import ecosystem as eco
    from app.services.agent import AgentContext
    from app.services.chain import FakeChain

    engine = make_engine("sqlite:///./test_rules.db")
    init_db(engine)
    db = sessionmaker(bind=engine, expire_on_commit=False)()
    seed(db)
    chain = FakeChain()
    wallet = "0x00000000000000000000000000000000000000aa"
    chain.mint(wallet, 1, {"hat": "Beanie", "mood": "Chaotic", "background": "Purple"})
    chain.fund(wallet, 5)
    chog = eco.sync_chog(db, chain, 1)
    yield AgentContext(db=db, chain=chain, settings=get_settings(), wallet=wallet, chog=chog)
    db.close()
    engine.dispose()
    if os.path.exists("test_rules.db"):
        os.remove("test_rules.db")


def say(ctx, text, history=None):
    from app.services.agent import chat

    ctx.actions = []
    msgs = (history or []) + [{"role": "user", "content": text}]
    return chat(ctx, msgs)


def test_buy_without_amount_asks_then_follows_up(ctx):
    r = say(ctx, "can you buy me chog token?")
    assert "How much CHOG" in r["reply"] and r["actions"] == []
    r2 = say(ctx, "10", [{"role": "user", "content": "can you buy me chog token?"},
                         {"role": "assistant", "content": r["reply"]}])
    assert len(r2["actions"]) == 1 and r2["actions"][0]["params"]["chog_amount"] == 10


@pytest.mark.parametrize("text,amount", [("buy 25 chog", 25), ("Get me fifty CHOG please", 50), ("purchase 1.5k chog", 1500)])
def test_buy_amounts(ctx, text, amount):
    r = say(ctx, text)
    assert r["actions"][0]["params"]["chog_amount"] == amount


def test_balance(ctx):
    assert "MON" in say(ctx, "how much chog do i have?")["reply"]


def test_join_by_name_and_start_quest_in_one_message(ctx):
    r = say(ctx, "register me for the community call and start the meme quest")
    assert "you're in Chog Community Call" in r["reply"]
    assert "Quest started: Create a Chog meme" in r["reply"]


def test_join_ambiguous_lists_options(ctx):
    r = say(ctx, "sign me up for an event")
    assert "Which one?" in r["reply"]


def test_quest_that_completes_automatically(ctx):
    r = say(ctx, "start the buy quest")
    assert "completes" in r["reply"]


def test_distinct_answers(ctx):
    replies = {say(ctx, q)["reply"] for q in [
        "hi", "who are you?", "what events are coming up?", "what quests are there", "show my badges",
        "what can you do", "what's happening today?",
    ]}
    assert len(replies) == 7


def test_unknown_gets_help_not_today_list(ctx):
    r = say(ctx, "what's the weather in Lagos")
    assert "didn't quite get that" in r["reply"]
