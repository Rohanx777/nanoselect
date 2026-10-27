"""One fresh process per offline verification scenario."""
import argparse
import json
import socket
import sys

import pandas as pd

from .offline_guard import OfflineNetworkBlocked
from .recommend import ROOT,recommend,load_demo,export_result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",required=True)
    args=parser.parse_args()
    assert getattr(sys,"_nanomaterial_offline_guard",False),"Offline guard was not installed"
    try:
        socket.create_connection(("example.invalid",443),timeout=.1)
    except OfflineNetworkBlocked:
        pass
    else:
        raise AssertionError("External network probe was not blocked by verification guard")
    if args.scenario=="edited_input":
        path=ROOT / "outputs/final_verification/edited_input.json"
        scenario=json.loads(path.read_text())
    else:
        scenario=load_demo(args.scenario)
    frame=recommend(scenario)
    assert len(frame)==15 and frame.material_id.is_unique
    assert set(frame.material_id)=={f"M{i:02d}" for i in range(1,16)}
    summary=frame.attrs["summary"]
    if args.scenario=="demo_ml":
        assert summary["top_candidates"]==["M02","M03","M08"]
        assert frame.prediction.notna().sum()==1
    elif args.scenario=="demo_dark":
        assert summary["top_candidates"]==["M08"]
        assert frame.set_index("material_id").loc["M02","status"]=="incompatible_with_setup"
        assert frame.prediction.isna().all()
    elif args.scenario=="demo_lead":
        assert summary["unique_policy_winner"]=="M13"
        assert frame.set_index("material_id").loc["M13","status"]=="supported"
        assert frame.prediction.isna().all()
    elif args.scenario=="demo_unknown":
        assert summary["top_candidates"]==[]
        assert frame.status.eq("insufficient_evidence").all()
        assert frame.prediction.isna().all()
    elif args.scenario=="edited_input":
        assert frame.set_index("material_id").loc["M13","status"]=="conditional"
        assert summary["unique_policy_winner"] is None
    if args.scenario.startswith("demo_"):
        expected=pd.read_csv(ROOT / f"outputs/ranking_{args.scenario}.csv")
        columns=["material_id","status","profile_id","score_min","score_max","prediction"]
        a=frame[columns].copy()
        b=expected[columns].copy()
        a.attrs={}
        b.attrs={}
        pd.testing.assert_frame_equal(a,b,check_dtype=False,check_exact=False,rtol=1e-10,atol=1e-10)
    export_result(frame,ROOT / "outputs/final_verification" / args.scenario)
    print(json.dumps({"scenario":args.scenario,"offline_guard":True,"rows":len(frame),
                      "top_candidates":summary["top_candidates"],"status":"passed"}))


if __name__=="__main__":
    main()
