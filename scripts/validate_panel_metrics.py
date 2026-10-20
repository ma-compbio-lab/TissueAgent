"""Check scripts/panel_metrics.py against the scores already published in the BioFigBench report.

For every published method/panel row whose image still exists, recompute SSIM, pHash and ORB from the
images and compare with metrics.json:

    python scripts/validate_panel_metrics.py [--source BioFigBench-website]
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import panel_metrics  # noqa: E402

AGENTS = ("tissueagent", "spatialagent", "biomni")
REPORT = Path("reports/figure_reproduce_20260904/metrics.json")


def main() -> None:
    default = Path(__file__).resolve().parent.parent / "BioFigBench-website"
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=default)
    source = parser.parse_args().source.resolve()
    sys.path.insert(0, str(source))
    from web_ui.reproduction import load_reproduction  # noqa: E402

    rows = json.loads((source / REPORT).read_text(encoding="utf-8"))["rows"]
    stats = {"rows": 0, "ssim": 0, "phash": 0, "keypoints": 0, "orb_exact": 0}
    orb_diffs: list[float] = []
    for record in load_reproduction(source).records:
        for agent in AGENTS:
            run = record.agent_run(agent)
            row = rows.get(f"{record.article_id}::{record.panel_id}::{agent}")
            if not (run.image_path and row and row.get("ssim") is not None):
                continue
            got = panel_metrics.score(record.original_image_path, run.image_path)
            stats["rows"] += 1
            stats["ssim"] += abs(got["ssim"] - row["ssim"]) < 1e-6
            stats["phash"] += got["phash_distance"] == row["phash_distance"]
            stats["keypoints"] += (got["reference_keypoints"], got["generated_keypoints"]) == (
                row["reference_keypoints"],
                row["generated_keypoints"],
            )
            if got["orb_similarity"] is not None and row["orb_similarity"] is not None:
                diff = abs(got["orb_similarity"] - row["orb_similarity"])
                orb_diffs.append(diff)
                stats["orb_exact"] += diff < 1e-9
    n = stats["rows"]
    print(f"{n} published rows recomputed")
    print(f"  SSIM exact (|diff| < 1e-6):        {stats['ssim']}/{n}")
    print(f"  pHash distance exact:              {stats['phash']}/{n}")
    print(f"  ORB keypoint counts exact:         {stats['keypoints']}/{n}")
    print(f"  ORB similarity exact:              {stats['orb_exact']}/{len(orb_diffs)}")
    if orb_diffs:
        print(f"  ORB similarity |diff|: median {statistics.median(orb_diffs):.4f}, max {max(orb_diffs):.4f}")


if __name__ == "__main__":
    main()
