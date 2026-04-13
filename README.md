# FLUX Roundtable

> Multi-Agent Role-Play & Reverse-Ideation System for the FLUX Fleet

A structured debate and ideation framework where agents assume distinct personas to collaboratively explore problems, debate solutions, and reach consensus through multiple viewpoints.

## Features

- **5 Built-in Roles**: Devil's Advocate, Innovator, Pragmatist, Visionary, Analyst — each with detailed profiles, biases, strengths, and blind spots
- **Debate Tracking**: Full argument tracking with pro/con, counter-arguments, evidence, and clustering
- **Consensus Engine**: 4 consensus methods — majority vote, weighted score, ranked choice, unanimous
- **Reverse Ideation**: Start with solutions, work backwards to discover problems they solve, then rank by coverage and fit
- **Session Recording**: Complete event-level recording with JSON serialization and replay
- **Clean Python API**: Simple, intuitive interface for orchestrating multi-perspective discussions

## Quick Start

```python
from flux_roundtable import RoundTable, Role

# Create a roundtable with a topic
table = RoundTable("Should we use ISA v2 or v3?")

# Add roles
table.add_role(Role.DEVILS_ADVOCATE)
table.add_role(Role.INNOVATOR)

# Contribute arguments
table.contribute("Devil's Advocate", "ISA v2 is proven, v3 is untested", arg_type="con")
table.contribute("Innovator", "v3 edge encoding saves 40% bandwidth")
table.provide_evidence("Innovator", "Benchmark data: 40% bandwidth reduction in v3")

# Counter-arguments
arg1 = table.contribute("Innovator", "v3 is production ready")
table.counter("Devil's Advocate", "Only 2 deployments exist, not battle-tested", arg1.id)

# Vote and reach consensus
table.cast_vote("Innovator", "Use v3", score=0.9)
table.cast_vote("Devil's Advocate", "Use v2", score=0.3)
result = table.get_consensus()
print(result.summary)  # Winner and confidence
```

## Roles

| Role | Bias | Focus |
|------|------|-------|
| **Devil's Advocate** | Conservative / Skeptical | Risk assessment, failure modes, hidden costs |
| **Innovator** | Optimistic / Creative | Novelty, emerging tech, paradigm shifts |
| **Pragmatist** | Practical / Grounded | Implementation, resource constraints, timelines |
| **Visionary** | Forward-looking / Ambitious | Strategy, long-term impact, market evolution |
| **Analyst** | Objective / Data-driven | Metrics, benchmarks, empirical evidence |

## Reverse Ideation

```python
from flux_roundtable import RoundTable, Role

table = RoundTable("How to improve edge throughput?")

# Propose solutions first
sol = table.propose_solution("Innovator", "ISA v3 encoding")

# Then identify problems each solution solves
table.identify_problem("Innovator", sol.id, "High bandwidth costs at edge", severity=0.9)
table.identify_problem("Pragmatist", sol.id, "Legacy protocol overhead", severity=0.7)

# Validate and rank
table.validate(sol.id, prob_id, "Analyst", is_valid=True, confidence=0.9)
ranked = table.get_ranked_solutions()  # Best solution first
```

## Session Recording & Replay

```python
table = RoundTable("Discussion topic")
table.add_role(Role.INNOVATOR)
table.contribute("Innovator", "My argument")

# Export session as JSON
json_data = table.export_session()

# Get human-readable transcript
print(table.get_transcript())
```

## Consensus Methods

| Method | Description |
|--------|-------------|
| `majority_vote` | Simple plurality — most votes wins |
| `weighted_score` | Score-weighted — higher absolute scores carry more influence |
| `ranked_choice` | Instant-runoff — iteratively eliminate lowest-ranked |
| `unanimous` | All participants must agree on the same position |

## Installation

```bash
pip install flux-roundtable
```

Or from source:

```bash
git clone https://github.com/SuperInstance/flux-roundtable.git
cd flux-roundtable
pip install -e .
```

## Testing

```bash
python -m pytest tests/ -v
```

## Architecture

```
flux_roundtable/
├── __init__.py          # Public API
├── roles.py             # Role enum, RoleProfile, RoleAssignment
├── debate_tracker.py    # Argument, ArgumentType, DebateTracker, ArgumentCluster
├── consensus.py         # ConsensusEngine, Vote, ConsensusResult, ConsensusMethod
├── reverse_ideation.py  # ReverseIdeation, Solution, Problem, Validation
├── roundtable.py        # RoundTable orchestrator, DiscussionPhase
└── session.py           # Session, SessionRecorder, SessionReplay
```

## License

MIT — see [LICENSE](LICENSE).
