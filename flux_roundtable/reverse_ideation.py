"""
Reverse ideation: start with solutions and work backwards to problems.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


@dataclass
class Solution:
    """A proposed solution in the reverse ideation process."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    content: str = ""
    participant: str = ""
    role: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Problem:
    """A discovered problem that a solution could solve."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    content: str = ""
    solution_id: Optional[str] = None
    participant: str = ""
    role: str = ""
    severity: float = 0.5  # 0.0 (low) to 1.0 (critical)
    likelihood: float = 0.5  # 0.0 (unlikely) to 1.0 (very likely)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Validation:
    """A validation or critique of a solution-problem pairing."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    solution_id: str = ""
    problem_id: str = ""
    participant: str = ""
    role: str = ""
    is_valid: bool = True
    confidence: float = 0.5
    notes: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)


class ReverseIdeation:
    """
    A reverse ideation engine that starts with proposed solutions and
    works backwards to identify problems they solve, then validates
    the solution-problem fit.

    Flow:
        1. Propose solutions
        2. Identify problems each solution could address
        3. Validate solution-problem pairings
        4. Rank solutions by coverage and fit
    """

    def __init__(self, topic: str = "") -> None:
        self.topic = topic
        self.solutions: Dict[str, Solution] = {}
        self.problems: Dict[str, Problem] = {}
        self.validations: Dict[str, Validation] = {}
        self.solution_problems: Dict[str, List[str]] = {}  # solution_id -> [problem_ids]

    def propose_solution(self, content: str, participant: str = "", role: str = "") -> Solution:
        """Propose a solution."""
        sol = Solution(content=content, participant=participant, role=role)
        self.solutions[sol.id] = sol
        self.solution_problems[sol.id] = []
        return sol

    def identify_problem(
        self,
        content: str,
        solution_id: str,
        participant: str = "",
        role: str = "",
        severity: float = 0.5,
        likelihood: float = 0.5,
    ) -> Problem:
        """
        Identify a problem that a given solution could solve.
        """
        prob = Problem(
            content=content,
            solution_id=solution_id,
            participant=participant,
            role=role,
            severity=max(0.0, min(1.0, severity)),
            likelihood=max(0.0, min(1.0, likelihood)),
        )
        self.problems[prob.id] = prob
        if solution_id in self.solution_problems:
            self.solution_problems[solution_id].append(prob.id)
        return prob

    def validate(
        self,
        solution_id: str,
        problem_id: str,
        participant: str = "",
        role: str = "",
        is_valid: bool = True,
        confidence: float = 0.5,
        notes: str = "",
    ) -> Validation:
        """Validate a solution-problem pairing."""
        val = Validation(
            solution_id=solution_id,
            problem_id=problem_id,
            participant=participant,
            role=role,
            is_valid=is_valid,
            confidence=max(0.0, min(1.0, confidence)),
            notes=notes,
        )
        self.validations[val.id] = val
        return val

    def get_problems_for_solution(self, solution_id: str) -> List[Problem]:
        """Get all problems linked to a solution."""
        prob_ids = self.solution_problems.get(solution_id, [])
        return [self.problems[pid] for pid in prob_ids if pid in self.problems]

    def get_validations_for_pair(self, solution_id: str, problem_id: str) -> List[Validation]:
        """Get all validations for a solution-problem pair."""
        return [
            v for v in self.validations.values()
            if v.solution_id == solution_id and v.problem_id == problem_id
        ]

    def rank_solutions(self) -> List[tuple]:
        """
        Rank solutions by their problem coverage and validation scores.

        Returns list of (solution, score) tuples sorted descending.
        """
        scores: Dict[str, float] = {}

        for sol_id in self.solutions:
            linked_problems = self.get_problems_for_solution(sol_id)
            if not linked_problems:
                scores[sol_id] = 0.0
                continue

            # Coverage: number of problems
            coverage = len(linked_problems)

            # Impact: average (severity * likelihood)
            impact = sum(p.severity * p.likelihood for p in linked_problems) / len(linked_problems)

            # Validation score: average confidence of positive validations
            valid_scores = []
            for p in linked_problems:
                vals = self.get_validations_for_pair(sol_id, p.id)
                positive = [v for v in vals if v.is_valid]
                if positive:
                    valid_scores.append(sum(v.confidence for v in positive) / len(positive))

            validation_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.5

            # Composite score
            scores[sol_id] = coverage * 0.3 + impact * 0.4 + validation_score * 0.3

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [(self.solutions[sid], score) for sid, score in ranked]

    def get_top_solution(self) -> Optional[tuple]:
        """Get the highest-ranked solution and its score."""
        ranked = self.rank_solutions()
        return ranked[0] if ranked else None

    def summary(self) -> Dict:
        """Return a summary of the reverse ideation state."""
        ranked = self.rank_solutions()
        return {
            "topic": self.topic,
            "solutions": len(self.solutions),
            "problems": len(self.problems),
            "validations": len(self.validations),
            "top_solution": ranked[0][0].content if ranked else None,
            "top_score": ranked[0][1] if ranked else 0.0,
        }
