# Migration notes

This cleanup is on branch `cleanup/deepagent-only` of the legacy repository. Its `main` ref is unchanged and no cleanup commit was created. The six edits that were present before branching were incorporated where the corresponding files remain. The cleaned tree was copied to `../TissueAgent` without a new commit. The complete path inventory is in [MIGRATION_MANIFEST.md](MIGRATION_MANIFEST.md).

## Branch reconciliation

- `main` is the base. Its four external-agent submodule pointers remain pinned; run `git submodule update --init --recursive` to populate them when needed.
- `optimizer-ccc-benchmark` (including its `ccc-ensemdble` ancestor) supplied the optimizer package, CCC scoring runner and references, CLI subcommand, docs, and relevant tests. Generated optimizer runs, reports, installed R packages, and duplicate CCC skill documents were omitted. Production recursion and replanning defaults were restored after the experimental benchmark overrides.
- `r-demo` supplied the `r-execution` skill and opt-in R tool. The shared R kernel gateway is retained and now starts only when an R-enabled step runs.
- `test` supplied the separate hypothesis-recovery fixture cards, runner, and scorer. Archived shortcut runs and generated results were omitted.
- `origin/cell-annotation`, `origin/hypothesis-recovery-prototype`, and `origin/revision` were reviewed against `main`. Their surviving agent, UI, and workflow features are already represented by newer implementations on `main`; old generated outputs, archived experiments, and superseded source were omitted.
- `deepagent`, `reproduce+apply`, `scmultisim-ccc-task`, and the remaining remote merge/topic tips add no live implementation beyond the selected tree or contain older versions of it.

## Cleanup

The manual LangGraph coding-agent implementation and its stock-versus-DeepAgent ablation runner were removed. DeepAgent is the sole coding-agent implementation. Its prompt now describes the tools it actually has. The R kernel, notebook log, and image spill utilities moved under the canonical coding-agent package because R-enabled steps still use them. The Docker setting and docs now describe only R kernel execution.

Generated benchmark run trees, demo outputs, cached skills, frontend icon backups, obsolete tests, duplicate skill documents, and a worktree-specific file were omitted. Tracked Spatial CellBench fixtures and demo inputs were retained so the benchmarks and notebooks remain reproducible. The external-agent submodules remain pinned; their source code is not vendored. Tests that require an uninitialized submodule skip explicitly.

## Estimated overhead avoided

The removed manual-agent directory portion accounts for **69 tracked paths, 366,942 bytes, and 851 Python source lines** after excluding the three utilities retained for R. The comparison runner removes another **347 lines**. This is a source/maintenance reduction, not a claim of faster DeepAgent inference: the manual agent was already inactive by default. Previously the app started a Jupyter Kernel Gateway at every CLI/server startup; now runs with no R step start **zero** gateways. That saves one gateway process and its startup work per such run. Exact memory and startup-time savings depend on the host and were not benchmarked.

## Validation

The Python suite passed in the legacy working tree with 235 tests passed and 2 skipped. In the transferred repository, 232 tests passed and 5 skipped: two require the uninitialized GeneGPT submodule, and three require a local archived session fixture that was intentionally not transferred. Frontend TypeScript checking and the production build passed in the legacy working tree. No end-to-end agent run was performed because it requires credentials and external data.
