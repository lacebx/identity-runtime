"""
Persistence tests for timeline, relationships, and goals.

Each domain object must survive a full runtime restart via the StorageBackend.
Tests cover both JSONFileBackend and SQLiteBackend.
"""

from pathlib import Path

import pytest

from core.evaluation import register_default_criteria
from core.identity import create_identity
from runtime.orchestrator import IdentityRuntime, InteractionRequest
from runtime.persistence import get_backend


BACKEND_TYPES = ["json", "sqlite"]


@pytest.fixture(params=BACKEND_TYPES)
def backend_type_and_kwargs(request, tmp_path: Path):
    backend_type = request.param
    if backend_type == "json":
        kwargs = {"root_dir": str(tmp_path / ".identity_store")}
    else:
        kwargs = {"db_path": str(tmp_path / "identities.db")}
    return backend_type, kwargs


def _make_runtime(kwargs: dict, backend_type: str):
    storage = get_backend(backend_type, **kwargs)
    rt = IdentityRuntime(storage=storage)
    register_default_criteria(rt.evaluation_engine)
    return rt


class TestTimelinePersistence:
    """Timeline events must survive restart."""

    def test_timeline_survives_restart(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs

        rt1 = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="TimelineBot", identity_id="timeline-bot")
        rt1.register(spec)
        sid = rt1.start_session("timeline-bot")
        rt1.process(InteractionRequest(
            identity_id="timeline-bot",
            user_input="Hello, first message.",
            session_id=sid,
        ))
        rt1.process(InteractionRequest(
            identity_id="timeline-bot",
            user_input="Second message here.",
            session_id=sid,
        ))
        assert len(rt1.timeline_registry.get("timeline-bot")) >= 3

        rt2 = _make_runtime(kwargs, backend_type)
        rt2.load_persisted()
        timeline = rt2.timeline_registry.get("timeline-bot")
        assert timeline is not None
        events = timeline.events()
        assert len(events) >= 3
        titles = [e.title for e in events]
        assert "Interaction" in titles

    def test_timeline_multiple_sessions(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs
        rt = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="MultiSess", identity_id="multi-sess")
        rt.register(spec)

        sid1 = rt.start_session("multi-sess")
        sid2 = rt.start_session("multi-sess")
        rt.process(InteractionRequest(
            identity_id="multi-sess", user_input="Session 1", session_id=sid1,
        ))
        rt.process(InteractionRequest(
            identity_id="multi-sess", user_input="Session 2", session_id=sid2,
        ))
        events = rt.timeline_registry.get("multi-sess").events()
        assert len(events) >= 3


class TestRelationshipPersistence:
    """Relationship graph edges must survive restart."""

    def test_relationships_survive_restart(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs

        rt1 = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="RelBot", identity_id="rel-bot")
        rt1.register(spec)
        sid = rt1.start_session("rel-bot")
        rt1.process(InteractionRequest(
            identity_id="rel-bot", user_input="Hello", session_id=sid,
        ))
        edges = rt1.identity_graph.get_relationships("rel-bot")
        assert len(edges) >= 1

        rt2 = _make_runtime(kwargs, backend_type)
        rt2.load_persisted()
        restored_edges = rt2.identity_graph.get_relationships("rel-bot")
        assert len(restored_edges) >= 1
        assert restored_edges[0].source_id == "rel-bot"

    def test_relationships_accumulate(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs
        rt = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="AccumBot", identity_id="accum-bot")
        rt.register(spec)

        sid1 = rt.start_session("accum-bot")
        sid2 = rt.start_session("accum-bot")
        rt.process(InteractionRequest(
            identity_id="accum-bot", user_input="Msg 1", session_id=sid1,
        ))
        rt.process(InteractionRequest(
            identity_id="accum-bot", user_input="Msg 2", session_id=sid2,
        ))
        edges = rt.identity_graph.get_relationships("accum-bot")
        assert len(edges) >= 1


class TestGoalPersistence:
    """Goals must survive restart."""

    def test_goals_survive_restart(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs

        rt1 = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="GoalBot", identity_id="goal-bot")
        rt1.register(spec)

        from core.goals import Goal
        goal = Goal(title="Learn persistence", description="Goals should persist")
        rt1.goal_engine.add(goal)
        assert len(rt1.goal_engine) == 1

        sid = rt1.start_session("goal-bot")
        rt1.process(InteractionRequest(
            identity_id="goal-bot", user_input="Work on goals", session_id=sid,
        ))

        rt2 = _make_runtime(kwargs, backend_type)
        rt2.load_persisted()
        assert len(rt2.goal_engine) >= 1
        goals = rt2.goal_engine.active()
        titles = [g.title for g in goals]
        assert "Learn persistence" in titles

    def test_goals_multiple(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs
        rt = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="MultiGoal", identity_id="multi-goal")
        rt.register(spec)

        from core.goals import Goal
        rt.goal_engine.add(Goal(title="Goal A"))
        rt.goal_engine.add(Goal(title="Goal B"))

        sid = rt.start_session("multi-goal")
        rt.process(InteractionRequest(
            identity_id="multi-goal", user_input="Test", session_id=sid,
        ))

        assert len(rt.goal_engine) == 2

        rt2 = _make_runtime(kwargs, backend_type)
        rt2.load_persisted()
        assert len(rt2.goal_engine) >= 2


class TestCrossDomainPersistence:
    """All three domains persist together in a single restart."""

    def test_all_survive_restart(self, backend_type_and_kwargs):
        backend_type, kwargs = backend_type_and_kwargs

        rt1 = _make_runtime(kwargs, backend_type)
        spec = create_identity(name="AllBot", identity_id="all-bot")
        rt1.register(spec)

        from core.goals import Goal
        rt1.goal_engine.add(Goal(title="Cross-domain goal"))

        sid = rt1.start_session("all-bot")
        rt1.process(InteractionRequest(
            identity_id="all-bot", user_input="Test all domains", session_id=sid,
        ))

        assert len(rt1.timeline_registry.get("all-bot")) >= 2
        assert len(rt1.identity_graph.get_relationships("all-bot")) >= 1
        assert len(rt1.goal_engine) == 1

        rt2 = _make_runtime(kwargs, backend_type)
        rt2.load_persisted()

        timeline = rt2.timeline_registry.get("all-bot")
        assert timeline is not None
        assert len(timeline) >= 2

        edges = rt2.identity_graph.get_relationships("all-bot")
        assert len(edges) >= 1

        assert len(rt2.goal_engine) >= 1
