"""Simple local entry point; never acquires data or retrains models."""
import argparse
import hashlib
import json
import subprocess
import sys

from .notebook import ROOT,runtime_environment


def preflight():
    required=["data/materials.csv","data/material_profiles.csv","data/evidence.csv","data/pollutants.csv",
              "data/sources.csv","models/model_card.json","models/domain.json","config/ranking.json",
              "config/demo_holdout_scenario.json","web/index.html","web/style.css","web/app.js"]
    absent=[rel for rel in required if not (ROOT / rel).is_file()]
    if absent:
        raise RuntimeError("Required local files are missing: "+", ".join(absent))
    card=json.loads((ROOT / "models/model_card.json").read_text())
    if card["enabled_for_prototype"]:
        artifact=ROOT / "models" / card["artifact_filename"]
        if not artifact.is_file() or hashlib.sha256(artifact.read_bytes()).hexdigest()!=card["artifact_sha256"]:
            raise RuntimeError("The saved model is missing or does not match its recorded hash.")
    from .recommend import RecommendationEngine
    engine=RecommendationEngine()
    if len(engine.materials)!=15 or not engine.materials.material_id.is_unique:
        raise RuntimeError("Expected exactly 15 unique material families.")
    return {"status":"ready","project":str(ROOT),"material_families":15,
            "saved_model":card["model_name"],"numerical_module_enabled":card["enabled_for_prototype"]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--check",action="store_true",help="Check readiness without opening a browser")
    parser.add_argument("--text",action="store_true",help="Run the example in a terminal instead of the web interface")
    args=parser.parse_args()
    try:
        readiness=preflight()
    except (OSError,ValueError,RuntimeError,ImportError) as error:
        print(f"Cannot start the demo: {error}",file=sys.stderr)
        print("Keep the project folder and its .venv together. See START_HERE.md for recovery instructions.",file=sys.stderr)
        raise SystemExit(1)
    print(json.dumps(readiness,indent=2),flush=True)
    if args.check:
        return
    command=[sys.executable,"-m","src.recommend","--scenario","demo_ml"] if args.text else [
        sys.executable,"-m","src.webapp"]
    raise SystemExit(subprocess.call(command,cwd=ROOT,env=runtime_environment()))


if __name__=="__main__":
    main()
