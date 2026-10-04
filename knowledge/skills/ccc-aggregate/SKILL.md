---
name: ccc-aggregate
description: Final ccc_ensemble step. Run the shipped aggregator; it inner-joins the four member score tables and writes project/outputs/ccc_ensemble.csv.
applies_to: [coding_agent]
tags: [ccc, ligand-receptor, ensemble, consensus]
status: enable
---

# CCC aggregate
Run exactly:
```python
%run project/skills/ccc-aggregate/scripts/ccc_aggregate.py
```
Inner-joins four member tables and mean-percentile-ranks them; writes `project/outputs/ccc_ensemble.csv`. Do not change combiner or add checks after success.
