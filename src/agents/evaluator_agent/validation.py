"""Task-independent completion checks and bounded evaluator feedback."""

from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage

from graph.replan_state import effective_replan_count
from server.plan_store import PlanDocument


def guard_plan_completion_verdict(content: str, plan: PlanDocument) -> str:
    """Prevent success while planned work remains unfinished.

    Completed and deliberately skipped steps are terminal. This checks recorded
    execution status only; the Evaluator still assesses artifacts and scientific
    correctness. Neither status nor artifact existence alone proves correctness.
    """
    if not content.lstrip().upper().startswith("ROUTE: REPORT"):
        return content
    unfinished = [step for step in plan.steps if step.status not in {"done", "skipped"}]
    if not unfinished:
        return content
    descriptions = "; ".join(
        f"Step {step.id}: {step.title} ({step.status})" for step in unfinished
    )
    return (
        "ROUTE: REPLAN\n\n"
        f"EVALUATION: The plan still contains unfinished work: {descriptions}.\n\n"
        "FEEDBACK: Preserve existing artifacts and completed work. Check execution evidence "
        "and reconcile stale plan statuses before repeating any analysis. Complete and verify "
        "the outstanding required work; explicitly mark an unnecessary step skipped with a "
        "reason. Do not mark a step done merely because an output file exists, or claim "
        "completion while required work remains unresolved."
    )


def _report_unresolved(content: str, reason: str) -> str:
    """Forward unresolved feedback to reporting without a success claim."""
    assessment = content.partition("\n")[2].strip()
    return (
        "ROUTE: REPORT\n\n"
        f"EVALUATION: {reason} Returning partial results with unresolved blockers.\n\n"
        "NOTE: Disclose the incomplete work and limitations in the final report; "
        "do not present this as successful completion.\n\n"
        + assessment
    )


def create_evaluator_state_update(
    plan_reader: Callable[[], PlanDocument],
    *,
    allow_targeted_replanning: bool,
    max_replans: int,
) -> Callable[[AIMessage, dict[str, Any]], dict[str, Any]]:
    """Build the final-verdict callback, keeping evaluation policy out of the graph."""

    def evaluator_state_update(response: AIMessage, state: dict[str, Any]) -> dict[str, Any]:
        # Tool-use turns are evidence gathering, not final verdicts.
        if response.tool_calls:
            return {}
        content = (response.content or "").strip()
        if content.upper().startswith("ROUTE: REPORT"):
            content = guard_plan_completion_verdict(content, plan_reader())
            response.content = content
        head = content.splitlines()[0].upper() if content else ""
        if not head.startswith("ROUTE: REPLAN"):
            return {}
        if not allow_targeted_replanning:
            response.content = _report_unresolved(content, "Targeted replanning is disabled.")
            return {}

        new_count = effective_replan_count(state) + 1
        history = list(state.get("replan_history", []))
        history.append(datetime.now(timezone.utc).isoformat())
        if new_count > max_replans:
            response.content = _report_unresolved(
                content, f"Replan limit reached (maximum {max_replans})."
            )
        return {"replan_count": new_count, "replan_history": history}

    return evaluator_state_update
