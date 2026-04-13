"""Comprehensive test suite for FLUX Roundtable."""

import json
import unittest
from datetime import datetime, timedelta

from flux_roundtable import (
    Role,
    RoleAssignment,
    RoundTable,
    ReverseIdeation,
    DebateTracker,
    Argument,
    ArgumentType,
    ConsensusEngine,
    ConsensusResult,
    ConsensusMethod,
    ConsensusStatus,
    Vote,
    Session,
    SessionRecorder,
    SessionReplay,
    DiscussionPhase,
)
from flux_roundtable.roundtable import RoundTable as RT


class TestRoleEnum(unittest.TestCase):
    """Test Role enum functionality."""

    def test_all_roles_exist(self):
        expected = {"Devil's Advocate", "Innovator", "Pragmatist", "Visionary", "Analyst"}
        actual = {r.value for r in Role}
        self.assertEqual(actual, expected)

    def test_role_str(self):
        self.assertEqual(str(Role.INNOVATOR), "Innovator")

    def test_from_string_case_insensitive(self):
        self.assertEqual(Role.from_string("innovator"), Role.INNOVATOR)
        self.assertEqual(Role.from_string("  ANALYST  "), Role.ANALYST)
        self.assertEqual(Role.from_string("devil's advocate"), Role.DEVILS_ADVOCATE)
        self.assertEqual(Role.from_string("devils advocate"), Role.DEVILS_ADVOCATE)


class TestRoleProfile(unittest.TestCase):
    """Test RoleProfile defaults."""

    def test_profile_has_all_fields(self):
        from flux_roundtable.roles import RoleProfile
        profile = RoleProfile(role=Role.INNOVATOR)
        self.assertTrue(len(profile.description) > 10)
        self.assertTrue(len(profile.bias) > 0)
        self.assertTrue(len(profile.focus_areas) > 0)
        self.assertTrue(len(profile.strengths) > 0)
        self.assertTrue(len(profile.blind_spots) > 0)

    def test_custom_profile_overrides(self):
        from flux_roundtable.roles import RoleProfile
        profile = RoleProfile(role=Role.ANALYST, description="Custom", bias="Neutral")
        self.assertEqual(profile.description, "Custom")
        self.assertEqual(profile.bias, "Neutral")


class TestRoleAssignment(unittest.TestCase):
    """Test RoleAssignment management."""

    def setUp(self):
        self.ra = RoleAssignment()

    def test_assign_and_get(self):
        self.ra.assign("Alice", Role.INNOVATOR)
        self.assertEqual(self.ra.get_role("Alice"), Role.INNOVATOR)

    def test_assign_creates_profile(self):
        self.ra.assign("Bob", Role.PRAGMATIST)
        profile = self.ra.get_profile("Bob")
        self.assertIsNotNone(profile)
        self.assertEqual(profile.role, Role.PRAGMATIST)

    def test_unassign(self):
        self.ra.assign("Carol", Role.VISIONARY)
        removed = self.ra.unassign("Carol")
        self.assertEqual(removed, Role.VISIONARY)
        self.assertIsNone(self.ra.get_role("Carol"))

    def test_list_participants(self):
        self.ra.assign("A", Role.DEVILS_ADVOCATE)
        self.ra.assign("B", Role.ANALYST)
        self.assertEqual(set(self.ra.list_participants()), {"A", "B"})

    def test_list_roles(self):
        self.ra.assign("A", Role.DEVILS_ADVOCATE)
        self.ra.assign("B", Role.ANALYST)
        self.assertEqual(set(self.ra.list_roles()), {Role.DEVILS_ADVOCATE, Role.ANALYST})

    def test_participants_for_role(self):
        self.ra.assign("A", Role.INNOVATOR)
        self.ra.assign("B", Role.INNOVATOR)
        self.ra.assign("C", Role.PRAGMATIST)
        result = self.ra.get_participants_for_role(Role.INNOVATOR)
        self.assertEqual(set(result), {"A", "B"})

    def test_has_role(self):
        self.ra.assign("A", Role.VISIONARY)
        self.assertTrue(self.ra.has_role(Role.VISIONARY))
        self.assertFalse(self.ra.has_role(Role.ANALYST))

    def test_auto_assign(self):
        participants = ["P1", "P2", "P3"]
        self.ra.auto_assign(participants)
        self.assertEqual(len(self.ra.list_participants()), 3)
        for p in participants:
            self.assertIsNotNone(self.ra.get_role(p))

    def test_unassign_nonexistent(self):
        self.assertIsNone(self.ra.unassign("Nobody"))

    def test_get_role_nonexistent(self):
        self.assertIsNone(self.ra.get_role("Nobody"))


