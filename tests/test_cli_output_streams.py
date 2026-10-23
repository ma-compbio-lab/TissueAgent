"""The documented CLI output must be usable in shell pipelines."""

import json
import threading
from queue import Queue

import pytest
from langchain_core.messages import AIMessage

import cli


def test_streamed_messages_and_tool_calls_use_stderr(capsys):
    """Tracing must not contaminate redirected answer output."""
    events = Queue()
    events.put(("message", AIMessage(
        content="Working on the analysis",
        tool_calls=[{"id": "call-1", "name": "read", "args": {"path": "input.csv"}}],
    )))
    stopped = threading.Event()
    stopped.set()
    cli._drain_trace(events, stopped, quiet=False)
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Working on the analysis" in captured.err
    assert "read(path)" in captured.err


@pytest.mark.parametrize("flags", [[], ["--quiet"], ["--json"]])
def test_final_output_has_no_status_banners(monkeypatch, capsys, flags):
    """Both text and JSON output stay machine-readable regardless of trace mode."""
    result = {"answer": "TISSUEAGENT_READY", "artifacts": [], "project_id": "test"}
    monkeypatch.setattr(cli, "run", lambda prompt, args: result)
    assert cli.main([*flags, "test prompt"]) == 0
    captured = capsys.readouterr()
    if "--json" in flags:
        assert json.loads(captured.out) == result
    else:
        assert captured.out == "TISSUEAGENT_READY\n"
