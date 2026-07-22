"""
Test meeting detection, creation, and outcome recording.
"""

from .conftest import make_agent


class TestMeetingDetection:
    def test_detect_meet_friday(self):
        agent = make_agent("meeting-1")
        results = agent.infer_meetings(
            "Let's meet Friday at 7.",
            author_id="user-1",
        )
        assert len(results) == 1
        assert "Friday" in results[0]["proposed_time"] or "friday" in results[0]["proposed_time"].lower()

    def test_detect_sync_today(self):
        agent = make_agent("meeting-2")
        results = agent.infer_meetings(
            "We should sync today.",
            author_id="user-2",
        )
        assert len(results) >= 1

    def test_detect_schedule_meeting(self):
        agent = make_agent("meeting-3")
        results = agent.infer_meetings(
            "Can we schedule a meeting?",
            author_id="user-3",
        )
        assert len(results) >= 1

    def test_no_meeting_detected(self):
        agent = make_agent("meeting-4")
        results = agent.infer_meetings(
            "That's a great point!",
            author_id="user-4",
        )
        assert len(results) == 0


class TestMeetingOutcomes:
    def test_record_outcome(self):
        agent = make_agent("outcome-1")
        from services.meetings import record_meeting_outcome
        event_id = record_meeting_outcome(
            agent,
            participants=["alice", "bob"],
            summary="Discussed authentication",
            decisions=["Use OAuth2", "Deploy next week"],
        )
        assert event_id is not None
        events = agent.timeline()
        assert any(e["id"] == event_id for e in events)

    def test_meeting_in_timeline(self):
        agent = make_agent("outcome-2")
        old_count = len(agent.timeline())
        agent.infer_meetings("Let's meet tomorrow", author_id="alice")
        new_count = len(agent.timeline())
        assert new_count >= old_count + 1
