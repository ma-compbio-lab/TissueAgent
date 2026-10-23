"""Provider-valid histories must retain paired tools and the current plan."""

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from graph.message_filters import (
    filter_for_manager,
    filter_for_recruiter,
    find_last_planner_final_content,
)


def _call(name, call_id):
    return AIMessage(
        content="Inspecting", name=name,
        tool_calls=[{"id": call_id, "name": "read", "args": {"path": "skill.md"}}],
    )


def test_planner_tool_call_does_not_replace_last_final_plan():
    messages = [AIMessage(content="Final plan", name="planner_agent"),
                _call("planner_agent", "read-plan")]
    assert find_last_planner_final_content(messages) == "Final plan"


def test_recruiter_keeps_its_current_tool_exchange_only():
    task = HumanMessage(content="Analyze the data")
    old = _call("recruiter_agent", "old")
    planner_read = _call("planner_agent", "template")
    plan = AIMessage(content="Revised plan", name="planner_agent")
    current = _call("recruiter_agent", "current")
    result = ToolMessage(content="Skill content", tool_call_id="current")
    messages = [task, old, ToolMessage(content="Old skill", tool_call_id="old"),
                planner_read, ToolMessage(content="Template", tool_call_id="template"),
                plan, current, result]
    assert filter_for_recruiter(messages) == [task, plan, current, result]


def test_manager_retains_user_anchor_and_only_current_paired_tools():
    current = _call("manager_agent", "current")
    result = ToolMessage(content="Result", tool_call_id="current")
    messages = [_call("manager_agent", "old"),
                ToolMessage(content="Old result", tool_call_id="old"),
                AIMessage(content="New assignments", name="recruiter_agent"),
                current, result, ToolMessage(content="Unrelated", tool_call_id="other")]
    filtered = filter_for_manager("manager_agent")(messages)
    assert isinstance(filtered[0], HumanMessage)
    assert filtered[1:] == [current, result]
