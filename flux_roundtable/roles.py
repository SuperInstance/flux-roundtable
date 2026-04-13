"""
Role definitions and assignment for roundtable participants.
"""

from __future__ import annotations

import enum
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional


class Role(enum.Enum):
    """Predefined roles for roundtable participants."""

    DEVILS_ADVOCATE = "Devil's Advocate"
    INNOVATOR = "Innovator"
    PRAGMATIST = "Pragmatist"
    VISIONARY = "Visionary"
    ANALYST = "Analyst"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def from_string(cls, value: str) -> Role:
        """Parse a role from its string name (case-insensitive)."""
        mapping = {
            "devil's advocate": cls.DEVILS_ADVOCATE,
            "devils advocate": cls.DEVILS_ADVOCATE,
            "innovator": cls.INNOVATOR,
            "pragmatist": cls.PRAGMATIST,
            "visionary": cls.VISIONARY,
            "analyst": cls.ANALYST,
        }
        return mapping[value.strip().lower()]


@dataclass
class RoleProfile:
    """Detailed profile for a role, including its strategic bias and focus areas."""

    role: Role
    description: str = ""
    bias: str = ""
    focus_areas: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    blind_spots: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.description:
            self.description = _DEFAULT_PROFILES[self.role]["description"]
            self.bias = _DEFAULT_PROFILES[self.role]["bias"]
            self.focus_areas = list(_DEFAULT_PROFILES[self.role]["focus_areas"])
            self.strengths = list(_DEFAULT_PROFILES[self.role]["strengths"])
            self.blind_spots = list(_DEFAULT_PROFILES[self.role]["blind_spots"])


# Default profiles for each role
_DEFAULT_PROFILES: Dict[Role, dict] = {
    Role.DEVILS_ADVOCATE: {
        "description": (
            "Challenges assumptions, identifies risks, and stress-tests "
            "proposals to prevent groupthink."
        ),
        "bias": "Conservative / skeptical",
        "focus_areas": ["risk assessment", "failure modes", "hidden costs"],
        "strengths": ["critical thinking", "risk identification", "logic"],
        "blind_spots": ["overly pessimistic", "resists change", "misses upside"],
    },
    Role.INNOVATOR: {
        "description": (
            "Generates novel solutions, connects disparate ideas, and "
            "pushes creative boundaries."
        ),
        "bias": "Optimistic / creative",
        "focus_areas": ["novelty", "emerging tech", "paradigm shifts"],
        "strengths": ["creativity", "lateral thinking", "rapid prototyping"],
        "blind_spots": ["impractical ideas", "ignores constraints", "scope creep"],
    },
    Role.PRAGMATIST: {
        "description": (
            "Grounds discussions in reality, evaluates feasibility, and "
            "prioritizes actionable steps."
        ),
        "bias": "Practical / grounded",
        "focus_areas": ["implementation", "resource constraints", "timelines"],
        "strengths": ["planning", "resource management", "risk mitigation"],
        "blind_spots": ["resists innovation", "too conservative", "misses long-term"],
    },
    Role.VISIONARY: {
        "description": (
            "Explores long-term implications, future possibilities, and "
            "strategic alignment."
        ),
        "bias": "Forward-looking / ambitious",
        "focus_areas": ["strategy", "long-term impact", "market evolution"],
        "strengths": ["strategic thinking", "foresight", "inspiration"],
        "blind_spots": ["impractical timing", "vague details", "ignores present"],
    },
    Role.ANALYST: {
        "description": (
            "Provides data-driven insights, quantitative analysis, and "
            "evidence-based evaluations."
        ),
        "bias": "Objective / data-driven",
        "focus_areas": ["metrics", "benchmarks", "empirical evidence"],
        "strengths": ["data analysis", "pattern recognition", "precision"],
        "blind_spots": ["analysis paralysis", "misses qualitative factors", "rigid"],
    },
}


@dataclass
class RoleAssignment:
    """Manages role assignments for roundtable participants."""

    assignments: Dict[str, Role] = field(default_factory=dict)
    profiles: Dict[str, RoleProfile] = field(default_factory=dict)

    def assign(self, participant: str, role: Role) -> None:
        """Assign a role to a participant."""
        self.assignments[participant] = role
        self.profiles[participant] = RoleProfile(role=role)

    def get_role(self, participant: str) -> Optional[Role]:
        """Get the role assigned to a participant."""
        return self.assignments.get(participant)

    def get_profile(self, participant: str) -> Optional[RoleProfile]:
        """Get the detailed profile for a participant."""
        return self.profiles.get(participant)

    def unassign(self, participant: str) -> Optional[Role]:
        """Remove a participant's role assignment. Returns the removed role."""
        role = self.assignments.pop(participant, None)
        if role and participant in self.profiles:
            del self.profiles[participant]
        return role

    def list_participants(self) -> List[str]:
        """List all assigned participants."""
        return list(self.assignments.keys())

    def list_roles(self) -> List[Role]:
        """List all currently assigned roles."""
        return list(self.assignments.values())

    def get_participants_for_role(self, role: Role) -> List[str]:
        """Get all participants assigned to a specific role."""
        return [p for p, r in self.assignments.items() if r == role]

    def auto_assign(self, participants: List[str]) -> Dict[str, Role]:
        """Auto-assign roles to participants, cycling through all roles."""
        roles = list(Role)
        random.shuffle(roles)
        for i, participant in enumerate(participants):
            role = roles[i % len(roles)]
            self.assign(participant, role)
        return dict(self.assignments)

    def has_role(self, role: Role) -> bool:
        """Check if any participant is assigned the given role."""
        return role in self.assignments.values()
