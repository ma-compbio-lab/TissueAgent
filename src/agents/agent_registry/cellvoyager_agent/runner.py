"""Adapter that runs upstream CellVoyager from inside TissueAgent.

CellVoyager exposes its entry point as a CLI (`run_cellvoyager.py`) rather
than a clean library API, so the simplest and most maintainable integration
is to invoke that CLI as a subprocess from the upstream directory. This keeps
us decoupled from any internal API churn in the upstream package and matches
the way the upstream is intended to be run.

The subprocess:
  - Sets CWD to the pinned upstream submodule (so its relative paths resolve).
  - Writes the biological-background text into the run directory.
  - Uses TissueAgent's Python interpreter with `--execution-mode legacy`.
  - Pins the analysis kernel to that same interpreter through a run-local
    Jupyter kernelspec; no separately activated environment is needed.
  - Routes outputs to `workspace/cellvoyager_agent/<request_id>/`.
  - Parses generated notebooks and returns a structured result.

The model follows the available provider credentials unless the caller
overrides it via `model_name=`.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# These imports come from the parent TissueAgent app, not the upstream
# CellVoyager submodule.
from config import DATA_DIR

_HERE = Path(__file__).resolve().parent
_UPSTREAM_DIR = _HERE / "upstream"
_CLI_SCRIPT = _UPSTREAM_DIR / "run_cellvoyager.py"


def _check_upstream() -> None:
    if not _UPSTREAM_DIR.is_dir():
        raise RuntimeError(
            f"CellVoyager upstream not found at {_UPSTREAM_DIR}. "
            "Run `git submodule update --init --recursive` from the repo root."
        )
    if not _CLI_SCRIPT.is_file():
        raise RuntimeError(
            f"CellVoyager CLI script missing: {_CLI_SCRIPT}. The upstream "
            "submodule appears corrupted."
        )


def _check_environment() -> None:
    """Verify the active TissueAgent interpreter can import the upstream."""
    # The upstream isn't a pip-installed package; it's a folder containing a
    # `cellvoyager` directory. Python finds it via cwd lookup, so we run the
    # probe with cwd set to the upstream directory (matches how the real
    # subprocess below invokes it).
    probe = subprocess.run(
        [sys.executable, "-c", "import cellvoyager"],
        cwd=str(_UPSTREAM_DIR),
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if probe.returncode != 0:
        raise RuntimeError(
            f"TissueAgent's Python ({sys.executable}) cannot import CellVoyager. "
            "Update this environment from the repository root with "
            "`uv sync --frozen` or `python -m pip install -e .`. "
            f"Probe stderr:\n{probe.stderr[-500:]}"
        )


def _subprocess_environment(run_dir: Path) -> dict[str, str]:
    """Keep upstream Python commands and its notebook kernel in this environment."""
    # Upstream requests the generic `python3` kernel. A user's global kernelspec
    # can point at another environment, even when the CLI uses sys.executable.
    # JUPYTER_PATH takes precedence without changing the user's kernel registry.
    jupyter_dir = run_dir / "jupyter"
    kernel_dir = jupyter_dir / "kernels" / "python3"
    kernel_dir.mkdir(parents=True, exist_ok=True)
    (kernel_dir / "kernel.json").write_text(
        json.dumps({
            "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
            "display_name": "TissueAgent (CellVoyager)",
            "language": "python",
        }) + "\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    for key, prefix in (
        ("PATH", str(Path(sys.executable).parent)),
        ("JUPYTER_PATH", str(jupyter_dir.resolve())),
    ):
        env[key] = prefix + (os.pathsep + env[key] if env.get(key) else "")
    return env


def _check_api_keys() -> None:
    """At least one of (OPENAI, ANTHROPIC) must be present for CellVoyager."""
    if not (os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")):
        raise RuntimeError(
            "Neither OPENAI_API_KEY nor ANTHROPIC_API_KEY is set; "
            "CellVoyager cannot run."
        )


def _parse_notebook_for_findings(notebook_path: Path) -> list[dict]:
    """Extract the agent-generated analysis cells from CellVoyager's notebook.

    CellVoyager writes markdown cells containing hypothesis statements above
    each code cell. We scan markdown cells whose first line mentions
    `Analysis` or `Hypothesis` and pair them with the next code cell.
    """
    if not notebook_path.is_file():
        return []
    try:
        nb = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    findings: list[dict] = []
    pending_header: Optional[str] = None
    for cell in nb.get("cells", []):
        src = "".join(cell.get("source", []))
        first_line = src.splitlines()[0] if src.splitlines() else ""
        if cell.get("cell_type") == "markdown" and (
            "Analysis" in first_line or "Hypothesis" in first_line
        ):
            pending_header = src
        elif cell.get("cell_type") == "code" and pending_header is not None:
            findings.append({"header": pending_header.strip(), "code_excerpt": src[:500]})
            pending_header = None
    return findings


def _resolve_h5ad_path(h5ad_path: str) -> Path:
    """Resolve agent-supplied h5ad paths to a real host file.

    Agents often pass container-style or workspace-relative paths
    (``/mnt/data/...``, ``/workspace/...``, ``library/datasets/foo.h5ad``).
    CellVoyager runs in the host's TissueAgent environment, so those must be mapped onto
    :data:`config.DATA_DIR`.
    """
    from config import DATA_DIR, DATASET_DIR

    raw = Path(h5ad_path)
    candidates: list[Path] = []
    if raw.is_absolute():
        candidates.append(raw)
        # Strip common container / mount prefixes → DATA_DIR-relative.
        for prefix in ("/mnt/data", "/workspace", "/data"):
            try:
                rel = raw.relative_to(prefix)
            except ValueError:
                continue
            candidates.append(DATA_DIR / rel)
            break
    else:
        candidates.append(Path.cwd() / raw)
        candidates.append(DATA_DIR / raw)
        if str(raw).startswith("library/datasets/"):
            candidates.append(DATA_DIR / raw)
        candidates.append(DATASET_DIR / raw.name)

    # Always try the basename under the curated dataset dir.
    candidates.append(DATASET_DIR / raw.name)

    seen: set[str] = set()
    for c in candidates:
        key = str(c)
        if key in seen:
            continue
        seen.add(key)
        try:
            resolved = c.resolve()
        except OSError:
            continue
        if resolved.is_file():
            return resolved

    raise FileNotFoundError(
        f"h5ad file not found: {h5ad_path}. Tried: {[str(c) for c in candidates]}"
    )


def run_cellvoyager_analysis(
    h5ad_path: str,
    background_text: str,
    analysis_name: str,
    num_analyses: int = 1,
    max_iterations: int = 6,
    model_name: Optional[str] = None,
    request_id: Optional[str] = None,
) -> dict:
    """Run CellVoyager on a single dataset + background-text pair.

    Args:
        h5ad_path: Path to the AnnData file (absolute host path preferred;
            workspace-relative and ``/mnt/data`` / ``/workspace`` prefixes are
            resolved automatically).
        background_text: Biological context the agent should see. In a
            recovery-benchmark run this is the LIMITED background with the
            target claim withheld.
        analysis_name: Short snake-case name for this run (becomes a
            sub-folder name).
        num_analyses: How many independent analyses CellVoyager should
            propose. Default 1 (fastest); 3–5 is typical for benchmarks.
        max_iterations: Max self-refinement iterations per analysis.
        model_name: Override the manifest's pinned model. Default uses
            CellVoyager's own default (claude-sonnet-4-6).
        request_id: Optional identifier for the run artifact directory.

    Returns:
        A dict with keys:
          - request_id, run_directory, model_used
          - notebook_path (str or None if not produced)
          - hypotheses: list of {header, code_excerpt}
          - stdout_tail: last ~50 lines of CellVoyager output
          - stderr_tail: last ~20 lines of CellVoyager stderr
          - returncode: subprocess exit code (0 = success)
    """
    _check_upstream()
    _check_environment()
    _check_api_keys()

    h5ad_path_p = _resolve_h5ad_path(h5ad_path)
    if not background_text.strip():
        raise ValueError("background_text must be non-empty.")

    # Upstream defaults to Claude; fall back to gpt-4o when only OpenAI is configured
    # (matches the CellVoyager-alone benchmark arm).
    if not model_name:
        if os.environ.get("ANTHROPIC_API_KEY"):
            model_name = None  # upstream default (claude-sonnet-4-6)
        elif os.environ.get("OPENAI_API_KEY"):
            model_name = "gpt-4o"
        else:
            model_name = "gpt-4o"

    run_identifier = request_id or datetime.now(timezone.utc).strftime(
        "run_%Y%m%d_%H%M%S"
    )
    run_dir = DATA_DIR / "cellvoyager_agent" / run_identifier
    run_dir.mkdir(parents=True, exist_ok=True)

    background_path = run_dir / "background.txt"
    background_path.write_text(background_text, encoding="utf-8")

    # Use the exact interpreter running TissueAgent, regardless of shell PATH
    # or whether the user installed with uv, pip, Conda, or Nix.
    cmd = [
        sys.executable, str(_CLI_SCRIPT),
        "--h5ad-path", str(h5ad_path_p),
        "--paper-path", str(background_path),
        "--analysis-name", analysis_name,
        "--execution-mode", "legacy",
        "--num-analyses", str(num_analyses),
        "--max-iterations", str(max_iterations),
        "--output-home", str(run_dir),
        "--log-home", str(run_dir / "logs"),
        "--no-vlm",  # skip the OpenAI VLM step to keep dependencies minimal
    ]
    if model_name:
        cmd.extend(["--model-name", model_name])

    proc = subprocess.run(
        cmd,
        cwd=str(_UPSTREAM_DIR),
        capture_output=True,
        text=True,
        env=_subprocess_environment(run_dir),
        check=False,
        timeout=14400,  # 4h hard cap for full-size ST (Nature Methods rebuttal: no subsample)
    )

    stdout_tail = "\n".join(proc.stdout.splitlines()[-50:])
    stderr_tail = "\n".join(proc.stderr.splitlines()[-20:])

    # CellVoyager writes one notebook per analysis under
    # <output_home>/<analysis_name>/<analysis_name>_analysis_{1,2,3,...}.ipynb.
    # We aggregate findings across ALL produced notebooks; otherwise a
    # num_analyses > 1 run would be undersampled.
    candidates = sorted(run_dir.rglob("*.ipynb"))
    notebook_path = str(candidates[0].resolve()) if candidates else None
    findings: list[dict] = []
    for nb in candidates:
        for h in _parse_notebook_for_findings(nb):
            h["source_notebook"] = nb.name
            findings.append(h)

    result = {
        "request_id": run_identifier,
        "run_directory": str(run_dir.resolve()),
        "model_used": model_name or "claude-sonnet-4-6",
        "notebook_path": notebook_path,
        "hypotheses": findings,
        "stdout_tail": stdout_tail,
        "stderr_tail": stderr_tail,
        "returncode": proc.returncode,
    }

    # Materialize findings into the active TissueAgent project so manager
    # heuristic validation can see workspace-relative artifacts.
    try:
        from config import active_project_outputs

        out = active_project_outputs()
        hyp_dir = out / "hypotheses"
        hyp_dir.mkdir(parents=True, exist_ok=True)
        suggestions = []
        for i, h in enumerate(findings, start=1):
            suggestions.append(
                {
                    "id": f"CV{i}",
                    "statement": (h.get("header") or "").strip(),
                    "code_excerpt": (h.get("code_excerpt") or "")[:4000],
                    "source_notebook": h.get("source_notebook"),
                }
            )
        suggestion_path = hyp_dir / "cellvoyager_suggestions.json"
        suggestion_path.write_text(
            json.dumps(
                {
                    "returncode": proc.returncode,
                    "upstream_run_directory": str(run_dir.resolve()),
                    "notebook_path": notebook_path,
                    "suggestions": suggestions,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        log_path = hyp_dir / "exploration_log.md"
        lines = [
            "",
            "## OBSERVATION_CV — CellVoyager submodule proposals",
            "",
            f"CellVoyager run `{run_identifier}` (returncode={proc.returncode}).",
            "Treat the following as candidate analysis directions to synthesize "
            "with TissueAgent observations.",
            "",
        ]
        if not suggestions:
            lines.append("- (No parseable hypotheses; see upstream run_directory.)")
        for s in suggestions:
            lines.append(f"- **{s['id']}**: {(s['statement'] or '(no header)')[:500]}")
        lines.append("")
        with log_path.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))
        result["staged_suggestions_path"] = str(suggestion_path)
        result["staged_exploration_log"] = str(log_path)
    except Exception as e:
        result["staging_error"] = str(e)

    return result
