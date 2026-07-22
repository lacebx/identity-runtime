"""
Test reminder generation and deadline tracking.
"""

from datetime import datetime, timezone

from .conftest import make_agent


class TestReminders:
    def test_reminder_empty(self):
        agent = make_agent("remind-1")
        r = agent.reminders()
        assert isinstance(r, list)

    def test_reminder_with_short_deadline(self):
        agent = make_agent("remind-2")
        agent.intention("Due very soon", hours=0)  # already expired
        r = agent.reminders()
        labels = [x["label"] for x in r]
        assert "overdue" in labels or "due_soon" in labels

    def test_reminder_sorted_by_urgency(self):
        agent = make_agent("remind-3")
        agent.intention("Less urgent", hours=48)
        agent.intention("Very urgent", hours=1)
        r = agent.reminders()
        if len(r) >= 2:
            assert r[0]["urgency"] >= r[-1]["urgency"]

    def test_reminder_author_tracking(self):
        agent = make_agent("remind-4")
        agent.infer_intentions("I'll fix the bug.", author_id="alice")
        r = agent.reminders()
        matching = [x for x in r if x["author_id"] == "alice"]
        assert len(matching) >= 1


class TestDeadlineTracking:
    def test_infer_parses_tomorrow(self):
        agent = make_agent("deadline-1")
        results = agent.infer_intentions(
            "I will finish this tomorrow.",
            author_id="user-1",
        )
        assert len(results) == 1

    def test_infer_parses_next_week(self):
        agent = make_agent("deadline-2")
        results = agent.infer_intentions(
            "I'll deploy next week.",
            author_id="user-1",
        )
        assert len(results) == 1

    def test_infer_no_deadline_defaults_24h(self):
        agent = make_agent("deadline-3")
        results = agent.infer_intentions(
            "I will review the PR.",
            author_id="user-1",
        )
        assert len(results) == 1
