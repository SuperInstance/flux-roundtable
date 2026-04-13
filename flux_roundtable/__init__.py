"""
FLUX Roundtable - Multi-Agent Role-Play & Reverse-Ideation System
==================================================================

A structured debate and ideation framework where agents assume distinct
personas (Devil's Advocate, Innovator, Pragmatist, Visionary, Analyst)
to collaboratively explore problems and solutions.

Quick Start
-----------
>>> from flux_roundtable import RoundTable, Role
>>> table = RoundTable("Should we use ISA v2 or v3?")
>>> table.add_role(Role.DEVILS_ADVOCATE)
>>> table.add_role(Role.INNOVATOR)
>>> table.contribute("Devil's Advocate", "ISA v2 is proven, v3 is untested")
>>> table.contribute("Innovator", "v3 edge encoding saves 40% bandwidth")
>>> result = table.get_consensus()
"""

__version__ = "1.0.0"
__author__ = "Super Z"

from flux_roundtable.roles import Role, RoleAssignment
from flux_roundtable.roundtable import RoundTable, DiscussionPhase
from flux_roundtable.reverse_ideation import ReverseIdeation
from flux_roundtable.debate_tracker import DebateTracker, Argument, ArgumentType
from flux_roundtable.consensus import ConsensusEngine, ConsensusResult, ConsensusMethod, ConsensusStatus, Vote
from flux_roundtable.session import Session, SessionRecorder, SessionReplay

__all__ = [
    "Role",
    "RoleAssignment",
    "RoundTable",
    "DiscussionPhase",
    "ReverseIdeation",
    "DebateTracker",
    "Argument",
    "ArgumentType",
    "ConsensusEngine",
    "ConsensusResult",
    "ConsensusMethod",
    "ConsensusStatus",
    "Vote",
    "Session",
    "SessionRecorder",
    "SessionReplay",
]