class TestArgument(unittest.TestCase):
    """Test Argument dataclass."""

    def test_create_argument(self):
        arg = Argument(participant="Alice", role="Innovator", content="Let's try X")
        self.assertEqual(arg.participant, "Alice")
        self.assertEqual(arg.argument_type, ArgumentType.PRO)

    def test_counter_creates_link(self):
        parent = Argument(participant="Alice", role="Innovator", content="Yes we should")
        child = parent.counter(participant="Bob", role="Pragmatist", content="No we shouldn't")
        self.assertEqual(child.parent_id, parent.id)
        self.assertEqual(child.argument_type, ArgumentType.COUNTER)
        self.assertEqual(child.topic, parent.topic)


class TestDebateTracker(unittest.TestCase):
    """Test DebateTracker functionality."""

    def setUp(self):
        self.dt = DebateTracker(topic="ISA v2 vs v3")

    def test_add_argument(self):
        arg = self.dt.add("Alice", "Innovator", "v3 is better", ArgumentType.PRO)
        self.assertEqual(self.dt.total_arguments, 1)
        self.assertEqual(arg.id, self.dt.timeline[0].id)

    def test_add_with_parent(self):
        a1 = self.dt.add("Alice", "Innovator", "Pro v3", ArgumentType.PRO)
        a2 = self.dt.add("Bob", "Pragmatist", "Con v3", ArgumentType.COUNTER, parent_id=a1.id)
        cluster = self.dt.get_cluster(a1.id)
        self.assertIsNotNone(cluster)
        self.assertEqual(len(cluster.rebuttals), 1)

    def test_participant_stats(self):
        self.dt.add("Alice", "Innovator", "Pro", ArgumentType.PRO)
        self.dt.add("Alice", "Innovator", "Evidence", ArgumentType.EVIDENCE)
        self.dt.add("Bob", "Analyst", "Question", ArgumentType.QUESTION)
        stats = self.dt.participant_stats
        self.assertEqual(stats["Alice"]["total"], 2)
        self.assertEqual(stats["Alice"]["pro"], 1)
        self.assertEqual(stats["Bob"]["questions"], 1)

    def test_filter_by_participant(self):
        self.dt.add("Alice", "Innovator", "A")
        self.dt.add("Bob", "Analyst", "B")
        alice_args = self.dt.get_arguments_by_participant("Alice")
        self.assertEqual(len(alice_args), 1)

    def test_filter_by_type(self):
        self.dt.add("Alice", "Innovator", "Pro", ArgumentType.PRO)
        self.dt.add("Bob", "Analyst", "Con", ArgumentType.CON)
        self.assertEqual(len(self.dt.get_arguments_by_type(ArgumentType.PRO)), 1)
        self.assertEqual(len(self.dt.get_arguments_by_type(ArgumentType.CON)), 1)

    def test_strongest_pro_con(self):
        self.dt.add("Alice", "Innovator", "Mild pro", ArgumentType.PRO, weight=0.5)
        self.dt.add("Bob", "Analyst", "Strong pro", ArgumentType.PRO, weight=2.0)
        self.dt.add("Carol", "Pragmatist", "Mild con", ArgumentType.CON, weight=0.3)
        self.dt.add("Dave", "Devil's Advocate", "Strong con", ArgumentType.CON, weight=1.8)
        self.assertEqual(self.dt.strongest_pro().content, "Strong pro")
        self.assertEqual(self.dt.strongest_con().content, "Strong con")

    def test_summary(self):
        self.dt.add("Alice", "Innovator", "Hello")
        s = self.dt.summary()
        self.assertEqual(s["topic"], "ISA v2 vs v3")
        self.assertEqual(s["total_arguments"], 1)

    def test_timeline_snapshot(self):
        self.dt.add("Alice", "Innovator", "Hello")
        snapshot = self.dt.get_timeline_snapshot()
        self.assertEqual(len(snapshot), 1)
        self.assertIn("id", snapshot[0])
        self.assertIn("timestamp", snapshot[0])

    def test_net_score_cluster(self):
        a1 = self.dt.add("Alice", "Innovator", "Pro", ArgumentType.PRO, weight=1.0)
        self.dt.add("Bob", "Pragmatist", "Counter", ArgumentType.COUNTER, parent_id=a1.id, weight=0.5)
        cluster = self.dt.get_cluster(a1.id)
        # PRO contributes +1.0, COUNTER contributes +0.5 (counters add positively in net score logic)
        self.assertIsNotNone(cluster)


