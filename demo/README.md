# Demo notebooks

This folder contains notebooks for several tasks described in the manuscript. Each notebook is self-contained and can be run end-to-end to load inputs, prompt the agent, and save outputs.

## Run a notebook

The commands below use macOS/Linux shells. On Windows, [install Ubuntu with WSL first](../README.md#windows-install-ubuntu-first) and run them in the Ubuntu terminal.

1. Follow the root README's [installation instructions](../README.md#installation). Choose uv, Conda + uv, or Nix + uv; all three support notebooks.

2. From the repository root, activate that environment: `source .venv/bin/activate` for uv or Nix + uv (inside `nix develop`), or `conda activate tissueagent` for Conda.

3. Configure [provider credentials](../README.md#credentials-and-models) before starting Jupyter. The default model needs `OPENAI_API_KEY`. Some tasks also need [external-agent environments](../README.md#external-agents) or [task-specific tools](../README.md#task-specific-dependencies).

4. Start Jupyter with `python -m notebook`. Select a kernel from the environment where TissueAgent is installed; see [kernel registration and verification](../README.md#notebook).

5. Open a notebook and review its inputs, model, prompt, and output directory before running it top to bottom. Included reference inputs are in `demo/data/`; each notebook specifies its dataset requirements. Lohoff Fig. 2b, 2d, and 2e retain runs under the repository's `cached/{TASK}/`, while Fig. 2a and 2c use `demo/outputs/`. The Lohoff runs record a `transcript.log` alongside their results.

Saved figures and reports can be viewed without executing the notebooks. Fresh agent runs need credentials and make model calls; their results can vary between runs. See the cache behavior below before rerunning a completed example.

For interactive projects or terminal workflows, see the root README's [Web UI](../README.md#web-ui) and [CLI](../README.md#cli) instructions.

## Included examples

```
demo
├── data/                                # datasets and inputs for demo tasks
├── figure_recreation_lohoff-2a.ipynb    # atlas and seqFISH joint UMAP figure reproduction
├── figure_recreation_lohoff-2b.ipynb    # notebook for figure recreation task (Figure 2b from Lohoff et. al.)
├── figure_recreation_lohoff-2c.ipynb    # germ-layer spatial panels
├── figure_recreation_lohoff-2d.ipynb    # spatial contact-probability heatmap
├── figure_recreation_lohoff-2e.ipynb    # notebook for figure recreation task (Figure 2e from Lohoff et. al.)
├── spot_deconvolution_visium_heart.ipynb    # notebook for cell-type deconvolution task
├── notebook_utils.py                    # utility functions for setting up and running TissueAgent in notebooks
└── README.md
```

## Lohoff figure reproduction inputs and outputs

The Fig. 2a–2e notebooks share `data/dataset_lohoff_et_al_seqfish.h5ad`.
Their reference images and instructions are included in `data/`, including the Fig. 2e
reference and methodology. Generated runs remain local under `demo/outputs/` or
the repository's Git-ignored `cached/` directory.

The [Fig. 2a notebook](figure_recreation_lohoff-2a.ipynb) reproduces both the
Gastrulation atlas and seqFISH panels using `gastrulation_atlas_joint_umap.csv`
and `seqfish_author_joint_umap.csv`. These contain published processed coordinates
and annotations, not raw atlas expression. Use both CSV coordinate systems together;
the shared AnnData's UMAP is a different embedding. See
[`instructions_lohoff-2a.md`](data/instructions_lohoff-2a.md) and
[`provenance_lohoff-2a.json`](data/provenance_lohoff-2a.json) for source details and checksums.

The notebook verifies input hashes before execution. It expects 16,861 atlas cells
and 52,568 seqFISH cells after excluding `Low quality` labels. Saved notebook outputs
include the executed example's final figure and data checks. Executing the notebook
needs credentials and makes model calls unless a completed local result matches the
model, prompt, and input hashes. Generated run directories remain local.

The [Fig. 2c notebook](figure_recreation_lohoff-2c.ipynb) recreates the three germ-layer
panels and verifies all 19,416 cells and their original spatial coordinates in each
panel. Both notebooks display the explicitly named `final_figure.png`, so diagnostic
plots cannot be mistaken for the final result. Reports document approximate colors
and, for Fig. 2c, the scale calibration inferred from the reference image.

The [Fig. 2b](figure_recreation_lohoff-2b.ipynb),
[Fig. 2d](figure_recreation_lohoff-2d.ipynb), and
[Fig. 2e](figure_recreation_lohoff-2e.ipynb) notebooks display their final figure,
validate the underlying data tables, and render `reports/reproduction_report.md`.
Their `cached/{TASK}/` directories retain figures, tables, reports, execution state,
runtime caches, logs, and an `executed_notebook.ipynb` copy. Existing runs are not
deleted: a completed run is reused only when its model, prompt, and input hashes
match; otherwise choose a new output directory. Backups of the notebooks before
this rerun are retained in `cached/notebook_backups/`.

The shared data lacks the original segmentation polygons and neighbor graph.
Fig. 2d and 2e therefore reconstruct neighborhoods from spatial coordinates and
document the approximation and statistical choices in their reports. Their
computed values and category order can differ from the published panels.

## Tissue-niche baselines

For named annotation with TissueAgent, Biomni and SpatialAgent, use the
[agent benchmark guide](../docs/tissue_niche_agent_baselines.md) and
[agent notebook](tissue_niche_agent_baselines.ipynb). The workflow covers heart MERFISH and
SpatialFusion Xenium OVCA with matched inputs/prompts, configurable models (GPT-5.1 by default),
macro F1/balanced accuracy, and spatial/performance plots. LLMiniST is deferred.

## Web UI demonstration

https://github.com/user-attachments/assets/ef381418-cf5c-431b-9052-f931c922d2c8
