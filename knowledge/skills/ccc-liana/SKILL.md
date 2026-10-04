---
name: ccc-liana
description: Step 2 of ccc_ensemble. Run the shipped LIANA+ scorer on Step 1 outputs; write project/outputs/liana_scores.csv.
applies_to: [coding_agent]
tags: [ccc, liana, ligand-receptor, ensemble]
status: enable
---

# CCC LIANA
Run exactly:
```python
%run project/skills/ccc-liana/scripts/ccc_liana.py
```
Requires Step 1 files; writes `project/outputs/liana_scores.csv`. Do not inspect/reimplement or add checks after success.
