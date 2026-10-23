"""Regression coverage for GeneAgent's legacy verification-tool dispatch."""

from types import SimpleNamespace
from copy import deepcopy
from pathlib import Path
import ast
import json
import re
import pytest

from openai.types.chat import ChatCompletion

from agents.llm_compat import _build_legacy_chat_completion


def legacy_message(message: dict):
    response = ChatCompletion(
        id="test", object="chat.completion", created=0, model="test",
        choices=[{"index": 0, "finish_reason": "stop", "message": message}],
    )
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
        create=lambda **kwargs: response,
    )))
    return _build_legacy_chat_completion(client, "test").create().choices[0]["message"]


def test_verification_tool_call_survives_legacy_adapter():
    message = legacy_message({
        "role": "assistant", "content": None,
        "function_call": {
            "name": "get_gene_summary_for_single_gene",
            "arguments": '{"gene_name":"DES"}',
        },
    })
    assert "function_call" in message
    assert message["function_call"] == {
        "name": "get_gene_summary_for_single_gene",
        "arguments": '{"gene_name":"DES"}',
    }


def test_text_report_does_not_enter_legacy_tool_dispatch():
    message = legacy_message({
        "role": "assistant", "content": "Report: Evidence is inconclusive.",
        "function_call": None,
    })
    assert "function_call" not in message
    assert message["content"] == "Report: Evidence is inconclusive."


@pytest.mark.parametrize("retain_assistant", [True, False])
def test_repeated_tool_exchanges_preserve_arguments_and_caller_history(retain_assistant):
    requests = []
    functions = [
        {"name": "gene_summary", "arguments": json.dumps({"gene": gene})}
        for gene in ("DES", "ACTA2")
    ]

    def create(**kwargs):
        requests.append(deepcopy(kwargs))
        message = {"role": "assistant", "content": "Done"}
        if len(requests) <= len(functions):
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call_{len(requests)}", "type": "function",
                "function": functions[len(requests) - 1],
            }]}
        return ChatCompletion(id="test", object="chat.completion", created=0,
                              model="test", choices=[{
                                  "index": 0, "finish_reason": "stop", "message": message,
                              }])

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    shim = _build_legacy_chat_completion(client, "test")
    history = [{"role": "user", "content": "Check these genes."}]
    for index in range(3):
        before = deepcopy(history)
        reply = shim.create(messages=history).choices[0]["message"]
        assert history == before
        if index < len(functions):
            if retain_assistant:
                history.append(reply)
            history.append({"role": "function", "name": "gene_summary",
                            "content": f"evidence {index}"})

    modern_history = requests[-1]["messages"]
    assert len(modern_history) == 5
    for index, function in enumerate(functions):
        call = modern_history[1 + 2 * index]["tool_calls"][0]
        result = modern_history[2 + 2 * index]
        assert call["function"] == function
        assert result == {"role": "tool", "tool_call_id": call["id"],
                          "content": f"evidence {index}"}


@pytest.mark.parametrize("invalid_history", ["separate_conversation", "edited_prefix", "wrong_tool"])
def test_omitted_call_recovery_rejects_unrelated_history(invalid_history):
    response = ChatCompletion(id="test", object="chat.completion", created=0,
                              model="test", choices=[{
                                  "index": 0, "finish_reason": "stop", "message": {
                                      "role": "assistant", "content": None, "tool_calls": [{
                                          "id": "call_test", "type": "function", "function": {
                                              "name": "gene_summary", "arguments": '{"gene":"DES"}',
                                          },
                                      }],
                                  },
                              }])
    requests = []

    def create(**kwargs):
        requests.append(kwargs)
        return response

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    shim = _build_legacy_chat_completion(client, "test")
    history = [{"role": "user", "content": "Check DES."}]
    shim.create(messages=history)
    if invalid_history == "separate_conversation":
        history = deepcopy(history)
    elif invalid_history == "edited_prefix":
        history[0]["content"] = "Check something else."
    history.append({"role": "function",
                    "name": "other_tool" if invalid_history == "wrong_tool" else "gene_summary",
                    "content": "evidence"})
    with pytest.raises(ValueError, match="missing its preceding assistant call"):
        shim.create(messages=history)
    assert len(requests) == 1


def test_upstream_verifier_completes_modern_tool_round_trip():
    """Run the actual upstream verifier with deterministic API/tool responses."""
    requests = []
    tool_inputs = []

    def create(**kwargs):
        requests.append(kwargs)
        if len(requests) == 1:
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": "call_test", "type": "function", "function": {
                    "name": "get_gene_summary_for_single_gene",
                    "arguments": json.dumps({"gene_name": "DES", "specie": "Homo"}),
                },
            }]}
        else:
            message = {"role": "assistant", "content": "Report: Evidence retrieved."}
        return ChatCompletion(id="test", object="chat.completion", created=0,
                              model="test", choices=[{
                                  "index": 0, "finish_reason": "stop", "message": message,
                              }])

    def gene_summary(**kwargs):
        tool_inputs.append(kwargs)
        return {"summary": "test evidence"}

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    tool_name = "get_gene_summary_for_single_gene"
    tool_doc = {"name": tool_name, "parameters": {"type": "object", "properties": {}}}
    namespace = {
        "openai": SimpleNamespace(ChatCompletion=_build_legacy_chat_completion(client, "test")),
        "time": SimpleNamespace(sleep=lambda _: None), "json": json, "re": re,
        "pattern": re.compile(r"^[a-zA-Z0-9_-]+$"),
        "encoding": SimpleNamespace(encode=lambda text: text.split()),
        "func2info": {tool_name: [gene_summary, tool_doc]},
    }
    # Load only AgentPhD, avoiding import-time Azure assignments and unrelated APIs.
    source = Path(__file__).resolve().parents[1] / "src/agents/agent_registry/gene_agent/upstream/worker.py"
    if not source.is_file():
        pytest.skip("GeneAgent submodule is not initialized; restore external submodules first")
    tree = ast.parse(source.read_text())
    verifier = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "AgentPhD")
    exec(compile(ast.Module(body=[verifier], type_ignores=[]), str(source), "exec"), namespace)
    report = namespace["AgentPhD"]([tool_name]).inference("DES has a known gene function.")
    assert report.startswith("Evidence retrieved")
    assert tool_inputs == [{"gene_name": "DES", "specie": "Homo"}]
    assert len(requests) == 2
    assert requests[0]["tools"] == [{"type": "function", "function": tool_doc}]
    assert requests[0]["parallel_tool_calls"] is False
    assert "functions" not in requests[0]
    history = requests[1]["messages"]
    call = history[-2]["tool_calls"][0]
    assert call["function"]["name"] == tool_name
    assert history[-1]["role"] == "tool"
    assert history[-1]["tool_call_id"] == call["id"]
    assert "test evidence" in history[-1]["content"]