class TestConsensusEngine(unittest.TestCase):
    """Test ConsensusEngine voting methods."""

    def setUp(self):
        self.ce = ConsensusEngine()

    def test_cast_vote(self):
        v = self.ce.cast_vote("Alice", "Innovator", "Use v3", score=0.8)
        self.assertEqual(v.score, 0.8)

    def test_majority_vote_clear_winner(self):
        self.ce.cast_vote("Alice", "Innovator", "Use v3", score=0.9)
        self.ce.cast_vote("Bob", "Analyst", "Use v3", score=0.7)
        self.ce.cast_vote("Carol", "Pragmatist", "Use v2", score=0.5)
        result = self.ce.majority_vote()
        self.assertEqual(result.winner, "Use v3")
        self.assertEqual(result.status, ConsensusStatus.CONSENSUS_REACHED)

    def test_weighted_score(self):
        self.ce.cast_vote("Alice", "Innovator", "Use v3", score=1.0)
        self.ce.cast_vote("Bob", "Analyst", "Use v3", score=0.8)
        self.ce.cast_vote("Carol", "Pragmatist", "Use v2", score=0.3)
        result = self.ce.weighted_score()
        self.assertEqual(result.winner, "Use v3")
        self.assertTrue(result.confidence > 0)

    def test_ranked_choice(self):
        self.ce.cast_vote("Alice", "Innovator", "v3", rank=1)
        self.ce.cast_vote("Bob", "Analyst", "v3", rank=1)
        self.ce.cast_vote("Carol", "Pragmatist", "v2", rank=2)
        result = self.ce.ranked_choice()
        self.assertEqual(result.winner, "v3")

    def test_unanimous_consensus(self):
        self.ce.cast_vote("Alice", "Innovator", "Use v3", score=0.9)
        self.ce.cast_vote("Bob", "Analyst", "Use v3", score=0.8)
        result = self.ce.unanimous()
        self.assertEqual(result.status, ConsensusStatus.CONSENSUS_REACHED)

    def test_unanimous_deadlock(self):
        self.ce.cast_vote("Alice", "Innovator", "Use v3", score=0.9)
        self.ce.cast_vote("Bob", "Analyst", "Use v2", score=0.7)
        result = self.ce.unanimous()
        self.assertEqual(result.status, ConsensusStatus.DEADLOCK)

    def test_no_votes(self):
        result = self.ce.majority_vote()
        self.assertEqual(result.status, ConsensusStatus.PENDING)

    def test_compute_default(self):
        self.ce.cast_vote("A", "R", "X", score=0.5)
        result = self.ce.compute()
        self.assertEqual(result.method, ConsensusMethod.MAJORITY_VOTE)

    def test_reset_votes(self):
        self.ce.cast_vote("A", "R", "X")
        self.ce.reset_votes()
        self.assertEqual(len(self.ce.votes), 0)

    def test_get_participant_votes(self):
        self.ce.cast_vote("Alice", "R", "X", score=0.5)
        self.ce.cast_vote("Bob", "R", "Y", score=0.3)
        self.assertEqual(len(self.ce.get_participant_votes("Alice")), 1)

    def test_history_tracked(self):
        self.ce.cast_vote("A", "R", "X")
        self.ce.compute()
        self.assertEqual(len(self.ce.history), 1)

    def test_dissent_tracking(self):
        self.ce.cast_vote("Alice", "Innovator", "v3", score=0.9)
        self.ce.cast_vote("Bob", "Devil's Advocate", "v2", score=-0.5)
        result = self.ce.majority_vote()
        self.assertIn("Bob", result.dissent)


