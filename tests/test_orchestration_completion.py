"""Run the production specialist graph offline through completion and replan limits."""

from dataclasses import replace
import json
from queue import Queue

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool
import pytest

from graph import graph as pipeline


class FakeModel(FakeMessagesListChatModel):
    """Serve fresh messages on repeated calls without a provider or network."""

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, *args, **kwargs):
        result = super()._generate(*args, **kwargs)
        for generation in result.generations:
            generation.message = generation.message.model_copy(deep=True)
        return result


@pytest.mark.parametrize("execute_work", [True, False])
def test_specialist_pipeline_finishes_or_preserves_unfinished_feedback(
    tmp_path, monkeypatch, execute_work,
):
    """Real routing retains counters and reports incomplete work at the configured cap."""
    monkeypatch.setattr(pipeline.plan_store, "_dir", tmp_path / "plan")
    monkeypatch.setattr(pipeline, "MAX_REPLANS", 1)
    dispatched = []

    def create_worker(state_queue, context_resolver=None):
        def work(prompt: str) -> str:
            """Complete the isolated test task."""
            dispatched.append(prompt)
            return "The requested work is complete."
        return StructuredTool.from_function(work)

    worker = pipeline.CustomAgent(
        id="test_worker", name="Test worker", description="Complete the test task",
        ctor=create_worker,
    )
    plan = {
        "steps": [{"step_number": 1, "title": "Complete required work",
                   "description": "Execute the test task", "reasoning": "Required",
                   "expected_artifacts": []}],
        "provenance": {"template_names": [], "justification": "A simple test task"},
    }
    assignments = {"assignments": [{"step_id": 1, "assigned_agent": "test_worker_agent",
                                    "assignment_rationale": "Available worker", "skills": []}]}
    manager = []
    if execute_work:
        for call_id in ("dispatch", "accept"):
            manager.append(AIMessage(content="", tool_calls=[{
                "id": call_id, "name": "next_step", "args": {"task_instructions": "Do the work"},
            }]))
    manager.append(AIMessage(content="Ready for evaluation"))
    replies = {
        "PlannerAgent": [AIMessage(content="ROUTE: PLAN\n```json\n" + json.dumps(plan) + "\n```")],
        "RecruiterAgent": [AIMessage(content="```json\n" + json.dumps(assignments) + "\n```")],
        "ManagerAgent": manager,
        "EvaluatorAgent": [AIMessage(content="ROUTE: REPORT\nEVALUATION: complete")],
        "ReporterAgent": [AIMessage(content="Report the supplied evaluation")],
    }
    for name, responses in replies.items():
        monkeypatch.setattr(pipeline, name, replace(
            getattr(pipeline, name),
            model_ctor=lambda responses=responses: FakeModel(responses=responses),
        ))
    graph = pipeline.create_tissueagent_graph(
        Queue(), lambda model: model, domain_agents=[worker],
    ).compile()
    state = graph.invoke(
        {"messages": [HumanMessage(content="Execute the required test task")],
         "replan_count": 0, "replan_history": []},
        {"recursion_limit": 60},
    )
    verdicts = [m.content for m in state["messages"] if m.name == "evaluator_agent"]
    assert state["messages"][-1].name == "reporter_agent"
    if execute_work:
        assert len(dispatched) == 1
        assert pipeline.plan_store.read().steps[0].status == "done"
        assert state["replan_count"] == 0
        assert len(verdicts) == 1
    else:
        assert not dispatched
        assert pipeline.plan_store.read().steps[0].status == "pending"
        assert state["replan_count"] == 2
        assert len(state["replan_history"]) == 2
        assert verdicts[0].startswith("ROUTE: REPLAN")
        assert verdicts[-1].startswith("ROUTE: REPORT")
        assert "Replan limit reached" in verdicts[-1]
        assert "Complete required work (pending)" in verdicts[-1]
