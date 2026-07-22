"""
Test intention detection, creation, completion, and promotion.
"""

from services.intentions import complete_authors_intention
from .conftest import make_agent


class TestIntentionDetection:
    def test_infer_direct_commitment(self):
        agent = make_agent("infer-1")
        results = agent.infer_intentions(
            "I'll finish authentication tomorrow.",
            author_id="user-1",
        )
        assert len(results) == 1
        assert results[0]["description"] == "finish authentication"
        assert results[0]["metadata"]["author_id"] == "user-1"

    def test_infer_deploy(self):
        agent = make_agent("infer-2")
        results = agent.infer_intentions(
            "I will deploy tonight.",
            author_id="user-2",
        )
        assert len(results) == 1
        assert "deploy" in results[0]["description"]

    def test_infer_review(self):
        agent = make_agent("infer-3")
        results = agent.infer_intentions(
            "Let me review the PR.",
            author_id="user-3",
        )
        assert len(results) == 1
        assert "review" in results[0]["description"]

    def test_infer_no_commitment(self):
        agent = make_agent("infer-4")
        results = agent.infer_intentions(
            "That's a great idea!",
            author_id="user-4",
        )
        assert len(results) == 0

    def test_infer_multiple_authors(self):
        agent = make_agent("infer-5")
        r1 = agent.infer_intentions("I'll fix the bug today.", author_id="alice")
        r2 = agent.infer_intentions("I will write docs tomorrow.", author_id="bob")
        assert len(r1) == 1
        assert len(r2) == 1
        assert r1[0]["metadata"]["author_id"] == "alice"
        assert r2[0]["metadata"]["author_id"] == "bob"


class TestIntentionLifecycle:
    def test_create_and_list(self):
        agent = make_agent("lifecycle-1")
        i = agent.intention("Test intention", priority="high", hours=24)
        intentions = agent.intentions()
        assert len(intentions) >= 1
        assert any(x["id"] == i["id"] for x in intentions)

    def test_complete(self):
        agent = make_agent("lifecycle-2")
        i = agent.intention("Complete me", hours=24)
        assert agent.complete_intention(i["id"])
        intentions = agent.intentions("completed")
        assert any(x["id"] == i["id"] for x in intentions)

    def test_complete_by_author(self):
        agent = make_agent("lifecycle-3")
        agent.infer_intentions("I'll finish the report.", author_id="alice")
        agent.infer_intentions("I will review.", author_id="bob")

        from services.intentions import complete_authors_intention
        result = complete_authors_intention(agent, "alice", "I finished")
        assert result is not None
        assert result["description"] == "finish the report"

    def test_promote_to_goal(self):
        agent = make_agent("lifecycle-4")
        i = agent.intention("Important task", hours=72)
        g = agent.goal("Important goal", priority="high")
        assert agent.promote_intention(i["id"], g["id"])
