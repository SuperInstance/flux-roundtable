"""
Session recording and replay for roundtable discussions.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class SessionEvent:
    """A single event in a roundtable session."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    event_type: str = ""  # "contribute", "vote", "role_assign", "phase_change", etc.
    timestamp: datetime = field(default_factory=datetime.utcnow)
    participant: str = ""
    role: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "participant": self.participant,
            "role": self.role,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, d: Dict) -> SessionEvent:
        d = dict(d)
        d["timestamp"] = datetime.fromisoformat(d["timestamp"])
        return cls(**d)


class Session:
    """Represents a recorded roundtable session."""

    def __init__(
        self,
        session_id: Optional[str] = None,
        topic: str = "",
        created_at: Optional[datetime] = None,
    ) -> None:
        self.session_id = session_id or uuid.uuid4().hex[:12]
        self.topic = topic
        self.created_at = created_at or datetime.utcnow()
        self.events: List[SessionEvent] = []
        self.metadata: Dict[str, Any] = {}
        self.ended_at: Optional[datetime] = None

    def record(self, event: SessionEvent) -> None:
        """Record an event to the session."""
        self.events.append(event)

    def record_event(
        self,
        event_type: str,
        participant: str = "",
        role: str = "",
        data: Optional[Dict] = None,
    ) -> SessionEvent:
        """Create and record an event in one call."""
        event = SessionEvent(
            event_type=event_type,
            participant=participant,
            role=role,
            data=data or {},
        )
        self.events.append(event)
        return event

    def end(self) -> None:
        """Mark the session as ended."""
        self.ended_at = datetime.utcnow()

    @property
    def duration(self) -> float:
        """Session duration in seconds."""
        if self.ended_at:
            return (self.ended_at - self.created_at).total_seconds()
        return (datetime.utcnow() - self.created_at).total_seconds()

    @property
    def event_count(self) -> int:
        return len(self.events)

    def get_events_by_type(self, event_type: str) -> List[SessionEvent]:
        return [e for e in self.events if e.event_type == event_type]

    def get_events_by_participant(self, participant: str) -> List[SessionEvent]:
        return [e for e in self.events if e.participant == participant]

    def get_events_in_range(self, start: datetime, end: datetime) -> List[SessionEvent]:
        return [e for e in self.events if start <= e.timestamp <= end]

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "topic": self.topic,
            "created_at": self.created_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "events": [e.to_dict() for e in self.events],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, d: Dict) -> Session:
        session = cls(
            session_id=d["session_id"],
            topic=d["topic"],
            created_at=datetime.fromisoformat(d["created_at"]),
        )
        session.ended_at = (
            datetime.fromisoformat(d["ended_at"]) if d.get("ended_at") else None
        )
        session.metadata = d.get("metadata", {})
        for ed in d.get("events", []):
            session.events.append(SessionEvent.from_dict(ed))
        return session

    @classmethod
    def from_json(cls, json_str: str) -> Session:
        return cls.from_dict(json.loads(json_str))


class SessionRecorder:
    """
    Records roundtable sessions with full event history.
    """

    def __init__(self) -> None:
        self.sessions: Dict[str, Session] = {}

    def start_session(self, topic: str = "", metadata: Optional[Dict] = None) -> Session:
        """Start a new session."""
        session = Session(topic=topic)
        session.metadata = metadata or {}
        self.sessions[session.session_id] = session
        session.record_event("session_start", data={"topic": topic})
        return session

    def record_event(
        self,
        session_id: str,
        event_type: str,
        participant: str = "",
        role: str = "",
        data: Optional[Dict] = None,
    ) -> Optional[SessionEvent]:
        """Record an event to an existing session."""
        session = self.sessions.get(session_id)
        if session:
            return session.record_event(event_type, participant, role, data)
        return None

    def end_session(self, session_id: str) -> Optional[Session]:
        """End an existing session."""
        session = self.sessions.get(session_id)
        if session:
            session.end()
            session.record_event("session_end")
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        return self.sessions.get(session_id)

    def list_sessions(self) -> List[str]:
        return list(self.sessions.keys())

    def export_session(self, session_id: str) -> Optional[str]:
        """Export a session as JSON."""
        session = self.sessions.get(session_id)
        return session.to_json() if session else None

    def import_session(self, json_str: str) -> Session:
        """Import a session from JSON."""
        session = Session.from_json(json_str)
        self.sessions[session.session_id] = session
        return session


class SessionReplay:
    """
    Replays a recorded session event-by-event.
    """

    def __init__(self, session: Session) -> None:
        self.session = session
        self._cursor = 0

    def reset(self) -> None:
        """Reset replay to the beginning."""
        self._cursor = 0

    @property
    def is_complete(self) -> bool:
        return self._cursor >= len(self.session.events)

    @property
    def progress(self) -> float:
        if not self.session.events:
            return 1.0
        return self._cursor / len(self.session.events)

    def next(self) -> Optional[SessionEvent]:
        """Get the next event in the replay."""
        if self.is_complete:
            return None
        event = self.session.events[self._cursor]
        self._cursor += 1
        return event

    def peek(self) -> Optional[SessionEvent]:
        """Peek at the next event without advancing the cursor."""
        if self.is_complete:
            return None
        return self.session.events[self._cursor]

    def replay_all(self) -> List[SessionEvent]:
        """Return all remaining events and advance to end."""
        remaining = self.session.events[self._cursor:]
        self._cursor = len(self.session.events)
        return remaining

    def replay_by_type(self, event_type: str) -> List[SessionEvent]:
        """Replay only events of a specific type."""
        self.reset()
        filtered = []
        while True:
            event = self.next()
            if event is None:
                break
            if event.event_type == event_type:
                filtered.append(event)
        return filtered

    def get_transcript(self) -> str:
        """Get a human-readable transcript of the session."""
        lines = [f"=== Roundtable Session: {self.session.topic} ==="]
        lines.append(f"Session ID: {self.session.session_id}")
        lines.append(f"Started: {self.session.created_at.isoformat()}")
        lines.append("")

        for event in self.session.events:
            ts = event.timestamp.strftime("%H:%M:%S")
            if event.event_type in ("session_start", "session_end"):
                lines.append(f"[{ts}] --- {event.event_type.upper()} ---")
            else:
                role_tag = f" ({event.role})" if event.role else ""
                lines.append(f"[{ts}] {event.participant}{role_tag}: [{event.event_type}] {event.data.get('content', '')}")

        if self.session.ended_at:
            lines.append(f"\nEnded: {self.session.ended_at.isoformat()}")
            lines.append(f"Duration: {self.session.duration:.1f}s")

        return "\n".join(lines)
