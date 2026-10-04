---
name: ccc-stlearn
description: Step 4 of ccc_ensemble. Run the shipped stLearn co-expression scorer on Step 1 outputs; write project/outputs/stlearn_scores.csv.
applies_to: [coding_agent]
tags: [ccc, stlearn, spatial, co-expression, ensemble]
status: enable
---

# CCC stLearn
Run exactly:
```python
%run project/skills/ccc-stlearn/scripts/ccc_stlearn.py
```
Requires Step 1 files/log radius; writes `project/outputs/stlearn_scores.csv`. Do not inspect/reimplement or add checks after success.
