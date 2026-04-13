"""
Debate tracking: arguments, counter-arguments, evidence, and consensus tracking.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class ArgumentType(enum.Enum):
    """Types of arguments in a debate."""

    PRO = "pro"
    CON = "con"
    QUESTION = "question"
    EVIDENCE = "evidence"
    CLARIFICATION = "clarification"
    COUNTER = "counter"
    CONCESSION = "concession"
    SYNTHESIS = "synthesis"


@dataclass
class Argument:
    """A single argument within a debate."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    participant: str = ""
    role: str = ""
    argument_type: ArgumentType = ArgumentType.PRO
    content: str = ""
    topic: str = ""
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    parent_id: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    weight: float = 1.0

    def counter(self, participant: str, role: str, content: str, **kwargs) -> Argument:
        """Create a counter-argument linked to this argument."""
        return Argument(
            participant=participant,
            role=role,
            argument_type=ArgumentType.COUNTER,
            content=content,
            topic=self.topic,
            parent_id=self.id,
            **kwargs,
        )


@dataclass
class ArgumentCluster:
    """A cluster of related arguments (original + rebuttals)."""

    root: Argument
    rebuttals: List[Argument] = field(default_factory=list)

    @property
    def net_score(self) -> float:
        """Compute a simple pro/con score for the cluster."""
        score = 0.0
        if self.root.argument_type in (ArgumentType.PRO, ArgumentType.EVIDENCE):
            score += self.root.weight
        elif self.root.argument_type in (ArgumentType.CON, ArgumentType.COUNTER):
            score -= self.root.weight
        for r in self.rebuttals:
            if r.argument_type in (ArgumentType.PRO, ArgumentType.EVIDENCE, ArgumentType.COUNTER):
                score += r.weight
            elif r.argument_type in (ArgumentType.CON,):
                score -= r.weight
        return score

    @property
    def argument_count(self) -> int:
        return 1 + len(self.rebuttals)


class DebateTracker:
    """
    Tracks all arguments, counter-arguments, and their relationships
    throughout a roundtable session.
    """

    def __init__(self, topic: str = "") -> None:
        self.topic = topic
        self.arguments: Dict[str, Argument] = {}
        self.clusters: List[ArgumentCluster] = []
        self.timeline: List[Argument] = []
        self.participant_stats: Dict[str, Dict[str, int]] = {}

    def add_argument(self, arg: Argument) -> Argument:
        """Register a new argument."""
        self.arguments[arg.id] = arg
        self.timeline.append(arg)

        if arg.parent_id and arg.parent_id in self.arguments:
            cluster = self._find_cluster_by_root(arg.parent_id)
            if cluster:
                cluster.rebuttals.append(arg)
            else:
                parent = self.arguments[arg.parent_id]
                self.clusters.append(ArgumentCluster(root=parent, rebuttals=[arg]))
        else:
            self.clusters.append(ArgumentCluster(root=arg))

        # Update participant stats
        if arg.participant not in self.participant_stats:
            self.participant_stats[arg.participant] = {
                "total": 0,
                "pro": 0,
                "con": 0,
                "questions": 0,
                "evidence": 0,
            }
        self.participant_stats[arg.participant]["total"] += 1
        type_key = {
            ArgumentType.PRO: "pro",
            ArgumentType.CON: "con",
            ArgumentType.QUESTION: "questions",
            ArgumentType.EVIDENCE: "evidence",
        }.get(arg.argument_type)
        if type_key:
            self.participant_stats[arg.participant][type_key] += 1

        return arg

    def add(
        self,
        participant: str,
        role: str,
        content: str,
        arg_type: ArgumentType = ArgumentType.PRO,
        parent_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        **kwargs,
    ) -> Argument:
        """Convenience method: create and add an argument in one call."""
        arg = Argument(
            participant=participant,
            role=role,
            argument_type=arg_type,
            content=content,
            topic=self.topic,
            parent_id=parent_id,
            tags=tags or [],
            **kwargs,
        )
        return self.add_argument(arg)

    def get_argument(self, arg_id: str) -> Optional[Argument]:
        return self.arguments.get(arg_id)

    def get_arguments_by_participant(self, participant: str) -> List[Argument]:
        return [a for a in self.timeline if a.participant == participant]

    def get_arguments_by_type(self, arg_type: ArgumentType) -> List[Argument]:
        return [a for a in self.timeline if a.argument_type == arg_type]

    def get_arguments_by_role(self, role: str) -> List[Argument]:
        return [a for a in self.timeline if a.role == role]

    def _find_cluster_by_root(self, root_id: str) -> Optional[ArgumentCluster]:
        for c in self.clusters:
            if c.root.id == root_id or any(r.id == root_id for r in c.rebuttals):
                return c
        return None

    def get_cluster(self, arg_id: str) -> Optional[ArgumentCluster]:
        """Get the cluster containing the given argument."""
        for c in self.clusters:
            if c.root.id == arg_id:
                return c
            if any(r.id == arg_id for r in c.rebuttals):
                return c
        return None

    @property
    def total_arguments(self) -> int:
        return len(self.timeline)

    @property
    def participants(self) -> List[str]:
        return list(self.participant_stats.keys())

    def summary(self) -> Dict:
        """Return a summary of the debate state."""
        return {
            "topic": self.topic,
            "total_arguments": self.total_arguments,
            "clusters": len(self.clusters),
            "participants": self.participants,
            "participant_stats": dict(self.participant_stats),
        }

    def strongest_pro(self) -> Optional[Argument]:
        """Return the pro argument with the highest weight."""
        pros = [a for a in self.timeline if a.argument_type in (ArgumentType.PRO, ArgumentType.EVIDENCE)]
        return max(pros, key=lambda a: a.weight, default=None)

    def strongest_con(self) -> Optional[Argument]:
        """Return the con argument with the highest weight."""
        cons = [a for a in self.timeline if a.argument_type in (ArgumentType.CON, ArgumentType.COUNTER)]
        return max(cons, key=lambda a: a.weight, default=None)

    def get_timeline_snapshot(self) -> List[Dict]:
        """Export the argument timeline as a list of dicts."""
        return [
            {
                "id": a.id,
                "participant": a.participant,
                "role": a.role,
                "type": a.argument_type.value,
                "content": a.content,
                "timestamp": a.timestamp.isoformat(),
                "parent_id": a.parent_id,
            }
            for a in self.timeline
        ]