class TestReverseIdeation(unittest.TestCase):
    """Test ReverseIdeation flow."""

    def setUp(self):
        self.ri = ReverseIdeation(topic="Edge computing")

    def test_propose_solution(self):
        sol = self.ri.propose_solution("ISA v3 encoding", "Alice", "Innovator")
        self.assertEqual(sol.content, "ISA v3 encoding")
        self.assertEqual(len(self.ri.solutions), 1)

    def test_identify_problem(self):
        sol = self.ri.propose_solution("ISA v3", "Alice", "Innovator")
        prob = self.ri.identify_problem(
            "High bandwidth cost", sol.id, "Bob", "Pragmatist",
            severity=0.8, likelihood=0.7
        )
        self.assertEqual(prob.severity, 0.8)
        self.assertEqual(prob.solution_id, sol.id)

    def test_get_problems_for_solution(self):
        sol = self.ri.propose_solution("ISA v3", "Alice")
        self.ri.identify_problem("Problem A", sol.id, "Bob")
        self.ri.identify_problem("Problem B", sol.id, "Carol")
        problems = self.ri.get_problems_for_solution(sol.id)
        self.assertEqual(len(problems), 2)

    def test_validation(self):
        sol = self.ri.propose_solution("ISA v3", "Alice")
        prob = self.ri.identify_problem("Bandwidth", sol.id, "Bob")
        val = self.ri.validate(sol.id, prob.id, "Carol", "Analyst", is_valid=True, confidence=0.9)
        self.assertTrue(val.is_valid)
        self.assertEqual(val.confidence, 0.9)

    def test_rank_solutions(self):
        s1 = self.ri.propose_solution("ISA v3", "Alice")
        self.ri.identify_problem("P1", s1.id, "Bob", severity=0.9, likelihood=0.8)
        self.ri.identify_problem("P2", s1.id, "Carol", severity=0.7, likelihood=0.6)
        self.ri.validate(s1.id, self.ri.get_problems_for_solution(s1.id)[0].id, "Dave", confidence=0.9, is_valid=True)

        s2 = self.ri.propose_solution("ISA v2", "Eve")
        ranked = self.ri.rank_solutions()
        self.assertEqual(len(ranked), 2)
        # s1 should rank higher (more problems, higher severity)
        self.assertEqual(ranked[0][0].content, "ISA v3")

    def test_top_solution(self):
        s1 = self.ri.propose_solution("A", "Alice")
        self.ri.identify_problem("P1", s1.id, "Bob", severity=0.9, likelihood=0.9)
        top = self.ri.get_top_solution()
        self.assertIsNotNone(top)
        self.assertEqual(top[0].content, "A")

    def test_top_solution_empty(self):
        self.assertIsNone(self.ri.get_top_solution())

    def test_summary(self):
        s = self.ri.summary()
        self.assertEqual(s["topic"], "Edge computing")
        self.assertEqual(s["solutions"], 0)

    def test_severity_likelihood_clamped(self):
        sol = self.ri.propose_solution("X", "A")
        prob = self.ri.identify_problem("Y", sol.id, "B", severity=5.0, likelihood=-1.0)
        self.assertEqual(prob.severity, 1.0)
        self.assertEqual(prob.likelihood, 0.0)


class TestSession(unittest.TestCase):
    """Test Session recording and replay."""

    def setUp(self):
        self.recorder = SessionRecorder()
        self.session = self.recorder.start_session(topic="Test topic")

    def test_start_session(self):
        self.assertIsNotNone(self.session.session_id)
        self.assertEqual(self.session.topic, "Test topic")
        self.assertEqual(self.session.event_count, 1)  # session_start event

    def test_record_event(self):
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "Innovator", {"content": "Hello"})
        self.assertEqual(self.session.event_count, 2)

    def test_end_session(self):
        self.recorder.end_session(self.session.session_id)
        self.assertIsNotNone(self.session.ended_at)
        self.assertTrue(self.session.duration > 0)

    def test_duration_before_end(self):
        dur = self.session.duration
        self.assertTrue(dur >= 0)

    def test_filter_by_type(self):
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "R", {"content": "A"})
        self.recorder.record_event(self.session.session_id, "vote", "Bob", "R", {"position": "X"})
        contributes = self.session.get_events_by_type("contribute")
        self.assertEqual(len(contributes), 1)

    def test_filter_by_participant(self):
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "R", {})
        self.recorder.record_event(self.session.session_id, "contribute", "Bob", "R", {})
        alice_events = self.session.get_events_by_participant("Alice")
        self.assertEqual(len(alice_events), 1)

    def test_to_json_roundtrip(self):
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "R", {"content": "Test"})
        self.recorder.end_session(self.session.session_id)
        json_str = self.session.to_json()
        restored = Session.from_json(json_str)
        self.assertEqual(restored.session_id, self.session.session_id)
        self.assertEqual(len(restored.events), len(self.session.events))

    def test_export_import(self):
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "R", {"content": "Test"})
        exported = self.recorder.export_session(self.session.session_id)
        self.assertIn("Test", exported)

        new_recorder = SessionRecorder()
        imported = new_recorder.import_session(exported)
        self.assertEqual(imported.topic, "Test topic")


