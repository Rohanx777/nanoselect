"""Restore only the two open access full texts referenced by Stage B."""
import json
from urllib.request import Request, urlopen

from .catalogue import ROOT


def main():
    seed=json.loads((ROOT / "data/curation/evidence_seed.json").read_text())
    for source in seed["sources"]:
        if "cache_url" not in source:
            continue
        target=ROOT / source["cache_path"]
        if not target.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            with urlopen(Request(source["cache_url"],headers={"User-Agent":"IDP-research-evidence"}),timeout=30) as response:
                payload=response.read()
            if b"<article" not in payload:
                raise ValueError("Expected article XML; did not save response")
            target.write_bytes(payload)
        print(source["source_id"], target.relative_to(ROOT))


if __name__=="__main__":
    main()
