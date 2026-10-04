---
name: ccc-data-prep
description: Step 1 of ccc_ensemble. Run the shipped prep script with --adata, --cell-type and --species; it writes ccc_base.h5ad, ccc_lr_common.csv and logs/ccc_data_prep.json for all later members.
applies_to: [coding_agent]
tags: [ccc, ligand-receptor, spatial, preprocessing, ensemble, progeny, decoupler]
status: enable
---

# CCC prep
Run exactly, filling only flags:
```python
%run project/skills/ccc-data-prep/scripts/ccc_data_prep.py --adata <path.h5ad> --cell-type <obs column> --species <human|mouse>
```
Writes `project/outputs/ccc_base.h5ad`, `project/outputs/ccc_lr_common.csv`, `project/outputs/logs/ccc_data_prep.json`. Do not inspect/reimplement or add checks after success.
