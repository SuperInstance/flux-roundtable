"""
RoundTable: The main orchestration class for multi-perspective discussions.
"""

from __future__ import annotations

import enum
from typing import Any, Dict, List, Optional

from flux_roundtable.roles import Role, RoleAssignment, RoleProfile
from flux_roundtable.debate_tracker import (
    DebateTracker,
    Argument,
    ArgumentType,
)
from flux_roundtable.consensus import (
    ConsensusEngine,
    ConsensusMethod,
    ConsensusResult,
)
from flux_roundtable.reverse_ideation import ReverseIdeation
from flux_roundtable.session import Session, SessionRecorder, SessionReplay


class DiscussionPhase(enum.Enum):
    """Phases of a roundtable discussion."""

    SETUP = "setup"
    IDEATION = "ideation"
    DEBATE = "debate"
    REFINEMENT = "refinement"
    CONSENSUS = "consensus"
    CLOSED = "closed"


class RoundTable:
    """
    Orchestrates a multi-perspective roundtable discussion.

    Example:
        >>> table = RoundTable("Should we use ISA v2 or v3?")
        >>> table.add_role(Role.DEVILS_ADVOCATE)
        >>> table.add_role(Role.INNOVATOR)
        >>> table.contribute("Devil's Advocate", "ISA v2 is proven, v3 is untested")
        >>> table.contribute("Innovator", "v3 edge encoding saves 40% bandwidth")
        >>> result = table.get_consensus()
    """

    def __init__(self, topic: str, enable_recording: bool = True) -> None:
        self.topic = topic
        self.phase = DiscussionPhase.SETUP
        self.role_assignment = RoleAssignment()
        self.tracker = DebateTracker(topic=topic)
        self.consensus_engine = ConsensusEngine(tracker=self.tracker)
        self.reverse_ideation = ReverseIdeation(topic=topic)
        self.recorder = SessionRecorder()
        self._session: Optional[Session] = None
        self._enable_recording = enable_recording
        self._contributions: List[Dict[str, Any]] = []

    def _ensure_session(self) -> None:
        """Lazily create a session when needed."""
        if self._enable_recording and self._session is None:
            self._session = self.recorder.start_session(topic=self.topic)
            self._record("session_init", data={"topic": self.topic})

    def _record(self, event_type: str, participant: str = "", role: str = "", data: Optional[Dict] = None) -> None:
        """Record an event to the current session."""
        if self._enable_recording and self._session:
            self.recorder.record_event(
                self._session.session_id, event_type, participant, role, data
            )

    # --- Phase Management ---

    def set_phase(self, phase: DiscussionPhase) -> None:
        """Move the discussion to a new phase."""
        self.phase = phase
        self._ensure_session()
        self._record("phase_change", data={"phase": phase.value})

    @property
    def is_active(self) -> bool:
        return self.phase != DiscussionPhase.CLOSED

    def close(self) -> None:
        """Close the roundtable session."""
        self.set_phase(DiscussionPhase.CLOSED)
        if self._session:
            self.recorder.end_session(self._session.session_id)

    # --- Role Management ---

    def add_role(self, role: Role, participant_name: Optional[str] = None) -> str:
        """
        Add a role to the roundtable. If participant_name is not provided,
        uses the role name as the participant identifier.
        """
        name = participant_name or str(role)
        self.role_assignment.assign(name, role)
        self._ensure_session()
        self._record("role_assign", participant=name, role=str(role))
        return name

    def add_participant(self, name: str, role: Role) -> str:
        """Add a named participant with a specific role."""
        self.role_assignment.assign(name, role)
        self._ensure_session()
        self._record("role_assign", participant=name, role=str(role))
        return name

    def remove_participant(self, name: str) -> Optional[Role]:
        """Remove a participant from the roundtable."""
        removed = self.role_assignment.unassign(name)
        self._record("role_remove", participant=name)
        return removed

    def get_participants(self) -> List[str]:
        return self.role_assignment.list_participants()

    def get_role_profile(self, participant: str) -> Optional[RoleProfile]:
        return self.role_assignment.get_profile(participant)

    def auto_assign_roles(self, participants: List[str]) -> Dict[str, Role]:
        """Automatically assign roles to a list of participants."""
        result = self.role_assignment.auto_assign(participants)
        for p, r in result.items():
            self._record("role_assign", participant=p, role=str(r))
        return result

    # --- Contributions ---

    def contribute(
        self,
        participant: str,
        content: str,
        arg_type: str = "pro",
        parent_id: Optional[str] = None,
        weight: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> Argument:
        """
        Have a participant contribute an argument to the discussion.

        Args:
            participant: The name of the contributing participant.
            content: The content of the argument.
            arg_type: Type of argument ("pro", "con", "question", "evidence",
                      "clarification", "counter", "concession", "synthesis").
            parent_id: Optional ID of a parent argument (for rebuttals).
            weight: Importance weight (default 1.0).
            tags: Optional tags for categorization.

        Returns:
            The created Argument.
        """
        self._ensure_session()
        role = self.role_assignment.get_role(participant)
        role_str = str(role) if role else ""

        arg_type_enum = ArgumentType(arg_type)
        arg = self.tracker.add(
            participant=participant,
            role=role_str,
            content=content,
            arg_type=arg_type_enum,
            parent_id=parent_id,
            tags=tags or [],
            weight=weight,
        )

        self._contributions.append({
            "participant": participant,
            "role": role_str,
            "content": content,
            "type": arg_type,
            "argument_id": arg.id,
        })

        self._record(
            "contribute",
            participant=participant,
            role=role_str,
            data={"content": content, "type": arg_type, "arg_id": arg.id},
        )

        return arg

    def ask_question(self, participant: str, content: str) -> Argument:
        """Shortcut: ask a clarifying question."""
        return self.contribute(participant, content, arg_type="question")

    def provide_evidence(self, participant: str, content: str, weight: float = 1.5) -> Argument:
        """Shortcut: provide evidence with higher default weight."""
        return self.contribute(participant, content, arg_type="evidence", weight=weight)

    def counter(self, participant: str, content: str, parent_id: str) -> Argument:
        """Shortcut: create a counter-argument."""
        return self.contribute(participant, content, arg_type="counter", parent_id=parent_id)

    # --- Consensus ---

    def cast_vote(
        self,
        participant: str,
        position: str,
        score: float = 1.0,
        justification: str = "",
    ) -> None:
        """Have a participant cast a vote."""
        role = self.role_assignment.get_role(participant)
        role_str = str(role) if role else ""
        self.consensus_engine.cast_vote(participant, role_str, position, score, justification)
        self._record(
            "vote",
            participant=participant,
            role=role_str,
            data={"position": position, "score": score, "justification": justification},
        )

    def get_consensus(self, method: Optional[ConsensusMethod] = None) -> ConsensusResult:
        """Compute and return the consensus result."""
        self.set_phase(DiscussionPhase.CONSENSUS)
        result = self.consensus_engine.compute(method)
        self._record("consensus_result", data={
            "status": result.status.value,
            "winner": result.winner,
            "confidence": result.confidence,
            "summary": result.summary,
        })
        return result

    def reset_votes(self) -> None:
        """Reset all votes for a new consensus round."""
        self.consensus_engine.reset_votes()
        self._record("votes_reset")

    # --- Reverse Ideation ---

    def propose_solution(self, participant: str, content: str) -> Any:
        """Propose a solution via reverse ideation."""
        role_str = str(self.role_assignment.get_role(participant) or "")
        sol = self.reverse_ideation.propose_solution(content, participant, role_str)
        self._record(
            "solution_proposed",
            participant=participant,
            role=role_str,
            data={"content": content, "solution_id": sol.id},
        )
        return sol

    def identify_problem(
        self,
        participant: str,
        solution_id: str,
        content: str,
        severity: float = 0.5,
        likelihood: float = 0.5,
    ) -> Any:
        """Identify a problem that a solution addresses."""
        role_str = str(self.role_assignment.get_role(participant) or "")
        prob = self.reverse_ideation.identify_problem(
            content, solution_id, participant, role_str, severity, likelihood
        )
        self._record(
            "problem_identified",
            participant=participant,
            role=role_str,
            data={"content": content, "solution_id": solution_id, "problem_id": prob.id},
        )
        return prob

    def get_ranked_solutions(self) -> List[tuple]:
        """Get solutions ranked by problem coverage and fit."""
        return self.reverse_ideation.rank_solutions()

    # --- Query ---

    def get_arguments(self) -> List[Argument]:
        """Get all arguments in discussion order."""
        return list(self.tracker.timeline)

    def get_argument(self, arg_id: str) -> Optional[Argument]:
        return self.tracker.get_argument(arg_id)

    def get_arguments_by_participant(self, participant: str) -> List[Argument]:
        return self.tracker.get_arguments_by_participant(participant)

    def get_cluster(self, arg_id: str):
        return self.tracker.get_cluster(arg_id)

    def get_debate_summary(self) -> Dict:
        return self.tracker.summary()

    def get_transcript(self) -> str:
        """Get a human-readable transcript of the session."""
        if self._session:
            replay = SessionReplay(self._session)
            return replay.get_transcript()
        return "No recording available."

    def export_session(self) -> Optional[str]:
        """Export the session as JSON."""
        if self._session:
            return self.recorder.export_session(self._session.session_id)
        return None

    # --- Summary ---

    def summary(self) -> Dict:
        """Get a full summary of the roundtable state."""
        return {
            "topic": self.topic,
            "phase": self.phase.value,
            "participants": self.get_participants(),
            "total_arguments": self.tracker.total_arguments,
            "debate_summary": self.tracker.summary(),
            "reverse_ideation": self.reverse_ideation.summary(),
            "votes_cast": len(self.consensus_engine.votes),
            "session_id": self._session.session_id if self._session else None,
            "recording_enabled": self._enable_recording,
        }