class TestSessionReplay(unittest.TestCase):
    """Test SessionReplay functionality."""

    def setUp(self):
        self.recorder = SessionRecorder()
        self.session = self.recorder.start_session(topic="Replay test")
        self.recorder.record_event(self.session.session_id, "contribute", "Alice", "Innovator", {"content": "First"})
        self.recorder.record_event(self.session.session_id, "contribute", "Bob", "Pragmatist", {"content": "Second"})
        self.recorder.record_event(self.session.session_id, "vote", "Carol", "Analyst", {"position": "X"})
        self.recorder.end_session(self.session.session_id)
        self.replay = SessionReplay(self.session)

    def test_initial_state(self):
        self.assertFalse(self.replay.is_complete)
        self.assertEqual(self.replay.progress, 0.0)

    def test_next_advances(self):
        # First event is session_start (no participant), advance past it
        self.replay.next()
        e = self.replay.next()
        self.assertEqual(e.participant, "Alice")
        self.assertEqual(self.replay.progress, 2 / 5)

    def test_peek_does_not_advance(self):
        # First event is session_start (no participant), peek at second
        self.replay.next()  # advance past session_start
        e = self.replay.peek()
        self.assertEqual(e.participant, "Alice")
        self.assertEqual(self.replay.progress, 1 / 5)

    def test_replay_all(self):
        all_events = self.replay.replay_all()
        # session_start + 3 events + session_end = 5
        self.assertEqual(len(all_events), 5)
        self.assertTrue(self.replay.is_complete)

    def test_reset(self):
        self.replay.next()
        self.replay.next()
        self.replay.reset()
        self.assertEqual(self.replay.progress, 0.0)

    def test_replay_by_type(self):
        contributes = self.replay.replay_by_type("contribute")
        self.assertEqual(len(contributes), 2)

    def test_get_transcript(self):
        transcript = self.replay.get_transcript()
        self.assertIn("Replay test", transcript)
        self.assertIn("Alice", transcript)
        self.assertIn("Duration:", transcript)


