---
name: ccc-commot
description: Step 3 of ccc_ensemble. Run the shipped COMMOT scorer on Step 1 outputs; write project/outputs/commot_scores.csv.
applies_to: [coding_agent]
tags: [ccc, commot, spatial, optimal-transport, ensemble]
status: enable
---

# CCC COMMOT
Run exactly:
```python
%run project/skills/ccc-commot/scripts/ccc_commot.py
```
Requires Step 1 files/log radius; writes `project/outputs/commot_scores.csv`. Do not inspect/reimplement or add checks after success.
