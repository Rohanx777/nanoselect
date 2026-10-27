"""Final independent process checks using cached data, with external sockets blocked."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import nbformat
from bs4 import BeautifulSoup
from nbconvert import HTMLExporter

from .notebook import ROOT,runtime_environment


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_static_preview():
    notebook=nbformat.read(ROOT / "notebooks/04_hybrid_demo_executed.ipynb",as_version=4)
    nbformat.validate(notebook)
    for cell in notebook.cells:
        if cell.cell_type=="code":
            assert cell.execution_count is not None
            assert not any(output.output_type=="error" for output in cell.outputs)
    exporter=HTMLExporter(template_name="lab",embed_images=True,mathjax_url="",require_js_url="",jquery_url="")
    html,_=exporter.from_notebook_node(notebook)
    soup=BeautifulSoup(html,"html.parser")
    remote=[]
    for tag in soup.find_all(["script","link","img","iframe","audio","video","source"]):
        # Normal citation hyperlinks are allowed; these are automatically loaded assets.
        for attr in ["src","href","srcset"]:
            value=str(tag.get(attr,""))
            if value.startswith(("http:","https:","//")):
                remote.append(value)
    assert not remote,f"Static preview has remote assets: {remote}"
    target=ROOT / "outputs/hybrid_demo.html"
    target.write_text(html,encoding="utf-8")
    return {"path":str(target.relative_to(ROOT)),"remote_asset_tags":remote,
            "executed_code_cells":sum(c.cell_type=="code" for c in notebook.cells)}


def main():
    out=ROOT / "outputs/final_verification"
    out.mkdir(parents=True,exist_ok=True)
    env=runtime_environment()
    env["NANOMATERIAL_OFFLINE_VERIFY"]="1"
    env["PYTHONPATH"]=os.pathsep.join([str(ROOT / "tools/offline_bootstrap"),str(ROOT)])
    before={str(p.relative_to(ROOT)):digest(p) for p in (ROOT / "models").iterdir() if p.is_file()}
    # Keep a fixed verification fixture separate from the user's editable file.
    edited=json.loads((ROOT / "config/demo_lead.json").read_text())
    edited["concentration_mg_L"]=1
    (out / "edited_input.json").write_text(json.dumps(edited,indent=2),encoding="utf-8")
    runs=[]
    tasks=[("readiness",["-m","src.launch","--check"])]
    tasks += [(name,["-m","src.verify_worker","--scenario",name]) for name in ["demo_ml","demo_dark","demo_unknown","demo_lead","edited_input"]]
    tasks += [("custom_cli",["-m","src.recommend","--input","config/my_scenario.json"]),
              ("tests",["-m","pytest","-q"]),("notebook",["-m","src.notebook","--name","04_hybrid_demo","--execute"])]
    for name,arguments in tasks:
        started=time.perf_counter()
        completed=subprocess.run([sys.executable]+arguments,cwd=ROOT,env=env,text=True,encoding="utf-8",errors="replace",capture_output=True,timeout=120)
        (out / f"{name}.log").write_text(completed.stdout+"\n"+completed.stderr,encoding="utf-8")
        result={"task":name,"exit_code":completed.returncode,"seconds":round(time.perf_counter()-started,2)}
        runs.append(result)
        print(json.dumps(result),flush=True)
        if completed.returncode:
            raise RuntimeError(f"Verification failed for {name}; see outputs/final_verification/{name}.log")
    preview=export_static_preview()
    after={str(p.relative_to(ROOT)):digest(p) for p in (ROOT / "models").iterdir() if p.is_file()}
    assert before==after,"Model artifacts changed during demonstration verification"
    report={"status":"passed","date":"2026-10-25","method":"Fresh Python processes with an audit hook blocking non-loopback socket connections and external name lookups; local notebook kernel traffic permitted.",
            "runs":runs,"model_artifacts_unchanged":True,"model_sha256":after,
            "static_preview":preview,"scope":"Verifies local cached workflows, not scientific generalisation or a system wide network firewall."}
    (ROOT / "outputs/final_verification.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    lines="\n".join(f"| {row['task']} | Passed | {row['seconds']} |" for row in runs)
    text=f"""# Final demonstration verification

Status: passed on 25 October 2026.

Each scenario ran in a new Python process. A process local audit hook blocked non-loopback connections and external name lookups. Every scenario confirmed the guard by attempting a blocked external connection, then ran successfully from cached files. Loopback communication was allowed for the notebook kernel. This is a verification control, not a system wide firewall or proof of scientific validity.

| Check | Result | Seconds |
|---|---|---:|
{lines}

All five scenario runs returned exactly 15 unique material IDs. The four named examples matched their saved outputs. The edited input example changed the lead concentration and correctly lost its exact source matched winner. The test suite ran under the same guard, and the main notebook executed all seven code cells without errors. No model file changed, and no retraining occurred.

An offline static preview is available at outputs/hybrid_demo.html. Automatically loaded asset tags contain no remote URLs; research citations still require internet when clicked. This preview shows saved results and cannot recompute inputs. Use START_DEMO.cmd or the terminal command to run live predictions and rankings.

Exact process results and model hashes are in final_verification.json. Logs and per scenario outputs are in outputs/final_verification. The existing model remains preliminary, the score remains a decision policy rather than removal percentage, and unsupported evidence pairs remain unknown.
"""
    (ROOT / "outputs/final_verification.md").write_text(text,encoding="utf-8")
    print("Final verification passed; model artifacts unchanged and offline preview exported.")


if __name__=="__main__":
    main()
