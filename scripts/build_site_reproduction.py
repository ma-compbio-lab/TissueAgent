"""Export the BioFigBench figure-reproduction results as static assets for ``site/``.

The results live in the standalone ``BioFigBench-website`` package (a Flask app plus ~240 MB of
images). This script reuses that package's own loader, ``web_ui.reproduction.load_reproduction``, so
the static page shows exactly what the Flask page shows, including the merged reruns. It then writes

    site/assets/reproduction/data.json
    site/assets/reproduction/img/<article>/<panel>/<slot>.webp      (<= FULL_EDGE px)
    site/assets/reproduction/img/<article>/<panel>/<slot>-s.webp    (<= THUMB_EDGE px)

where ``<slot>`` is ``original``, ``tissueagent``, ``spatialagent`` or ``biomni``.

Usage (from the repo root):

    python scripts/build_site_reproduction.py [--source BioFigBench-website] [--out site/assets/reproduction]

Needs Pillow. Images are scaled down only, EXIF-oriented, and transparency is composited on white,
matching the image protocol in the package's report README. Unchanged outputs are skipped.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = None  # trusted local data; some source panels are very large

AGENTS = ("tissueagent", "spatialagent", "biomni")
SLOTS = ("original", *AGENTS)
FULL_EDGE = 1600
THUMB_EDGE = 560
FULL_QUALITY = 84
THUMB_QUALITY = 80
MANUAL_RERUN_MARKER = "mkdir_loff_reproduce_resutls_tissueagent"
METRICS_REPORT = Path("reports/figure_reproduce_20260904/metrics.json")


def _load_rgb(path: Path) -> Image.Image:
    image = ImageOps.exif_transpose(Image.open(path))
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, (255, 255, 255))
        canvas.paste(rgba, mask=rgba.getchannel("A"))
        return canvas
    return image.convert("RGB")


def _save_scaled(image: Image.Image, edge: int, quality: int, dest: Path) -> tuple[int, int]:
    scaled = image.copy()
    scaled.thumbnail((edge, edge), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    scaled.save(dest, "WEBP", quality=quality, method=5)
    return scaled.size


def _write_images(source: Path, folder: Path, slot: str) -> tuple[int, int] | None:
    """Write the full and thumbnail variants; return the full image's (width, height)."""
    if not source or not source.is_file():
        return None
    full_dest = folder / f"{slot}.webp"
    thumb_dest = folder / f"{slot}-s.webp"
    newest_source = source.stat().st_mtime
    if (
        full_dest.is_file()
        and thumb_dest.is_file()
        and min(full_dest.stat().st_mtime, thumb_dest.stat().st_mtime) >= newest_source
    ):
        with Image.open(full_dest) as existing:
            return existing.size
    image = _load_rgb(source)
    size = _save_scaled(image, FULL_EDGE, FULL_QUALITY, full_dest)
    _save_scaled(image, THUMB_EDGE, THUMB_QUALITY, thumb_dest)
    return size


def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


def _write_metrics_csv(data: dict, dest: Path) -> None:
    """A downloadable per-panel table. Unlike the package's metrics.csv it has no local paths."""
    import csv

    columns = [
        "article_id", "panel_id", "figure", "paper_title", "method", "run_status", "run_seconds",
        "has_image", "ssim", "phash_similarity", "orb_similarity", "in_matched_set",
        "access_audit_flag", "rerun_in_separate_workflow",
    ]
    with dest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        for paper in data["papers"]:
            for panel in paper["panels"]:
                for agent in AGENTS:
                    run = panel["runs"][agent]
                    writer.writerow([
                        paper["article"], panel["panel"], panel["label"], paper["title"], agent,
                        run["status"], "" if run["seconds"] is None else run["seconds"],
                        int(run["image"]),
                        *("" if run[k] is None else run[k] for k in ("ssim", "phash", "orb")),
                        int(panel["matched"]), int(run["flagged"]), int(run["rerun"]),
                    ])


def build(source: Path, out: Path) -> dict:
    source = source.resolve()
    sys.path.insert(0, str(source))
    from web_ui.reproduction import load_reproduction  # noqa: E402  (path set above)

    snapshot = load_reproduction(source)
    if not snapshot.available:
        raise SystemExit(f"Reproduction snapshot unavailable: {snapshot.error}")
    metrics = json.loads((source / METRICS_REPORT).read_text(encoding="utf-8"))
    rows = metrics["rows"]
    matched = set(metrics["paired"])
    dataset = {(d["article_id"], d["panel_id"]): d for d in metrics["dataset"]}

    papers: dict[str, dict] = {}
    bytes_written = 0
    for record in snapshot.records:
        key = f"{record.article_id}::{record.panel_id}"
        folder = out / "img" / record.article_id / record.panel_id
        meta = dataset.get((record.article_id, record.panel_id), {})

        original_size = _write_images(record.original_image_path, folder, "original")
        runs = {}
        for agent in AGENTS:
            run = record.agent_run(agent)
            score = rows.get(f"{key}::{agent}", {})
            size = _write_images(run.image_path, folder, agent) if run.image_path else None
            runs[agent] = {
                "status": run.status,
                "seconds": _round(run.elapsed_seconds, 1),
                "image": size is not None,
                "ssim": _round(score.get("ssim")),
                "phash": _round(score.get("phash_similarity")),
                "orb": _round(score.get("orb_similarity")),
                "flagged": bool(score.get("audit_flag")),
                "rerun": bool(run.image_path and MANUAL_RERUN_MARKER in str(run.image_path)),
            }

        paper = papers.setdefault(
            record.article_id,
            {
                "article": record.article_id,
                "title": record.paper_title,
                "journal": record.journal,
                "year": record.year,
                "doi": record.doi,
                "panels": [],
            },
        )
        paper["panels"].append(
            {
                "panel": record.panel_id,
                "label": record.published_id,
                "caption": record.caption,
                "figureType": meta.get("figure_type", ""),
                "technologies": meta.get("technologies", []),
                "matched": key in matched,
                "originalSize": list(original_size) if original_size else None,
                "runs": runs,
            }
        )

    bytes_written = sum(p.stat().st_size for p in (out / "img").rglob("*.webp"))
    data = {
        "generatedAt": metrics["generated_at"],
        "source": snapshot.source_label,
        "coverage": metrics["summary"],
        "matchedCount": metrics["paired_n"],
        "papers": list(papers.values()),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    _write_metrics_csv(data, out / "metrics.csv")
    panel_count = sum(len(p["panels"]) for p in papers.values())
    print(
        f"{panel_count} panels from {len(papers)} papers, {data['matchedCount']} matched; "
        f"{bytes_written / 1e6:.1f} MB of images, data.json "
        f"{(out / 'data.json').stat().st_size / 1e3:.0f} kB"
    )
    return data


def main() -> None:
    repo = Path(__file__).resolve().parent.parent
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", type=Path, default=repo / "BioFigBench-website")
    parser.add_argument("--out", type=Path, default=repo / "site" / "assets" / "reproduction")
    args = parser.parse_args()
    build(args.source, args.out)


if __name__ == "__main__":
    main()
