"""
Consensus engine: collective decision-making from multiple viewpoints.
"""

from __future__ import annotations

import enum
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from flux_roundtable.debate_tracker import DebateTracker, ArgumentType


class ConsensusMethod(enum.Enum):
    """Methods for reaching consensus."""

    MAJORITY_VOTE = "majority_vote"
    WEIGHTED_SCORE = "weighted_score"
    UNANIMOUS = "unanimous"
    RANKED_CHOICE = "ranked_choice"


class ConsensusStatus(enum.Enum):
    CONSENSUS_REACHED = "consensus_reached"
    PARTIAL_AGREEMENT = "partial_agreement"
    DEADLOCK = "deadlock"
    PENDING = "pending"


@dataclass
class Vote:
    """A single vote cast by a participant."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    participant: str = ""
    role: str = ""
    position: str = ""
    score: float = 1.0  # -1.0 (strongly against) to +1.0 (strongly for)
    justification: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    rank: int = 1  # For ranked choice voting


@dataclass
class ConsensusResult:
    """Result of a consensus process."""

    status: ConsensusStatus = ConsensusStatus.PENDING
    positions: Dict[str, float] = field(default_factory=dict)  # position -> aggregate score
    winner: Optional[str] = None
    confidence: float = 0.0
    votes: List[Vote] = field(default_factory=list)
    method: ConsensusMethod = ConsensusMethod.MAJORITY_VOTE
    summary: str = ""
    dissent: List[str] = field(default_factory=list)  # participants who disagreed


class ConsensusEngine:
    """
    Facilitates consensus-building from multiple viewpoints using
    configurable voting and scoring methods.
    """

    def __init__(self, tracker: Optional[DebateTracker] = None) -> None:
        self.tracker = tracker
        self.votes: List[Vote] = []
        self.history: List[ConsensusResult] = []

    def cast_vote(
        self,
        participant: str,
        role: str,
        position: str,
        score: float = 1.0,
        justification: str = "",
        rank: int = 1,
    ) -> Vote:
        """Cast a vote on a position."""
        score = max(-1.0, min(1.0, score))
        vote = Vote(
            participant=participant,
            role=role,
            position=position,
            score=score,
            justification=justification,
            rank=rank,
        )
        self.votes.append(vote)
        return vote

    def majority_vote(self) -> ConsensusResult:
        """
        Simple majority: position with most votes above 0 score wins.
        """
        position_counts: Dict[str, int] = {}
        position_scores: Dict[str, float] = {}

        for v in self.votes:
            position_counts[v.position] = position_counts.get(v.position, 0) + 1
            position_scores[v.position] = position_scores.get(v.position, 0.0) + v.score

        if not position_counts:
            return ConsensusResult(
                status=ConsensusStatus.PENDING,
                method=ConsensusMethod.MAJORITY_VOTE,
                summary="No votes cast.",
            )

        total = len(self.votes)
        winner = max(position_counts, key=position_counts.get)
        winner_count = position_counts[winner]
        winner_score = position_scores[winner]

        if winner_count > total / 2:
            status = ConsensusStatus.CONSENSUS_REACHED
        elif winner_count == total:
            status = ConsensusStatus.CONSENSUS_REACHED
        else:
            status = ConsensusStatus.PARTIAL_AGREEMENT

        dissent = [v.participant for v in self.votes if v.score < 0 and v.position != winner]

        return ConsensusResult(
            status=status,
            positions=position_scores,
            winner=winner,
            confidence=winner_score / total if total > 0 else 0.0,
            votes=list(self.votes),
            method=ConsensusMethod.MAJORITY_VOTE,
            summary=f"Winner: '{winner}' with {winner_count}/{total} votes (score: {winner_score:.1f}).",
            dissent=dissent,
        )

    def weighted_score(self) -> ConsensusResult:
        """
        Weighted scoring: aggregate scores determine the winner.
        Higher absolute scores carry more influence.
        """
        position_scores: Dict[str, float] = {}
        position_counts: Dict[str, int] = {}

        for v in self.votes:
            position_scores[v.position] = position_scores.get(v.position, 0.0) + abs(v.score) * v.score
            position_counts[v.position] = position_counts.get(v.position, 0) + 1

        if not position_scores:
            return ConsensusResult(
                status=ConsensusStatus.PENDING,
                method=ConsensusMethod.WEIGHTED_SCORE,
                summary="No votes cast.",
            )

        total = len(self.votes)
        winner = max(position_scores, key=position_scores.get)
        winner_score = position_scores[winner]
        max_possible = total * 1.0
        confidence = winner_score / max_possible if max_possible > 0 else 0.0

        if confidence >= 0.6:
            status = ConsensusStatus.CONSENSUS_REACHED
        elif confidence >= 0.3:
            status = ConsensusStatus.PARTIAL_AGREEMENT
        else:
            status = ConsensusStatus.DEADLOCK

        dissent = [v.participant for v in self.votes if v.score < 0 and v.position != winner]

        return ConsensusResult(
            status=status,
            positions=position_scores,
            winner=winner,
            confidence=confidence,
            votes=list(self.votes),
            method=ConsensusMethod.WEIGHTED_SCORE,
            summary=f"Winner: '{winner}' with weighted score {winner_score:.2f} (confidence: {confidence:.0%}).",
            dissent=dissent,
        )

    def ranked_choice(self) -> ConsensusResult:
        """
        Ranked-choice voting: iteratively eliminate lowest-ranked position.
        """
        position_ranks: Dict[str, List[int]] = {}

        for v in self.votes:
            if v.position not in position_ranks:
                position_ranks[v.position] = []
            position_ranks[v.position].append(v.rank)

        if not position_ranks:
            return ConsensusResult(
                status=ConsensusStatus.PENDING,
                method=ConsensusMethod.RANKED_CHOICE,
                summary="No votes cast.",
            )

        positions = set(position_ranks.keys())
        round_num = 0

        while len(positions) > 1 and round_num < 10:
            round_num += 1
            # Score each position by average rank (lower is better)
            avg_ranks = {}
            for p in positions:
                ranks = position_ranks[p]
                avg_ranks[p] = sum(ranks) / len(ranks) if ranks else float("inf")

            # Eliminate worst
            worst = max(avg_ranks, key=avg_ranks.get)
            positions.remove(worst)

        if len(positions) == 1:
            winner = positions.pop()
            avg_ranks_all = {p: sum(r) / len(r) for p, r in position_ranks.items() if r}
            return ConsensusResult(
                status=ConsensusStatus.CONSENSUS_REACHED,
                positions=avg_ranks_all,
                winner=winner,
                confidence=0.7,
                votes=list(self.votes),
                method=ConsensusMethod.RANKED_CHOICE,
                summary=f"Winner: '{winner}' after {round_num} round(s) of ranked choice.",
                dissent=[v.participant for v in self.votes if v.position != winner],
            )

        return ConsensusResult(
            status=ConsensusStatus.DEADLOCK,
            method=ConsensusMethod.RANKED_CHOICE,
            summary="Ranked choice voting could not determine a winner.",
            votes=list(self.votes),
        )

    def unanimous(self) -> ConsensusResult:
        """
        All participants must agree (score >= 0) on the same position.
        """
        if not self.votes:
            return ConsensusResult(
                status=ConsensusStatus.PENDING,
                method=ConsensusMethod.UNANIMOUS,
                summary="No votes cast.",
            )

        positions = set(v.position for v in self.votes)
        all_positive = all(v.score >= 0 for v in self.votes)

        if len(positions) == 1 and all_positive:
            winner = positions.pop()
            avg_score = sum(v.score for v in self.votes) / len(self.votes)
            return ConsensusResult(
                status=ConsensusStatus.CONSENSUS_REACHED,
                winner=winner,
                confidence=avg_score,
                votes=list(self.votes),
                method=ConsensusMethod.UNANIMOUS,
                summary=f"Unanimous consensus: '{winner}' (avg score: {avg_score:.2f}).",
                dissent=[],
            )

        return ConsensusResult(
            status=ConsensusStatus.DEADLOCK,
            positions={v.position: v.score for v in self.votes},
            votes=list(self.votes),
            method=ConsensusMethod.UNANIMOUS,
            summary="No unanimous agreement reached.",
            dissent=[v.participant for v in self.votes if v.score < 0],
        )

    def compute(self, method: Optional[ConsensusMethod] = None) -> ConsensusResult:
        """Compute consensus using the specified method (defaults to majority vote)."""
        method = method or ConsensusMethod.MAJORITY_VOTE
        dispatch = {
            ConsensusMethod.MAJORITY_VOTE: self.majority_vote,
            ConsensusMethod.WEIGHTED_SCORE: self.weighted_score,
            ConsensusMethod.RANKED_CHOICE: self.ranked_choice,
            ConsensusMethod.UNANIMOUS: self.unanimous,
        }
        result = dispatch[method]()
        self.history.append(result)
        return result

    def reset_votes(self) -> None:
        """Clear all votes for a new round."""
        self.votes.clear()

    def get_participant_votes(self, participant: str) -> List[Vote]:
        return [v for v in self.votes if v.participant == participant]
