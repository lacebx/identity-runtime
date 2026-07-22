"""
Test timeline events and evidence lookup.
"""

from .conftest import make_agent


class TestTimeline:
    def test_record_event(self):
        agent = make_agent("tl-1")
        eid = agent.record_event("milestone", "Test event", "A test", significance=3)
        assert eid is not None
        events = agent.timeline()
        assert any(e["id"] == eid for e in events)

    def test_timeline_list(self):
        agent = make_agent("tl-2")
        events = agent.timeline()
        assert isinstance(events, list)

    def test_timeline_ordering(self):
        agent = make_agent("tl-3")
        e1 = agent.record_event("milestone", "First", significance=1)
        e2 = agent.record_event("milestone", "Second", significance=2)
        events = agent.timeline(limit=10)
        ids = [e["id"] for e in events]
        assert e1 in ids
        assert e2 in ids

    def test_record_various_types(self):
        agent = make_agent("tl-4")
        for etype in ["creation", "milestone", "goal_completed", "failure", "knowledge_acquired"]:
            eid = agent.record_event(etype, f"Event {etype}", significance=2)
            assert eid is not None


class TestEvidence:
    def test_evidence_for_entity(self):
        agent = make_agent("ev-1")
        g = agent.goal("Evidence test goal", priority="high")
        ev = agent.evidence(g["id"])
        assert isinstance(ev, list)

    def test_provenance(self):
        agent = make_agent("ev-2")
        g = agent.goal("Provenance test", priority="medium")
        prov = agent.provenance(g["id"])
        assert prov["entity_id"] == g["id"]
        assert "confidence" in prov

    def test_confidence_score(self):
        agent = make_agent("ev-3")
        g = agent.goal("Confidence test", priority="high")
        c = agent.confidence(g["id"])
        assert c["entity_id"] == g["id"]
        assert "label" in c
