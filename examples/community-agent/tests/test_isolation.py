"""
Test session isolation — each Discord thread/channel is a separate session.
"""

from .conftest import make_agent


class TestSessionIsolation:
    def test_sessions_list(self):
        agent = make_agent("sessions-1")
        sessions = agent.sessions()
        assert isinstance(sessions, list)

    def test_session_context_manager(self):
        agent = make_agent("sessions-2")
        with agent.session() as s:
            reply = s.chat("Session test")
        assert isinstance(reply, str)

    def test_session_id(self):
        agent = make_agent("sessions-3")
        custom_id = "discord:guild:channel"
        with agent.session(session_id=custom_id) as s:
            reply = s.chat("Custom session")
        assert isinstance(reply, str)

    def test_session_observe(self):
        agent = make_agent("sessions-4")
        with agent.session() as s:
            facts = s.observe("My name is Bob")
        assert isinstance(facts, list)

    def test_sessions_after_use(self):
        agent = make_agent("sessions-5")
        with agent.session() as s:
            s.chat("Hello")
        sessions = agent.sessions()
        assert isinstance(sessions, list)
