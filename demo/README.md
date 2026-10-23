

# Demo

This folder contains notebooks for several tasks described in the manuscript. Each notebook is self-contained and can be run end-to-end to load inputs, prompt the agent, and save outputs.

### Usage

1. Set up the repository (see [README.md](../README.md))

2. Run source `.venv/bin/activate` to activate the virtual environment created by `uv`

3. Export your LLM credentials. At minimum `OPENAI_API_KEY` must be set for the default agents to function (e.g. `export OPENAI_API_KEY="sk-..."`).

4. Start a jupyter server with `jupyter notebook`.

5. Open a notebook and run it top-to-bottom to reproduce a task. Data can be accessed in `demo/data` and outputs are written to `workspace/` and copied into `demo/outputs/{TASK}`. The run is logged to `demo/outputs/{TASK}/transcript.log`.

> [!WARNING]
> LLM outputs are inherently stochastic, so TissueAgent may produce slightly different outputs between runs.

### Structure
```
demo
├── data/                                # datasets and inputs for demo tasks
├── figure_recreation_lohoff-2a.ipynb    # atlas and seqFISH joint UMAP figure reproduction
├── figure_recreation_lohoff-2b.ipynb    # notebook for figure recreation task (Figure 2b from Lohoff et. al.)
├── figure_recreation_lohoff-2e.ipynb    # notebook for figure recreation task (Figure 2e from Lohoff et. al.)
├── spot_deconvolution_visium_heart.ipynb    # notebook for cell-type deconvolution task
├── notebook_utils.py                    # utility functions for setting up and running TissueAgent in notebooks
└── README.md
```

### Lohoff figure reproduction inputs

The Fig. 2a–2e notebooks share `data/dataset_lohoff_et_al_seqfish.h5ad`.
Their reference images and instructions are included in `data/`, including the Fig. 2e
reference and methodology. Generated runs remain local under `demo/outputs/`.

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

### Tissue-niche baselines

For named annotation with TissueAgent, Biomni and SpatialAgent, use the
[agent benchmark guide](../docs/tissue_niche_agent_baselines.md) and
[agent notebook](tissue_niche_agent_baselines.ipynb). The workflow covers heart MERFISH and
SpatialFusion Xenium OVCA with matched inputs/prompts, configurable models (GPT-5.1 by default),
macro F1/balanced accuracy, and spatial/performance plots. LLMiniST is deferred.


### Web UI Demo

https://github.com/user-attachments/assets/ef381418-cf5c-431b-9052-f931c922d2c8
