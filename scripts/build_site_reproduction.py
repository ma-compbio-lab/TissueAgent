"""Export the BioFigBench figure-reproduction results as static assets for ``site/``.

The results live in the standalone ``BioFigBench-website`` package (a Flask app plus ~240 MB of
images). This script reuses that package's own loader, ``web_ui.reproduction.load_reproduction``, so
the static page shows exactly what the Flask page shows, including the merged reruns. It then writes

    site/assets/reproduction/data.json
    site/assets/reproduction/metrics.csv
    site/assets/reproduction/img/<article>/<panel>/<slot>.webp      (<= FULL_EDGE px)
    site/assets/reproduction/img/<article>/<panel>/<slot>-s.webp    (<= THUMB_EDGE px)

where ``<slot>`` is ``original``, ``tissueagent``, ``spatialagent`` or ``biomni``.

Results can be replaced without touching the package: put ``<source>/updates/<article>/<panel>/<method>.png``
and the build shows that image and recomputes its SSIM / pHash / ORB (scripts/panel_metrics.py). Hand
corrections to the keyword-based technology and auxiliary-data labels live in scripts/label_corrections.py.

Only panels on which all three methods were run are exported, so every method is shown on the same
panels. Panels that only some methods attempted are skipped (the count is printed).

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

from label_corrections import apply as apply_label_corrections
from label_corrections import checks_for

Image.MAX_IMAGE_PIXELS = None  # trusted local data; some source panels are very large

AGENTS = ("tissueagent", "spatialagent", "biomni")
SLOTS = ("original", *AGENTS)
FULL_EDGE = 1600
THUMB_EDGE = 560
FULL_QUALITY = 84
THUMB_QUALITY = 80
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


def _write_images(source: Path, folder: Path, slot: str, force: bool = False) -> tuple[int, int] | None:
    """Write the full and thumbnail variants; return the full image's (width, height)."""
    if not source or not source.is_file():
        return None
    full_dest = folder / f"{slot}.webp"
    thumb_dest = folder / f"{slot}-s.webp"
    newest_source = source.stat().st_mtime
    if (
        not force
        and full_dest.is_file()
        and thumb_dest.is_file()
        and min(full_dest.stat().st_mtime, thumb_dest.stat().st_mtime) >= newest_source
    ):
        with Image.open(full_dest) as existing:
            return existing.size
    image = _load_rgb(source)
    size = _save_scaled(image, FULL_EDGE, FULL_QUALITY, full_dest)
    _save_scaled(image, THUMB_EDGE, THUMB_QUALITY, thumb_dest)
    return size


_SOURCE_NAMES = {
    "zenodo.org": "Zenodo",
    "media.springernature.com": "Publisher supplementary files",
    "cf.10xgenomics.com": "10x Genomics",
    "ftp.ncbi.nlm.nih.gov": "NCBI GEO",
    "raw.githubusercontent.com": "GitHub",
    "media.githubusercontent.com": "GitHub",
    "download.brainimagelibrary.org": "Brain Image Library",
    "datadryad.org": "Dryad",
    "api.brain-map.org": "Allen Institute",
    "download.alleninstitute.org": "Allen Institute",
    "ftp.cngb.org": "CNGB",
    "content.cruk.cam.ac.uk": "CRUK Cambridge Institute",
}


def _data_sources(urls) -> list[str]:
    """Distinct, readable hosting names for a panel's raw-data URLs."""
    from urllib.parse import urlparse

    names: list[str] = []
    for url in urls or ():
        host = urlparse(url).netloc.lower().removeprefix("www.")
        if host.endswith("amazonaws.com"):
            name = "Amazon S3"
        else:
            name = _SOURCE_NAMES.get(host) or host
        if name and name not in names:
            names.append(name)
    return names


def _was_run(run) -> bool:
    """True once the method has a terminal result (anything except not started / still running)."""
    return run.status not in ("pending", "running")


def _round(value, digits=4):
    return None if value is None else round(float(value), digits)


def _write_metrics_csv(data: dict, dest: Path) -> None:
    """A downloadable per-panel table. Unlike the package's metrics.csv it has no local paths."""
    import csv

    columns = [
        "article_id", "panel_id", "figure", "paper_title", "method",
        "has_image", "ssim", "phash_similarity", "orb_similarity", "in_matched_set",
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
                        int(run["image"]),
                        *("" if run[k] is None else run[k] for k in ("ssim", "phash", "orb")),
                        int(panel["matched"]),
                    ])


def _find_updates(source: Path) -> dict[tuple[str, str, str], Path]:
    """Replacement result images: ``updates/<article>/<panel>/<method>.<ext>``."""
    found: dict[tuple[str, str, str], Path] = {}
    root = source / "updates"
    if not root.is_dir():
        return found
    for path in sorted(root.glob("*/*/*")):
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and path.stem in AGENTS:
            found[(path.parent.parent.name, path.parent.name, path.stem)] = path
    return found


