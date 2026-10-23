# Repository structure

This is the cleaned tree on `cleanup/deepagent-only`. The [file manifest](MIGRATION_MANIFEST.md) lists every retained path, and [migration notes](MIGRATION_NOTES.md) explain branch reconciliation and removals.

| Area | Paths | Purpose |
| --- | ---: | --- |
| `src/agents/` | 112 | Agent registry, prompts, tools, DeepAgent coding worker, and external-agent adapters |
| `src/graph/` | 8 | LangGraph orchestration, state handling, routing, and UI events |
| `src/server/` | 18 | FastAPI service, routes, sessions, persistence, usage tracking, and streaming |
| `src/frontend/` | 57 | React/Vite interface and its frontend test |
| `src/optimizer/` | 7 | Session-driven skill/plan optimizer and guardrails |
| Other `src/` modules | 7 | CLI, model/provider selection, configuration, logging, and shared settings |
| `benchmark/` | 259 | BioMysteryBench, Spatial CellBench, CCC optimizer, hypothesis-recovery fixtures, scoring, and references |
| `demo/` | 70 | Example notebooks, small reference data, and hypothesis-recovery runner/scorer |
| `knowledge/` | 52 | Domain skill cards and executable scripts, plans, and reference docs |
| `tests/` | 29 | Python regression and integration checks |
| `docs/`, `site/`, root docs | 21 | Architecture, integration, Docker/R, migration, and public site material |
| Root support, `docker/`, `workspace/` | 14 | Dependency locks, environment definitions, Docker image, and empty workspace placeholders |

The main execution path is `src/cli.py` or `src/server/main.py` → `src/graph/graph.py` → agents in `src/agents/agent_defns.py` → an agent's tools. The coding worker is `src/agents/agent_registry/coding_agent/model.py`, built with DeepAgent. It uses `knowledge/skills/` through `src/agents/skills_workspace.py`. When a step is assigned `r-execution`, the R tool starts the gateway in `src/agents/agent_registry/coding_agent/kernel.py` on demand. Ordinary coding steps use DeepAgent's local shell execution and start no gateway.

The API serves the React app in `src/frontend/` and stores runtime data under `workspace/`. `workspace/library/` contains shared inputs; `workspace/project/` holds the active project's uploads and outputs. Parked projects live under the repository-root `projects/` directory. Only placeholder files are versioned there. The `site/` directory is a separate static informational site.

External adapters for CellVoyager, GeneAgent, and GeneGPT live under `src/agents/agent_registry/`. Each adapter's `upstream` path is a pinned git submodule, not vendored code. Their upstream trees must be initialized before running those integrations or their dependent tests.

`pyproject.toml` and `uv.lock` define the Python package; `src/frontend/package.json` and its lockfile define the web app. `flake.nix` and `environment.yml` provide alternative development environments. `docker/Dockerfile` supports the optional R kernel container. `README.md`, `INTEGRATING.md`, and `DOCKER.md` explain user setup and integration points.
