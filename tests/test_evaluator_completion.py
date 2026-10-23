"""Offline checks for task-independent completion and bounded evaluator routing."""

import os
from pathlib import Path
import sys
import unittest
from copy import deepcopy
from datetime import datetime
from unittest.mock import Mock

os.environ.setdefault("OPENAI_API_KEY", "unit-test")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from langchain_core.messages import AIMessage

from agents.evaluator_agent.validation import (
    create_evaluator_state_update,
    guard_plan_completion_verdict,
)
from server.plan_store import PlanDocument, PlanStep


class CompletionTests(unittest.TestCase):
    """Final success requires terminal steps, independently of task or specialist."""

    def test_unfinished_steps_block_success_for_any_task(self):
        for status in ("pending", "running", "failed"):
            for agent, skills in (
                (None, []),
                ("coding_agent", ["figure-reproduce"]),
                ("cell_annotator_agent", ["tissue-niche-annotation"]),
            ):
                with self.subTest(status=status, agent=agent):
                    plan = PlanDocument(steps=[
                        PlanStep(id=1, title="Generate outputs", status="done"),
                        PlanStep(id=2, title="Verify results", status=status,
                                 assigned_agent=agent, skills=skills),
                        PlanStep(id=3, title="Optional formatting", status="skipped"),
                    ])
                    before = deepcopy(plan)
                    result = guard_plan_completion_verdict(
                        "ROUTE: REPORT\nThe output file exists", plan
                    )
                    self.assertTrue(result.startswith("ROUTE: REPLAN"), result)
                    self.assertIn(f"Step 2: Verify results ({status})", result)
                    self.assertNotIn("Step 1:", result)
                    self.assertNotIn("Step 3:", result)
                    self.assertIn("Preserve existing artifacts", result)
                    self.assertEqual(plan, before)

    def test_multiple_unfinished_steps_are_reported(self):
        plan = PlanDocument(steps=[
            PlanStep(id=3, title="Analyze", status="failed"),
            PlanStep(id=7, title="Validate", status="pending"),
        ])
        result = guard_plan_completion_verdict("  route: report\nDone", plan)
        self.assertIn("Step 3: Analyze (failed)", result)
        self.assertIn("Step 7: Validate (pending)", result)

    def test_empty_completed_and_deliberately_skipped_plans_are_allowed(self):
        content = "ROUTE: REPORT\nCompleted with minor presentation limitations"
        for statuses in ([], ["done"], ["done", "skipped"], ["skipped"]):
            with self.subTest(statuses=statuses):
                plan = PlanDocument(steps=[
                    PlanStep(id=i, title="Task", status=status)
                    for i, status in enumerate(statuses, 1)
                ])
                self.assertEqual(guard_plan_completion_verdict(content, plan), content)

    def test_non_success_assessments_are_preserved(self):
        plan = PlanDocument(steps=[PlanStep(id=1, title="Task")])
        for content in ("ROUTE: REPLAN\nScientifically incorrect result", "", "Inspecting"):
            self.assertEqual(guard_plan_completion_verdict(content, plan), content)


class EvaluatorStateTests(unittest.TestCase):
    """Completion policy must not bypass tools, replan limits, or static-plan mode."""

    def setUp(self):
        self.plan_reader = Mock(return_value=PlanDocument(steps=[
            PlanStep(id=1, title="Validate results", status="pending"),
        ]))

    def callback(self, *, allow_replanning=True, max_replans=2):
        return create_evaluator_state_update(
            self.plan_reader,
            allow_targeted_replanning=allow_replanning,
            max_replans=max_replans,
        )

    def test_final_report_reads_current_plan_and_requests_replan(self):
        response = AIMessage(content="ROUTE: REPORT\nDone")
        state = {"replan_count": 0, "replan_history": ["earlier"]}
        update = self.callback()(response, state)
        self.assertTrue(response.content.startswith("ROUTE: REPLAN"))
        self.assertEqual(update["replan_count"], 1)
        self.assertEqual(update["replan_history"][0], "earlier")
        self.assertIsNotNone(datetime.fromisoformat(update["replan_history"][1]).tzinfo)
        self.assertEqual(state["replan_history"], ["earlier"])
        self.plan_reader.assert_called_once_with()

    def test_completed_report_needs_no_replan(self):
        self.plan_reader.return_value.steps[0].status = "done"
        content = "ROUTE: REPORT\nResults validated"
        response = AIMessage(content=content)
        self.assertEqual(self.callback()(response, {}), {})
        self.assertEqual(response.content, content)

    def test_tool_calls_are_not_final_verdicts(self):
        for route in ("REPORT", "REPLAN"):
            with self.subTest(route=route):
                content = f"ROUTE: {route}\nInspecting evidence"
                response = AIMessage(content=content, tool_calls=[{
                    "name": "read", "args": {"path": "results.json"}, "id": "read-1",
                }])
                self.assertEqual(self.callback()(response, {"replan_count": 0}), {})
                self.assertEqual(response.content, content)
        self.plan_reader.assert_not_called()

    def test_existing_replan_feedback_is_preserved(self):
        content = "ROUTE: REPLAN\nEVALUATION: Incorrect analysis"
        response = AIMessage(content=content)
        update = self.callback()(response, {"replan_count": 1})
        self.assertEqual(update["replan_count"], 2)
        self.assertEqual(response.content, content)
        self.plan_reader.assert_not_called()

    def test_cap_uses_persisted_count_or_message_history(self):
        for state in (
            {"replan_count": 2},
            {"messages": [
                AIMessage(content="ROUTE: REPLAN\nBlocker", name="evaluator_agent"),
                AIMessage(content="ROUTE: REPLAN\nStill blocked", name="evaluator_agent"),
            ]},
        ):
            with self.subTest(state=state):
                response = AIMessage(content="ROUTE: REPORT\nDone")
                update = self.callback()(response, state)
                self.assertEqual(update["replan_count"], 3)
                self.assertTrue(response.content.startswith("ROUTE: REPORT"))
                self.assertIn("Replan limit reached (maximum 2)", response.content)
                self.assertIn("unresolved blockers", response.content)
                self.assertIn("Step 1: Validate results (pending)", response.content)
                self.assertNotIn("ROUTE: REPLAN", response.content)

    def test_disabled_replanning_reports_limitations_without_counting(self):
        for content, blocker in (
            ("ROUTE: REPORT\nDone", "Step 1: Validate results (pending)"),
            ("ROUTE: REPLAN\nEVALUATION: Missing evidence", "Missing evidence"),
        ):
            with self.subTest(content=content):
                response = AIMessage(content=content)
                self.assertEqual(self.callback(allow_replanning=False)(response, {}), {})
                self.assertTrue(response.content.startswith("ROUTE: REPORT"))
                self.assertIn("Targeted replanning is disabled", response.content)
                self.assertIn("do not present this as successful completion", response.content)
                self.assertIn(blocker, response.content)
                self.assertNotIn("ROUTE: REPLAN", response.content)

    def test_non_verdict_does_not_read_plan_or_increment_count(self):
        response = AIMessage(content="No final verdict available")
        self.assertEqual(self.callback()(response, {}), {})
        self.plan_reader.assert_not_called()


if __name__ == "__main__":
    unittest.main()