def _score_update(reference: Path, generated: Path) -> dict:
    import panel_metrics  # needs OpenCV, scikit-image and scipy; only loaded when a result is replaced

    got = panel_metrics.score(reference, generated)
    return {"ssim": got["ssim"], "phash_similarity": got["phash_similarity"], "orb_similarity": got["orb_similarity"]}


def _prune_images(img_root: Path, papers: dict[str, dict]) -> None:
    """Delete images from earlier builds that the current data no longer references."""
    expected: set[Path] = set()
    for paper in papers.values():
        for panel in paper["panels"]:
            folder = img_root / paper["article"] / panel["panel"]
            slots = ["original", *(a for a in AGENTS if panel["runs"][a]["image"])]
            for slot in slots:
                expected |= {folder / f"{slot}.webp", folder / f"{slot}-s.webp"}
    if not img_root.is_dir():
        return
    for path in img_root.rglob("*.webp"):
        if path not in expected:
            path.unlink()
    for directory in sorted((p for p in img_root.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()


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

    updates = _find_updates(source)
    replaced: list[str] = []
    label_changes: list[dict] = []
    label_checks: list[dict] = []
    papers: dict[str, dict] = {}
    excluded: list[dict] = []
    for record in snapshot.records:
        key = f"{record.article_id}::{record.panel_id}"
        if not all(_was_run(record.agent_run(agent)) for agent in AGENTS):
            excluded.append(
                {
                    "article": record.article_id,
                    "title": record.paper_title,
                    "panel": record.panel_id,
                    "label": record.published_id,
                    "ran": [a for a in AGENTS if _was_run(record.agent_run(a))],
                }
            )
            continue
        folder = out / "img" / record.article_id / record.panel_id
        meta = dataset.get((record.article_id, record.panel_id), {})
        technologies, modalities, changes = apply_label_corrections(
            record.article_id, record.panel_id, meta.get("technologies", []), meta.get("modalities", [])
        )
        for change in changes:
            change.update(title=record.paper_title, label=record.published_id)
        label_changes.extend(changes)
        for check in checks_for(record.article_id, record.panel_id):
            label_checks.append(
                {
                    "article": record.article_id,
                    "title": record.paper_title,
                    "panel": record.panel_id,
                    "label": record.published_id,
                    "reason": check["reason"],
                }
            )

        original_size = _write_images(record.original_image_path, folder, "original")
        runs = {}
        for agent in AGENTS:
            run = record.agent_run(agent)
            score = rows.get(f"{key}::{agent}", {})
            image_path = run.image_path
            replacement = updates.get((record.article_id, record.panel_id, agent))
            if replacement:
                image_path = replacement
                score = _score_update(record.original_image_path, replacement)
                replaced.append(f"{record.article_id} {record.panel_id} {agent}")
            size = _write_images(image_path, folder, agent, force=bool(replacement)) if image_path else None
            runs[agent] = {
                "image": size is not None,
                "ssim": _round(score.get("ssim")),
                "phash": _round(score.get("phash_similarity")),
                "orb": _round(score.get("orb_similarity")),
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
                "methods": (record.methods or "").strip(),
                "figureType": meta.get("figure_type", ""),
                "technologies": technologies,
                "modalities": modalities,
                "dataSources": _data_sources(record.raw_data_urls),
                "matched": key in matched,
                "originalSize": list(original_size) if original_size else None,
                "runs": runs,
            }
        )

    _prune_images(out / "img", papers)
    bytes_written = sum(p.stat().st_size for p in (out / "img").rglob("*.webp"))
    panels = [panel for paper in papers.values() for panel in paper["panels"]]
    matched_count = sum(panel["matched"] for panel in panels)
    if matched_count != metrics["paired_n"]:
        print(
            f"note: matched set has {matched_count} panels here but metrics.json lists "
            f"{metrics['paired_n']}; using the {matched_count} shown",
            file=sys.stderr,
        )
    data = {
        "generatedAt": metrics["generated_at"],
        "source": snapshot.source_label,
        "matchedCount": matched_count,
        "labelCorrections": label_changes,
        "labelChecks": label_checks,
        "papers": list(papers.values()),
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "data.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    _write_metrics_csv(data, out / "metrics.csv")
    if out.resolve().is_relative_to((Path(__file__).resolve().parent.parent / "site")):
        from stamp_site_version import stamp

        stamp()
    if replaced:
        print(f"replaced {len(replaced)} result(s) and recomputed their scores: " + "; ".join(replaced))
    print(
        f"{len(label_changes)} label correction(s) applied; "
        f"{len(panels)} panels from {len(papers)} papers, {matched_count} matched, "
        f"{len(excluded)} left out (not run by every method); {bytes_written / 1e6:.1f} MB of images, "
        f"data.json {(out / 'data.json').stat().st_size / 1e3:.0f} kB"
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
