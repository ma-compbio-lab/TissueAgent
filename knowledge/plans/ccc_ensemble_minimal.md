---
name: ccc_ensemble
status: disabled
description: >
  Fixed four-member spatial CCC ensemble: prep shared LR resource/base, run
  LIANA+, COMMOT, stLearn and decoupler, then aggregate to ccc_ensemble.csv.
---

## Contract
Produce only `project/outputs/ccc_ensemble.csv` with columns `ligand, receptor, liana_score, commot_score, stlearn_score, decoupler_score, liana_pct, commot_pct, stlearn_pct, decoupler_pct, ensemble_score`, sorted descending.

Draft exactly the six command-only steps below. Step descriptions should be just the command; expected_artifacts just the listed files. No validation/reporting/check stages unless a required file is missing. Cross-step state is only `project/outputs/`. Executors must run shipped scripts directly (no inspect/paste/reimplement).

1. `ccc-data-prep`: `%run project/skills/ccc-data-prep/scripts/ccc_data_prep.py --adata <input> --cell-type <obs column> --species <human|mouse>` → `project/outputs/ccc_base.h5ad`, `project/outputs/ccc_lr_common.csv`, `project/outputs/logs/ccc_data_prep.json`.
2. `ccc-liana`: `%run project/skills/ccc-liana/scripts/ccc_liana.py` → `project/outputs/liana_scores.csv`.
3. `ccc-commot`: `%run project/skills/ccc-commot/scripts/ccc_commot.py` → `project/outputs/commot_scores.csv`.
4. `ccc-stlearn`: `%run project/skills/ccc-stlearn/scripts/ccc_stlearn.py` → `project/outputs/stlearn_scores.csv`.
5. `ccc-decoupler`: `%run project/skills/ccc-decoupler/scripts/ccc_decoupler.py` → `project/outputs/decoupler_scores.csv`.
6. `ccc-aggregate`: `%run project/skills/ccc-aggregate/scripts/ccc_aggregate.py` → `project/outputs/ccc_ensemble.csv`.

Do not drop/add members, add p-values/evaluation metrics, reweight, or change the combiner; scripts already use the shared LR file, prep-log radius/k, and `obs['_dact']`.
