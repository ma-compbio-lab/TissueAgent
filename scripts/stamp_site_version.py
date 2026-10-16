"""Stamp content-hash version strings on the site's CSS, JS and data references.

GitHub Pages lets browsers cache each file for ten minutes. Right after a publish a browser can
therefore pair the new index.html with a cached old reproduction.js, and the page breaks. Giving every
referenced file a ``?v=<hash of its contents>`` URL means a changed file is always fetched fresh and an
unchanged one stays cached, so the HTML and its scripts can never disagree.

Run it after editing anything under site/ (build_site_reproduction.py does this automatically):

    python scripts/stamp_site_version.py
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"

# page -> files it links to directly through href/src
LINKED = {
    "index.html": ("styles.css", "reproduction.js"),
    "paper.html": ("styles.css", "script.js"),
}
# index.html passes the data file's version to the script, which appends it to its fetch() URL
DATA_FILE = "assets/reproduction/data.json"
DATA_ATTRIBUTE = "data-data-version"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:10]


def stamp() -> dict[str, str]:
    """Rewrite the version strings in the site's HTML pages; return {file: version}."""
    versions: dict[str, str] = {}
    for page, files in LINKED.items():
        html_path = SITE / page
        html = html_path.read_text(encoding="utf-8")
        for name in files:
            version = digest(SITE / name)
            versions[name] = version
            pattern = rf'((?:href|src)="{re.escape(name)})(?:\?v=[0-9a-f]*)?(")'
            html, count = re.subn(pattern, rf"\g<1>?v={version}\g<2>", html)
            if count != 1:
                raise SystemExit(f"{page}: expected exactly one reference to {name}, found {count}")
        if page == "index.html":
            version = digest(SITE / DATA_FILE)
            versions[DATA_FILE] = version
            html, count = re.subn(rf'({DATA_ATTRIBUTE}=")[0-9a-f]*(")', rf"\g<1>{version}\g<2>", html)
            if count != 1:
                raise SystemExit(f"index.html: expected one {DATA_ATTRIBUTE} attribute, found {count}")
        html_path.write_text(html, encoding="utf-8")
    return versions


def main() -> None:
    for name, version in stamp().items():
        print(f"{version}  {name}")


if __name__ == "__main__":
    main()
