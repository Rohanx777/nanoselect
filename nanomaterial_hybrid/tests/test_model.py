import json

import numpy as np
import pandas as pd
import pytest

from src.predict import ROOT, FEATURES, NUMERIC, TiO2Predictor, assess_inputs, build_domain, scenario_from_row


def trained_predictor_and_scenario():
    predictor=TiO2Predictor()
    scenario=json.loads((ROOT / "config/demo_ml_scenario.json").read_text())
    return predictor,scenario


def test_no_identical_group_leakage_and_cv_uses_training_only():
    split=pd.read_csv(ROOT / "outputs/train_test_split.csv")
    assert split.groupby("input_group_id").split.nunique().max()==1
    assert split.source_row.is_unique
    assert len(split)==440
    cv=pd.read_csv(ROOT / "outputs/cv_validation_folds.csv")
    assert set(cv.source_row)==set(split.loc[split.split.eq("train"),"source_row"])
    assert cv.source_row.is_unique
    assert cv.groupby("input_group_id").fold.nunique().max()==1


def test_model_only_uses_real_predictive_features():
    predictor,_=trained_predictor_and_scenario()
    assert predictor.card["input_features"]==FEATURES
    assert "mlogk" not in FEATURES
    assert "source_row" not in FEATURES
    assert predictor.card["study_independent_validation"] is False
    assert predictor.card["target"]=="mlogk"


def test_real_prediction_is_repeatable_and_training_match_is_labelled():
    predictor,scenario=trained_predictor_and_scenario()
    a=predictor.predict(scenario)
    b=predictor.predict(scenario)
    if predictor.card["enabled_for_prototype"]:
        assert a["status"]=="experimental_ml_prediction"
        assert np.isfinite(a["prediction"])
        assert a["prediction"]==pytest.approx(b["prediction"],abs=1e-12)
        assert a["exact_training_conditions"] is True
    else:
        assert a["prediction"] is None


@pytest.mark.parametrize("changes",[
    {"pollutant_id":"methylene_blue"},
    {"dose_g_L":None},
    {"light_intensity_mW_cm2":float("nan")},
    {"temperature_C":float("inf")},
    {"pH":100},
    {"light_type":"dark"},
    {"material_id":"M03"},
    {"profile_id":"P02"},
    {"water_matrix":"industrial_wastewater"},
    {"requested_endpoint":"removal_percent"},
])
def test_runtime_refuses_unsupported_requests(changes):
    predictor,scenario=trained_predictor_and_scenario()
    answer=predictor.predict(dict(scenario,**changes))
    assert answer["prediction"] is None
    assert answer["status"]=="evidence_only"
    assert answer["reasons"]


def test_joint_domain_rejects_unobserved_corner_inside_marginal_ranges():
    # Six nearby conditions in two clusters; the cross-cluster combination is unsupported.
    frame=pd.DataFrame({"I":[1,1,1,10,10,10],"T":[20,20,20,30,30,30],
                        "D":[1,1,1,2,2,2],"C0":[1,1.1,1.2,9.8,9.9,10],
                        "pH":[3,3,3,9,9,9],"SMILES":["C"]*6,"Molecule_Name":["sample"]*6})
    policy={"minimum_distinct_training_conditions_per_pollutant":5,"local_distance_quantile":.9,
            "local_distance_multiplier":1.5,"local_distance_floor":.1,"local_distance_cap":1}
    domain=build_domain(frame,policy)
    scenario=scenario_from_row(frame.iloc[0])
    scenario["temperature_C"]=30
    check=assess_inputs(scenario,domain)
    assert not check["eligible"]
    assert any("combination" in reason for reason in check["reasons"])
    assert not any("outside" in reason for reason in check["reasons"])


def test_domain_is_built_from_training_inputs_only():
    split=pd.read_csv(ROOT / "outputs/train_test_split.csv")
    frame=pd.read_csv(ROOT / "data/processed/tio2_audited.csv")
    train=frame.loc[frame.source_row.isin(split.loc[split.split.eq("train"),"source_row"])]
    domain=json.loads((ROOT / "models/domain.json").read_text())
    for smiles,part in train.groupby("SMILES"):
        local=domain["pollutants"][smiles]
        assert local["minimum"]==part[NUMERIC].min().tolist()
        assert local["maximum"]==part[NUMERIC].max().tolist()
        assert local["distinct_conditions"]==len(part[NUMERIC].drop_duplicates())


def test_heldout_demo_does_not_match_training_group():
    path=ROOT / "config/demo_holdout_scenario.json"
    if not path.exists():
        pytest.skip("No supported held out condition available")
    predictor=TiO2Predictor()
    scenario=json.loads(path.read_text())
    answer=predictor.predict(scenario)
    assert answer["exact_training_conditions"] is False
    splits=pd.read_csv(ROOT / "outputs/train_test_split.csv")
    assert splits.set_index("source_row").loc[scenario["source_row"],"split"]=="test"


def test_model_card_records_predeclared_usefulness_gate():
    predictor,_=trained_predictor_and_scenario()
    expected=all(predictor.card["usefulness_checks"].values())
    assert predictor.card["enabled_for_prototype"]==expected
    assert predictor.card["acceptance_policy"]["minimum_relative_mae_improvement"]==.1
