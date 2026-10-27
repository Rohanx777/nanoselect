import hashlib
import json

import pandas as pd

from src.data_audit import ROOT, INPUTS, clean_frame, summarise


def test_source_files_match_manifest():
    records = json.loads((ROOT / "data/source_manifest.json").read_text())
    for record in records:
        payload = (ROOT / record["path"]).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]


def test_audit_keeps_conflicting_results_visible():
    raw = pd.DataFrame({"I":[1,1], "T":[25,25], "D":[1,1], "C0":[10,10],
                        "pH":[7,7], "mlogk":[1,2], "SMILES":["C", "C"],
                        "Molecule_Name":[" methane ", "methane"]})
    audit = summarise(raw)
    assert audit["same_input_groups_with_different_targets"] == 1
    assert audit["normalised_exact_duplicates"] == 0
    assert audit["unique_names_after_strip"] == 1
    assert len(clean_frame(raw)) == 2


def test_selected_dataset_contains_only_valid_nonduplicate_inputs():
    frame = pd.read_csv(ROOT / "data/processed/tio2_audited.csv")
    assert not frame.duplicated(subset=INPUTS + ["mlogk"]).any()
    assert (frame.D > 0).all()
    assert frame[INPUTS + ["mlogk"]].notna().all().all()
    assert set(frame.material_id) == {"M02"}
    assert frame.groupby(INPUTS).input_group_id.nunique().max() == 1
