---
name: ccc-decoupler
description: Step 5 of ccc_ensemble. Run the shipped decoupler/PROGENy-response scorer using Step 1 obs['_dact']; write project/outputs/decoupler_scores.csv.
applies_to: [coding_agent]
tags: [ccc, decoupler, progeny, downstream, pathway, ensemble]
status: enable
---

# CCC decoupler
Run exactly:
```python
%run project/skills/ccc-decoupler/scripts/ccc_decoupler.py
```
Uses Step 1 `obs['_dact']`; writes `project/outputs/decoupler_scores.csv`. Do not recompute/inspect/reimplement or add checks after success.