class TestRoundTable(unittest.TestCase):
    """Integration tests for the RoundTable orchestrator."""

    def setUp(self):
        self.table = RoundTable("Should we use ISA v2 or v3?")

    def test_initial_state(self):
        self.assertEqual(self.table.topic, "Should we use ISA v2 or v3?")
        self.assertEqual(self.table.phase, DiscussionPhase.SETUP)
        self.assertTrue(self.table.is_active)

    def test_add_role(self):
        self.table.add_role(Role.INNOVATOR)
        self.assertIn("Innovator", self.table.get_participants())

    def test_add_role_custom_name(self):
        self.table.add_role(Role.DEVILS_ADVOCATE, "Zara")
        self.assertIn("Zara", self.table.get_participants())

    def test_add_participant(self):
        self.table.add_participant("Alice", Role.ANALYST)
        self.assertEqual(self.table.role_assignment.get_role("Alice"), Role.ANALYST)

    def test_remove_participant(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.remove_participant("Innovator")
        self.assertNotIn("Innovator", self.table.get_participants())

    def test_contribute(self):
        self.table.add_role(Role.INNOVATOR)
        arg = self.table.contribute("Innovator", "v3 is the future")
        self.assertEqual(arg.content, "v3 is the future")
        self.assertEqual(self.table.tracker.total_arguments, 1)

    def test_contribute_with_type(self):
        self.table.add_role(Role.PRAGMATIST)
        arg = self.table.contribute("Pragmatist", "Is it tested?", arg_type="question")
        self.assertEqual(arg.argument_type, ArgumentType.QUESTION)

    def test_ask_question(self):
        self.table.add_role(Role.ANALYST)
        arg = self.table.ask_question("Analyst", "What are the benchmarks?")
        self.assertEqual(arg.argument_type, ArgumentType.QUESTION)

    def test_provide_evidence(self):
        self.table.add_role(Role.ANALYST)
        arg = self.table.provide_evidence("Analyst", "Benchmark shows 40% improvement")
        self.assertEqual(arg.argument_type, ArgumentType.EVIDENCE)
        self.assertEqual(arg.weight, 1.5)

    def test_counter_argument(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.add_role(Role.DEVILS_ADVOCATE)
        a1 = self.table.contribute("Innovator", "v3 is great")
        a2 = self.table.counter("Devil's Advocate", "v3 has bugs", a1.id)
        self.assertEqual(a2.argument_type, ArgumentType.COUNTER)
        self.assertEqual(a2.parent_id, a1.id)

    def test_cast_vote_and_consensus(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.add_role(Role.PRAGMATIST)
        self.table.cast_vote("Innovator", "Use v3", score=0.9)
        self.table.cast_vote("Pragmatist", "Use v3", score=0.6)
        result = self.table.get_consensus()
        self.assertEqual(result.winner, "Use v3")
        self.assertEqual(self.table.phase, DiscussionPhase.CONSENSUS)

    def test_auto_assign_roles(self):
        participants = ["Alice", "Bob", "Carol"]
        self.table.auto_assign_roles(participants)
        self.assertEqual(len(self.table.get_participants()), 3)

    def test_close(self):
        self.table.close()
        self.assertEqual(self.table.phase, DiscussionPhase.CLOSED)
        self.assertFalse(self.table.is_active)

    def test_reverse_ideation_integration(self):
        self.table.add_role(Role.INNOVATOR)
        sol = self.table.propose_solution("Innovator", "ISA v3 encoding")
        prob = self.table.identify_problem("Innovator", sol.id, "Bandwidth costs", severity=0.8)
        self.assertEqual(len(self.table.reverse_ideation.solutions), 1)
        self.assertEqual(len(self.table.reverse_ideation.problems), 1)

    def test_get_transcript(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.contribute("Innovator", "Hello world")
        transcript = self.table.get_transcript()
        self.assertIn("Hello world", transcript)

    def test_export_session(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.contribute("Innovator", "Test")
        exported = self.table.export_session()
        self.assertIsNotNone(exported)
        data = json.loads(exported)
        self.assertEqual(data["topic"], "Should we use ISA v2 or v3?")

    def test_summary(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.contribute("Innovator", "Hello")
        s = self.table.summary()
        self.assertEqual(s["topic"], "Should we use ISA v2 or v3?")
        self.assertEqual(s["total_arguments"], 1)
        self.assertEqual(s["phase"], "setup")

    def test_recording_disabled(self):
        table = RoundTable("Test", enable_recording=False)
        table.add_role(Role.INNOVATOR)
        table.contribute("Innovator", "Hello")
        self.assertIsNone(table.export_session())

    def test_get_arguments(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.contribute("Innovator", "A")
        self.table.contribute("Innovator", "B")
        self.assertEqual(len(self.table.get_arguments()), 2)

    def test_get_arguments_by_participant(self):
        self.table.add_role(Role.INNOVATOR)
        self.table.add_role(Role.PRAGMATIST)
        self.table.contribute("Innovator", "A")
        self.table.contribute("Pragmatist", "B")
        self.assertEqual(len(self.table.get_arguments_by_participant("Innovator")), 1)

    def test_full_roundtrip_example(self):
        """Full roundtrip: setup -> contribute -> vote -> consensus."""
        table = RoundTable("Microservices vs Monolith?")

        table.add_role(Role.DEVILS_ADVOCATE, "Zara")
        table.add_role(Role.INNOVATOR, "Max")
        table.add_role(Role.PRAGMATIST, "Sam")
        table.add_role(Role.VISIONARY, "Lee")
        table.add_role(Role.ANALYST, "Pat")

        table.contribute("Max", "Microservices scale independently")
        table.contribute("Zara", "Network latency adds 15ms per hop", arg_type="con")
        table.contribute("Sam", "Our team is 5 people - ops overhead is real", arg_type="con")
        table.contribute("Lee", "In 3 years we'll need multi-region deployment")
        table.provide_evidence("Pat", "Industry data: 60% of startups over-engineer with microservices")

        table.cast_vote("Max", "Microservices", 0.9, "Best for scale")
        table.cast_vote("Zara", "Monolith", -0.3, "Too risky now")
        table.cast_vote("Sam", "Monolith", 0.4, "Pragmatic choice")
        table.cast_vote("Lee", "Microservices", 0.6, "Future-proof")
        table.cast_vote("Pat", "Monolith", 0.7, "Data says stay simple")

        result = table.get_consensus()

        self.assertEqual(result.winner, "Monolith")
        self.assertEqual(len(table.get_arguments()), 5)
        self.assertTrue(table.tracker.total_arguments > 0)
        self.assertTrue(result.summary != "")
        table.close()


if __name__ == "__main__":
    unittest.main()
