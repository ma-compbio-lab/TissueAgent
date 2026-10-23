"""CellVoyager and its analysis kernel must use the active TissueAgent environment."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from agents.agent_registry.cellvoyager_agent import runner


def test_import_probe_reports_missing_dependencies(monkeypatch):
    """An old installation gets actionable instructions for its own environment."""
    def probe(command, **kwargs):
        assert command[0] == sys.executable
        assert kwargs["cwd"] == str(runner._UPSTREAM_DIR)
        return subprocess.CompletedProcess(command, 1, "", "No module named 'instructor'")

    monkeypatch.setattr(runner.subprocess, "run", probe)
    with pytest.raises(RuntimeError, match="uv sync --frozen") as error:
        runner._check_environment()
    assert sys.executable in str(error.value)
    assert "instructor" in str(error.value)


@pytest.mark.parametrize("provider,override,expected", [
    ("OPENAI_API_KEY", None, "gpt-4o"),
    ("ANTHROPIC_API_KEY", None, "claude-sonnet-4-6"),
    ("OPENAI_API_KEY", "custom-model", "custom-model"),
])
def test_subprocess_uses_active_python_without_conda(
    monkeypatch, tmp_path, provider, override, expected,
):
    """Exercise a real child process, artifact collection, and kernel discovery."""
    upstream = tmp_path / "upstream with spaces"
    upstream.mkdir()
    (upstream / "cellvoyager.py").write_text("# Import probe fixture\n")
    script = upstream / "run_cellvoyager.py"
    script.write_text('''
import argparse
import json
import sys
from pathlib import Path
from jupyter_client.kernelspec import KernelSpecManager

parser = argparse.ArgumentParser()
parser.add_argument('--output-home')
args, _ = parser.parse_known_args()
root = Path(args.output_home)
root.joinpath('runtime.json').write_text(json.dumps({
    'python': sys.executable,
    'kernel': KernelSpecManager().get_kernel_spec('python3').argv[0],
}))
root.joinpath('analysis.ipynb').write_text(json.dumps({'cells': [
    {'cell_type': 'markdown', 'source': ['## Hypothesis: example']},
    {'cell_type': 'code', 'source': ['print(1)']},
]}))
''')
    # A conflicting user kernel must not override the per-run interpreter.
    other_data = tmp_path / "other-jupyter"
    other_kernel = other_data / "kernels" / "python3"
    other_kernel.mkdir(parents=True)
    (other_kernel / "kernel.json").write_text(json.dumps({
        "argv": ["/wrong/environment/python", "-m", "ipykernel_launcher"],
        "display_name": "Wrong environment", "language": "python",
    }))
    monkeypatch.setenv("JUPYTER_PATH", str(other_data))
    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv(provider, "test-only-not-a-key")
    monkeypatch.setattr(runner, "_UPSTREAM_DIR", upstream)
    monkeypatch.setattr(runner, "_CLI_SCRIPT", script)
    monkeypatch.setattr(runner, "DATA_DIR", tmp_path / "workspace")
    import config
    monkeypatch.setattr(config, "active_project_outputs", lambda: tmp_path / "outputs")

    dataset = tmp_path / "dataset.h5ad"
    dataset.touch()
    result = runner.run_cellvoyager_analysis(
        str(dataset), "Example biological context", "test-analysis",
        model_name=override, request_id="test-run",
    )

    assert result["returncode"] == 0, result["stderr_tail"]
    run_dir = Path(result["run_directory"])
    runtime = json.loads((run_dir / "runtime.json").read_text())
    assert runtime == {"python": sys.executable, "kernel": sys.executable}
    assert result["model_used"] == expected
    assert result["hypotheses"][0]["header"] == "## Hypothesis: example"
    assert Path(result["staged_suggestions_path"]).is_file()
    # No global environment changes or provider credentials in the kernelspec.
    assert os.environ["JUPYTER_PATH"] == str(other_data)
    assert "test-only-not-a-key" not in (
        run_dir / "jupyter" / "kernels" / "python3" / "kernel.json"
    ).read_text()
