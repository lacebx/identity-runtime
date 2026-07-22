"""
Test relationship learning and trust tracking.
"""

from .conftest import make_agent


class TestRelationships:
    def test_create_relationship(self):
        agent = make_agent("rel-1")
        rel = agent.relationship("user-alice", trust_level=0.8, context="Frequent collaborator")
        assert rel["target_id"] == "user-alice"
        assert rel["trust_level"] >= 3  # TrustLevel.HIGH

    def test_list_relationships(self):
        agent = make_agent("rel-2")
        agent.relationship("user-bob", trust_level=0.5, context="Team member")
        rels = agent.relationships()
        assert len(rels) >= 1
        assert any(r["target_id"] == "user-bob" for r in rels)

    def test_relationship_edge_types(self):
        agent = make_agent("rel-3")
        rel = agent.relationship("user-mentor", trust_level=0.9, edge_type="mentor")
        assert rel["edge_type"] == "mentor"

    def test_query_relationship(self):
        agent = make_agent("rel-4")
        agent.relationship("user-query", trust_level=0.6)
        result = agent.relationship("user-query")
        assert result["target_id"] == "user-query"
