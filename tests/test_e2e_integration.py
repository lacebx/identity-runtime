"""
End-to-end integration tests for IdentityOS v0.1.

Tests the full pipeline across all subsystems:
- Identity lifecycle (create, load, persist)
- Context composition (all blocks rendered)
- Memory extraction and persistence
- Timeline recording and persistence
- Relationship tracking and persistence
- Goal management and persistence
- Adapter invocation
- Restart survival for all domain objects
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from core.evaluation import register_default_criteria
from core.identity import create_identity
from runtime.orchestrator import IdentityRuntime, InteractionRequest
from runtime.persistence import JSONFileBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_adapter():
    """A mock adapter that returns a predictable response."""
    import sys
    _openai_mock = MagicMock()
    sys.modules["openai"] = _openai_mock

    _openai_mock.OpenAI = MagicMock()
    client = MagicMock()
    _openai_mock.OpenAI.return_value = client

    choice = MagicMock()
    choice.message.content = "I am TestBot, your AI identity."
    completion = MagicMock()
    completion.choices = [choice]
    client.chat.completions.create.return_value = completion

    from adapters.openai_adapter import OpenAIAdapter
    adapter = OpenAIAdapter(api_key="sk-test")
    yield adapter


@pytest.fixture
def runtime_with_adapter(mock_adapter, tmp_path: Path):
    storage = JSONFileBackend(root_dir=str(tmp_path / ".identity_store"))
    rt = IdentityRuntime(storage=storage, adapter=mock_adapter)
    register_default_criteria(rt.evaluation_engine)
    return rt


@pytest.fixture
def runtime(tmp_path: Path):
    storage = JSONFileBackend(root_dir=str(tmp_path / ".identity_store"))
    rt = IdentityRuntime(storage=storage)
    register_default_criteria(rt.evaluation_engine)
    return rt


# ---------------------------------------------------------------------------
# Full pipeline tests
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """End-to-end: register → process → verify all subsystems."""

    def test_full_pipeline_without_adapter(self, runtime):
        spec = create_identity(name="E2EBot", identity_id="e2e-bot")
        runtime.register(spec)

        assert runtime.identity_store.get("e2e-bot") is not None
        assert runtime.timeline_registry.get("e2e-bot") is not None

        sid = runtime.start_session("e2e-bot")
        resp = runtime.process(InteractionRequest(
            identity_id="e2e-bot",
            user_input="My favorite programming language is Python.",
            session_id=sid,
        ))
        assert resp.identity_id == "e2e-bot"
        assert "No adapter configured" in resp.output
        assert resp.policy_passed is True

        timeline = runtime.timeline_registry.get("e2e-bot")
        assert len(timeline) >= 2
        # Timeline title now reflects memory classification
        assert timeline.events()[-1].title != "Interaction"  # should be "Learned preference"

        edges = runtime.identity_graph.get_relationships("e2e-bot")
        assert len(edges) >= 1

        mems = runtime.memory_store.by_identity(identity_id="e2e-bot")
        assert len(mems) >= 1
        semantic = [m for m in mems if "Python" in m.content]
        assert len(semantic) >= 1

        ctx = resp.context_used
        assert ctx is not None
        assert "E2EBot" in ctx.identity_block
        assert "Timeline" in ctx.timeline_block

        # Verify memories were stored
        mems = runtime.memory_store.by_identity(identity_id="e2e-bot")
        assert len(mems) >= 1
        assert any("Python" in m.content for m in mems)

        # Verify relationship was recorded (happens post-compose at stage 9)
        edges = runtime.identity_graph.get_relationships("e2e-bot")
        assert len(edges) >= 1
        assert edges[0].source_id == "e2e-bot"

    def test_full_pipeline_with_adapter(self, runtime_with_adapter):
        spec = create_identity(
            name="AdapterBot",
            identity_id="adapter-e2e",
        )
        runtime_with_adapter.register(spec)

        sid = runtime_with_adapter.start_session("adapter-e2e")
        resp = runtime_with_adapter.process(InteractionRequest(
            identity_id="adapter-e2e",
            user_input="What is your purpose?",
            session_id=sid,
        ))
        assert "TestBot" in resp.output
        assert resp.policy_passed is True
        assert resp.eval_score is not None

    def test_context_composer_includes_all_blocks(self, runtime):
        from core.goals import Goal
        from core.motivations import Motivation, MotivationStrength, MotivationDomain

        spec = create_identity(
            name="FullBot",
            identity_id="full-bot",
            persona="wise mentor",
        )
        runtime.register(spec)

        runtime.goal_engine.add(Goal(title="Test all context blocks"))
        runtime.motivation_engine.add(Motivation(
            name="Curiosity",
            domain=MotivationDomain.TRUTH,
            strength=MotivationStrength.CORE,
        ))

        sid = runtime.start_session("full-bot")
        runtime.process(InteractionRequest(
            identity_id="full-bot",
            user_input="Show me everything.",
            session_id=sid,
        ))

        ctx = runtime.context_composer.compose(
            identity=spec,
            memory_store=runtime.memory_store,
            skill_registry=runtime.skill_registry,
            goal_engine=runtime.goal_engine,
            identity_graph=runtime.identity_graph,
            motivation_engine=runtime.motivation_engine,
            timeline_registry=runtime.timeline_registry,
        )
        rendered = ctx.render()

        assert "FullBot" in rendered
        assert "Core Motivations" in rendered or "No active goals" in rendered
        assert "Timeline" in rendered
        assert "Test all context blocks" in rendered


# ---------------------------------------------------------------------------
# Restart survival tests
# ---------------------------------------------------------------------------

class TestRestartSurvival:
    """All domain objects survive a full runtime restart."""

    def test_everything_survives_restart(self, tmp_path: Path):
        store_path = str(tmp_path / ".identity_store")

        storage1 = JSONFileBackend(root_dir=store_path)
        rt1 = IdentityRuntime(storage=storage1)
        register_default_criteria(rt1.evaluation_engine)

        from core.goals import Goal
        spec = create_identity(name="SurvivorBot", identity_id="survivor")
        rt1.register(spec)
        rt1.goal_engine.add(Goal(title="Survive restart"))

        sid = rt1.start_session("survivor")
        rt1.process(InteractionRequest(
            identity_id="survivor",
            user_input="My favorite color is blue.",
            session_id=sid,
        ))
        rt1.process(InteractionRequest(
            identity_id="survivor",
            user_input="I enjoy hiking.",
            session_id=sid,
        ))

        storage2 = JSONFileBackend(root_dir=store_path)
        rt2 = IdentityRuntime(storage=storage2)
        register_default_criteria(rt2.evaluation_engine)
        rt2.load_persisted()

        assert rt2.identity_store.get("survivor") is not None

        timeline = rt2.timeline_registry.get("survivor")
        assert timeline is not None
        assert len(timeline) >= 3

        edges = rt2.identity_graph.get_relationships("survivor")
        assert len(edges) >= 1

        assert len(rt2.goal_engine) >= 1
        goals = rt2.goal_engine.active()
        assert any("Survive restart" in g.title for g in goals)

        mems = rt2.memory_store.by_identity(identity_id="survivor")
        assert len(mems) >= 1
        semantic = [m for m in mems if any("blue" in m.content for m in mems)]
        assert len(semantic) >= 1


# ---------------------------------------------------------------------------
# Multi-identity isolation tests
# ---------------------------------------------------------------------------

class TestMultiIdentity:
    """Multiple identities must remain properly isolated."""

    def test_identities_isolated_after_restart(self, tmp_path: Path):
        store_path = str(tmp_path / ".identity_store")
        storage = JSONFileBackend(root_dir=store_path)
        rt = IdentityRuntime(storage=storage)
        register_default_criteria(rt.evaluation_engine)

        from core.goals import Goal
        bot1 = create_identity(name="BotAlice", identity_id="alice")
        bot2 = create_identity(name="BotBob", identity_id="bob")
        rt.register(bot1)
        rt.register(bot2)

        rt.goal_engine.add(Goal(title="Alice's goal"))
        sid1 = rt.start_session("alice")
        rt.process(InteractionRequest(
            identity_id="alice", user_input="Alice's secret", session_id=sid1,
        ))

        sid2 = rt.start_session("bob")
        rt.process(InteractionRequest(
            identity_id="bob", user_input="Bob's secret", session_id=sid2,
        ))

        storage2 = JSONFileBackend(root_dir=store_path)
        rt2 = IdentityRuntime(storage=storage2)
        register_default_criteria(rt2.evaluation_engine)
        rt2.load_persisted()

        alice_edges = rt2.identity_graph.get_relationships("alice")
        bob_edges = rt2.identity_graph.get_relationships("bob")
        assert len(alice_edges) >= 1
        assert len(bob_edges) >= 1

        alice_mems = rt2.memory_store.by_identity(identity_id="alice")
        bob_mems = rt2.memory_store.by_identity(identity_id="bob")
        alice_text = " ".join(m.content for m in alice_mems)
        bob_text = " ".join(m.content for m in bob_mems)
        assert "Alice" in alice_text
        assert "Bob" in bob_text


# ---------------------------------------------------------------------------
# Pipeline failure modes
# ---------------------------------------------------------------------------

class TestPipelineFailureModes:
    """The pipeline must handle edge cases gracefully."""

    def test_missing_identity(self, runtime):
        resp = runtime.process(InteractionRequest(
            identity_id="nonexistent",
            user_input="Hello",
        ))
        assert resp.policy_passed is False
        assert "not found" in resp.output.lower()

    def test_policy_blocked_input(self, runtime):
        from core.policies import Policy, PolicyEffect, PolicyScope

        spec = create_identity(name="BlockedBot", identity_id="blocked")
        runtime.register(spec)

        runtime.policy_engine.add(Policy(
            name="BlockTest",
            description="Block inputs containing 'blocked'",
            scope=PolicyScope.INPUT,
            effect=PolicyEffect.DENY,
            condition=lambda data: "blocked" in str(data).lower(),
        ))

        sid = runtime.start_session("blocked")
        resp = runtime.process(InteractionRequest(
            identity_id="blocked",
            user_input="This is blocked content",
            session_id=sid,
        ))
        assert resp.policy_passed is False
        assert "Blocked" in resp.output

    def test_memory_persists_across_sessions(self, runtime):
        spec = create_identity(name="SessionBot", identity_id="session-bot")
        runtime.register(spec)

        sid1 = runtime.start_session("session-bot")
        runtime.process(InteractionRequest(
            identity_id="session-bot",
            user_input="My name is John.",
            session_id=sid1,
        ))
        runtime.end_session(sid1)

        sid2 = runtime.start_session("session-bot")
        resp = runtime.process(InteractionRequest(
            identity_id="session-bot",
            user_input="What is my name?",
            session_id=sid2,
        ))
        assert resp.policy_passed is True

        mems = runtime.memory_store.by_identity(identity_id="session-bot")
        assert any("John" in m.content for m in mems)
