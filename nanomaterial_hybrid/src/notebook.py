"""Launch notebooks with runtime/config files kept inside the project."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def runtime_environment():
    env = os.environ.copy()
    for key, sub in {"IPYTHONDIR":"ipython", "JUPYTER_CONFIG_DIR":"config",
                     "JUPYTER_DATA_DIR":"data", "JUPYTER_RUNTIME_DIR":"runtime",
                     "TEMP":"temp", "TMP":"temp"}.items():
        path = ROOT / ".runtime" / sub
        path.mkdir(parents=True, exist_ok=True)
        env[key] = str(path)
    return env


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--name", default="01_data_audit", choices=["01_data_audit","02_catalogue_evidence","03_model_evaluation","04_hybrid_demo"])
    args = parser.parse_args()
    env = runtime_environment()
    target = f"notebooks/{args.name}.ipynb"
    if args.execute:
        cmd = [sys.executable, "-m", "nbconvert", "--to", "notebook", "--execute", target,
               "--output", f"{args.name}_executed.ipynb", "--ExecutePreprocessor.timeout=90"]
    else:
        cmd = [sys.executable, "-m", "jupyterlab", target]
    raise SystemExit(subprocess.call(cmd, cwd=ROOT, env=env))


if __name__ == "__main__":
    main()
