"""Exercise context recovery with real provider exceptions and a running toy graph."""

import copy

import anthropic
import httpx
import openai
import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from graph.context_recovery import (
    compact_context,
    invoke_with_context_recovery,
    is_context_overflow,
)


def _error(provider=openai, text="maximum context length exceeded", code=None):
    """Build the SDK error shape without making any network requests."""
    response = httpx.Response(
        400, request=httpx.Request("POST", "https://api.example.com/messages")
    )
    return provider.BadRequestError(
        text, response=response, body={"error": {"message": text, "code": code}}
    )


class _Model:
    """Record actual model inputs and return scripted failures or responses."""

    def __init__(self, outcomes):
        self.outcomes = iter(outcomes)
        self.inputs = []

    def invoke(self, messages):
        self.inputs.append(copy.deepcopy(messages))
        outcome = next(self.outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _exchange(call_id, content="start\n" + "x" * 20000 + "\nproject/outputs/result.csv"):
    """Build a paired exchange with a long result and intact tool arguments."""
    return [
        AIMessage(content="", tool_calls=[{
            "id": call_id, "name": "read", "args": {"path": "project/outputs/result.csv"},
        }]),
        ToolMessage(content=content, tool_call_id=call_id),
    ]


@pytest.mark.parametrize("error", [
    _error(code="context_length_exceeded", text="provider-specific detail"),
    _error(),
    _error(anthropic, "prompt is too long: 210000 tokens > 200000 maximum"),
    _error(text="Input is too long for this model"),
])
def test_recognizes_explicit_overflow(error):
    """Both providers' explicit context overflow formats are recognized."""
    assert is_context_overflow(error)


@pytest.mark.parametrize("error", [
    _error(text="tool messages must follow a matching tool call"),
    _error(text="max_tokens exceeds the maximum output tokens"),
    _error(anthropic, "Image exceeds maximum image dimensions"),
    ValueError("maximum context length exceeded"),
])
def test_unrelated_errors_propagate_without_retry(error):
    """A similar phrase or another bad request must not cause destructive pruning."""
    model = _Model([error])
    with pytest.raises(type(error)) as caught:
        invoke_with_context_recovery(model, _exchange("a"), node_name="test")
    assert caught.value is error
    assert len(model.inputs) == 1


def test_success_preserves_exact_input():
    """Healthy calls never prune their context."""
    messages = [SystemMessage(content="policy"), HumanMessage(content="task"), *_exchange("a")]
    model = _Model([AIMessage(content="ok")])
    invoke_with_context_recovery(model, messages, node_name="manager")
    assert model.inputs == [messages]


def test_recovers_and_preserves_requirements_plan_tool_pair_and_full_trace():
    """An overflow can recover while current plan and historical messages remain intact."""
    protected = [
        SystemMessage(content="system policy and current plan " * 1000),
        HumanMessage(content="original task with all requirements " * 1000),
        AIMessage(content="current JSON plan " * 1000, name="planner_agent"),
        AIMessage(content="current assignments " * 1000, name="recruiter_agent"),
        AIMessage(content="latest failure assessment " * 1000, name="evaluator_agent"),
    ]
    messages = [*protected, *_exchange("old"), *_exchange("recent")]
    original = copy.deepcopy(messages)
    model = _Model([_error(), AIMessage(content="recovered")])
    result = invoke_with_context_recovery(model, messages, node_name="evaluator")
    assert result.content == "recovered"
    assert messages == original
    retry = model.inputs[1]
    assert retry[:len(protected)] == protected
    assert retry[-2].tool_calls == messages[-2].tool_calls
    assert retry[-1].tool_call_id == "recent"
    assert len(retry[-1].content) < len(messages[-1].content)
    assert retry[-1].content.endswith("project/outputs/result.csv")
    assert "Middle omitted" in retry[-1].content
    assert not any(isinstance(m, ToolMessage) and m.tool_call_id == "old" for m in retry)


def test_parallel_tools_are_removed_together_and_recent_pair_is_retained():
    """Compaction never leaves orphaned results or drops only one parallel result."""
    calls = [{"id": i, "name": "read", "args": {"path": i}} for i in ("a", "b")]
    messages = [
        HumanMessage(content="task"),
        AIMessage(content="read", tool_calls=calls),
        ToolMessage(content="a" * 5000, tool_call_id="b"),
        ToolMessage(content="b" * 5000, tool_call_id="a"),
        *_exchange("c"),
    ]
    compacted = compact_context(messages)
    assert compacted is not None
    assert [m.tool_call_id for m in compacted if isinstance(m, ToolMessage)] == ["c"]
    assert [call["id"] for m in compacted if isinstance(m, AIMessage)
            for call in m.tool_calls] == ["c"]


def test_multimodal_results_keep_images_and_do_not_mutate_blocks():
    """Only text is clipped; image evidence and the source blocks survive."""
    blocks = [
        {"type": "text", "text": "x" * 20000},
        {"type": "image_url", "image_url": {"url": "data:image/png;base64,abc"}},
    ]
    messages = _exchange("a", blocks)
    original = copy.deepcopy(messages)
    compacted = compact_context(messages)
    assert compacted[-1].content[1] == blocks[1]
    assert len(compacted[-1].content[0]["text"]) < len(blocks[0]["text"])
    assert messages == original


def test_incomplete_tool_exchange_is_not_removed():
    """Recovery does not remove a call that has unmatched results."""
    missing = AIMessage(content="", tool_calls=[
        {"id": i, "name": "read", "args": {}} for i in ("a", "b")
    ])
    messages = [missing, ToolMessage(content="x" * 20000, tool_call_id="a"), *_exchange("c")]
    compacted = compact_context(messages)
    assert compacted[0] == missing
    assert compacted[1].tool_call_id == "a"


def test_retry_budget_is_bounded_and_each_input_is_smaller():
    """Repeated overflows cause at most two smaller retries, then retain the error."""
    failures = [_error(), _error(), _error()]
    model = _Model(failures)
    with pytest.raises(openai.BadRequestError) as caught:
        invoke_with_context_recovery(model, _exchange("a"), node_name="manager")
    assert caught.value is failures[-1]
    assert len(model.inputs) == 3
    lengths = [len(messages[-1].content) for messages in model.inputs]
    assert lengths[0] > lengths[1] > lengths[2]


def test_unshrinkable_instructions_fail_without_repeating_same_request():
    """Large protected content must not be silently truncated or retried unchanged."""
    messages = [SystemMessage(content="policy " * 10000), HumanMessage(content="task " * 10000)]
    model = _Model([_error()])
    with pytest.raises(openai.BadRequestError):
        invoke_with_context_recovery(model, messages, node_name="planner")
    assert len(model.inputs) == 1


def test_node_retry_does_not_reexecute_tool_or_update_state_twice(monkeypatch):
    """A real graph recovers the model call and keeps the full tool output in state."""
    from langchain_core.tools import StructuredTool
    from langgraph.graph import END, START, MessagesState, StateGraph

    from graph import node_factories

    monkeypatch.setattr(node_factories, "emit_message", lambda *_: None)
    monkeypatch.setattr(node_factories, "pop_completed_subagent", lambda: None)
    monkeypatch.setattr(node_factories.usage_tracker, "record_llm_call", lambda *_: None)
    executed = []
    updates = []

    def read(path: str) -> str:
        executed.append(path)
        return "evidence " * 4000

    def update(response, state):
        updates.append(response)
        return {}

    model = _Model([_exchange("a")[0], _error(), AIMessage(content="done")])
    graph = StateGraph(MessagesState)
    graph.add_node("agent", node_factories.create_agent_node(
        "agent", model, "system instructions", "tools", END, state_update_fn=update,
    ))
    graph.add_node("tools", node_factories.create_tool_node([
        StructuredTool.from_function(read, description="Read test evidence"),
    ]))
    graph.add_edge(START, "agent")
    graph.add_edge("tools", "agent")
    result = graph.compile().invoke({"messages": [HumanMessage(content="task")]})
    assert executed == ["project/outputs/result.csv"]
    assert len(updates) == 2  # first tool request and final answer; no failed-turn update
    assert result["messages"][-1].content == "done"
    assert result["messages"][2].content == "evidence " * 4000
    assert len(model.inputs) == 3
    assert len(model.inputs[-1][-1].content) < len(result["messages"][2].content)
