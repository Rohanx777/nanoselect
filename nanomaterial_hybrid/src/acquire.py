"""Acquire immutable upstream research files without executing upstream code."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "c59e1a748b36b87eb051d9ce0acf6962bab1d118"
BASE = f"https://raw.githubusercontent.com/mahyavs/GNN_photodegradation/{COMMIT}/"
FILES = ["data/curated_data.xlsx", "data/original_data.xlsx", "README.md",
         "GNN_photodegradation/data_utils.py", "GNN_photodegradation/training.py",
         "GNN_photodegradation/evaluations.py", "GNN_photodegradation/config.py",
         "GNN_photodegradation/featurizer.py", "requirements.txt"]


def main():
    dest = ROOT / "data/raw/tio2"
    dest.mkdir(parents=True, exist_ok=True)
    records = []
    for rel in FILES:
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        url = BASE + rel
        if not target.exists():
            with urlopen(Request(url, headers={"User-Agent": "IDP-research-audit"}), timeout=30) as response:
                payload = response.read()
            target.write_bytes(payload)
        records.append({"path": str(target.relative_to(ROOT)), "url": url,
                        "commit": COMMIT, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
                        "size_bytes": target.stat().st_size,
                        "accessed_utc": datetime.now(timezone.utc).isoformat(),
                        "reuse_terms": "No repository licence located in audited tree; attribution retained, redistribution permission unverified."})
        print(target.relative_to(ROOT))
    paper_url = "https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12126497/fullTextXML"
    paper = dest / "paper.xml"
    if not paper.exists():
        with urlopen(Request(paper_url, headers={"User-Agent": "IDP-research-audit"}), timeout=30) as response:
            paper.write_bytes(response.read())
    records.append({"path": str(paper.relative_to(ROOT)), "url": paper_url,
                    "sha256": hashlib.sha256(paper.read_bytes()).hexdigest(),
                    "size_bytes": paper.stat().st_size,
                    "accessed_utc": datetime.now(timezone.utc).isoformat(),
                    "reuse_terms": "See article licence in cached XML; separate from spreadsheet reuse terms."})
    (ROOT / "data/source_manifest.json").write_text(json.dumps(records, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
