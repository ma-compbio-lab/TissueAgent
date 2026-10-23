# Repository structure

For installation and interface choices, start with the [root README](../README.md). This guide maps the source code and generated runtime files.

## Source and documentation

| Path | Purpose |
| --- | --- |
| `src/cli.py` | Installed `tissueagent` command and module entry point; also invoked by the Lohoff notebooks |
| `src/server/` | FastAPI service, project persistence, routes, usage tracking, and streaming |
| `src/frontend/` | React/Vite Web UI; its built `dist/` directory is served by the backend |
| `src/graph/` | LangGraph workflow, state handling, routing, and UI events |
| `src/agents/` | Agent definitions, prompts, tools, skill assignment, and external-agent adapters |
| `src/optimizer/` | Session-driven skill and plan optimization with guardrails |
| `src/config.py`, `src/models.py` | Runtime paths and settings, model catalog, and provider selection |
| `knowledge/` | Domain plans, skill instructions, executable scripts, and reference documentation |
| `demo/` | Example notebooks, reference inputs, and notebook utilities; see the [demo guide](../demo/README.md) |
| `tests/` | Python regression and integration checks |
| `docs/` | Architecture, workflow guides, and historical migration notes |
| `site/` | Separate informational website |
| `docker/` | Optional R kernel container image |

The main execution path is `src/cli.py` or `src/server/main.py` → `src/graph/graph.py` → agents registered in `src/agents/agent_defns.py` → each agent's tools. All three user interfaces share this workflow.

The coding worker in `src/agents/agent_registry/coding_agent/model.py` uses DeepAgent and local shell execution. Skills under `knowledge/skills/` are made available through `src/agents/skills_workspace.py`. When a step is assigned `r-execution`, the R tool starts the gateway in `src/agents/agent_registry/coding_agent/kernel.py` on demand. See [DOCKER.md](../DOCKER.md) for local and containerized R setup.

## Dependencies and external agents

| File | Role |
| --- | --- |
| `pyproject.toml`, `uv.lock`, `.python-version` | Python package, locked dependencies, and Python version |
| `environment.yml` | Conda environment for TissueAgent |
| `flake.nix`, `flake.lock` | Nix development toolchain |
| `src/frontend/package.json`, `src/frontend/package-lock.json` | Frontend scripts and dependencies |
| `.gitmodules` | Pinned external-agent submodule locations |

Adapters for **GeneAgent**, **GeneGPT**, and **CellVoyager** live under `src/agents/agent_registry/`. Each adapter's `upstream/` directory is a pinned Git submodule. Initialize these sources before using the integrations or running tests that depend on them. CellVoyager additionally requires its own Conda environment. See [external-agent setup](../README.md#external-agents) for installation and verification, and [INTEGRATING.md](../INTEGRATING.md) for adapter development.

## Generated state and outputs

By default, the state root is the repository root. Set `TISSUEAGENT_STATE_ROOT` before starting a process to relocate its mutable state; the source code and knowledge assets remain in the checkout.

```text
<state root>/
├── workspace/
│   ├── library/
│   │   ├── datasets/       # shared reference datasets
│   │   └── files/          # shared reference files
│   ├── project/           # one active project
│   │   ├── .project_id
│   │   ├── .chat.json
│   │   ├── uploads/       # project-specific inputs
│   │   ├── outputs/       # generated artifacts
│   │   └── skills/        # assigned skill snapshots
│   └── notebook/          # process-wide notebook scratch
├── projects/<id>/         # parked projects
├── plan_scratch/          # in-flight plans
├── logs/                  # runtime logs
└── sessions/              # legacy session storage, migrated at startup
```

Agents access shared library inputs as read-only files. Switching projects parks the previous project outside `workspace/` and activates the selected one under `workspace/project/`. External-agent adapters also retain tool-specific artifacts; CellVoyager keeps its upstream runs under `workspace/cellvoyager_agent/`.

The Lohoff notebooks configure an isolated state root inside each run directory. Figures 2b, 2d, and 2e retain reports, figures, tables, logs, executed notebook copies, and runtime state under `cached/`; figures 2a and 2c use `demo/outputs/`. Both directories are Git-ignored. Notebook backups are retained under `cached/notebook_backups/`. See the [demo guide](../demo/README.md#lohoff-figure-reproduction-inputs-and-outputs) for cache reuse and input validation.

For state isolation, concurrent processes, and output locations, see [runtime configuration](../README.md#state-and-output-locations). Runtime files and retained demo results are generated locally; they are not required in a fresh clone.
