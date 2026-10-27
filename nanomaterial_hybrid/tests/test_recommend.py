import copy

import numpy as np
import pandas as pd
import pytest

from src.predict import PROFILE,TiO2Predictor
from src.recommend import RecommendationEngine,load_demo,recommend,rank_intervals,score_bounds,observed_target_support


def test_all_fifteen_families_are_returned_without_guessed_scores():
    frame=recommend(load_demo("demo_ml"))
    assert len(frame)==15
    assert set(frame.material_id)=={f"M{i:02d}" for i in range(1,16)}
    unsupported=frame.loc[frame.status.eq("insufficient_evidence")]
    assert unsupported.score_min.isna().all()
    assert unsupported.prediction.isna().all()
    assert unsupported.preference_tier.isna().all()


def test_unknown_pollutant_does_not_fabricate_ranking_or_prediction():
    frame=recommend(load_demo("demo_unknown"))
    assert frame.status.eq("insufficient_evidence").all()
    assert frame.prediction.isna().all()
    assert frame.attrs["summary"]["top_candidates"]==[]
    assert frame.attrs["summary"]["request_supported"] is False


def test_uv_scenario_preserves_overlapping_candidate_shortlist():
    frame=recommend(load_demo("demo_ml")).set_index("material_id")
    assert set(frame.attrs["summary"]["top_candidates"])=={"M02","M03","M05","M06","M08"}
    assert frame.attrs["summary"]["unique_policy_winner"] is None
    assert np.isfinite(frame.loc["M02","prediction"])
    assert frame.loc["M02","prediction_profile_id"]==PROFILE
    assert frame.loc["M03","score_min"]==55
    assert frame.loc["M03","score_max"]==70
    assert pd.isna(frame.loc["M03","recovery"])


def test_dark_excludes_photocatalytic_routes_but_not_adsorption():
    frame=recommend(load_demo("demo_dark")).set_index("material_id")
    assert frame.loc["M02","status"]=="incompatible_with_setup"
    assert frame.loc["M03","status"]=="incompatible_with_setup"
    assert pd.isna(frame.loc["M02","prediction"])
    assert pd.isna(frame.loc["M02","preference_tier"])
    assert frame.attrs["summary"]["top_candidates"]==["M05","M06","M08"]
    assert pd.isna(frame.loc["M05","setup"])
    assert pd.isna(frame.loc["M06","setup"])


def test_new_abstract_evidence_preserves_uncertainty_and_profile_boundaries():
    frame=recommend(load_demo("demo_ml")).set_index("material_id")
    for material,profile,evidence in [("M05","P14","E019"),("M06","P13","E018")]:
        row=frame.loc[material]
        assert row["status"]=="conditional"
        assert row["profile_id"]==profile
        assert row["evidence_ids"]==evidence
        assert pd.isna(row["setup"]) and pd.isna(row["recovery"])
        assert row["score_min"]==30 and row["score_max"]==70
        assert "does not establish an illumination requirement" in row["reason"]
        assert pd.isna(row["prediction"])


@pytest.mark.parametrize("qualifier",["up_to","maximum_reported","reported_range","approximately"])
def test_qualified_results_cannot_become_exact_target_support(qualifier):
    scenario=dict(load_demo("demo_lead"),required_removal_percent=90)
    observation={field:scenario[field] for field in ["pH","dose_g_L","concentration_mg_L","temperature_C","time_min"]}
    observation.update(result_value=99,result_unit="percent",result_qualifier=qualifier,endpoint="reported_removal_percent")
    assert not observed_target_support(observation,scenario)[0]


def test_unaccepted_new_profiles_remain_unranked():
    scenario=load_demo("demo_ml")
    scenario["consider_study_profiles"]=False
    result=recommend(scenario).set_index("material_id")
    for material in ("M05","M06"):
        assert not result.loc[material,"rank_eligible"]
        assert pd.isna(result.loc[material,"preference_tier"])


def test_source_matched_lead_case_has_documented_policy_winner():
    frame=recommend(load_demo("demo_lead")).set_index("material_id")
    assert frame.attrs["summary"]["unique_policy_winner"]=="M13"
    assert frame.loc["M13","status"]=="supported"
    assert frame.loc["M13","score_min"]==100
    assert frame.loc["M13","evidence_ids"]=="E013;E014"
    assert pd.isna(frame.loc["M13","prediction"])
    assert frame.loc["M01","score_min"]==62.5


def test_changed_concentration_cannot_keep_source_matched_support():
    scenario=load_demo("demo_lead")
    scenario["concentration_mg_L"]=1
    frame=recommend(scenario).set_index("material_id")
    assert frame.loc["M13","status"]=="conditional"
    assert frame.loc["M13","suitability"]==1


def test_source_recovery_requirement_cannot_be_bypassed():
    scenario=load_demo("demo_lead")
    scenario["available_equipment"]=["mixer","filtration"]
    frame=recommend(scenario).set_index("material_id")
    assert frame.loc["M13","status"]=="incompatible_with_setup"
    assert pd.isna(frame.loc["M13","preference_tier"])
    assert "M13" not in frame.attrs["summary"]["top_candidates"]


def test_conditional_ranking_requires_explicit_opt_in():
    scenario=load_demo("demo_ml")
    scenario["allow_conditional_ranking"]=False
    frame=recommend(scenario)
    assert frame.preference_tier.isna().all()
    assert frame.attrs["summary"]["ranked_candidates"]==0


def test_unknown_setup_and_unaccepted_profiles_are_not_silently_assumed():
    frame=recommend({"pollutant_id":"lead_ii"})
    assert frame.preference_tier.isna().all()
    assert frame.score_min.isna().all()
    assert frame.loc[frame.material_id.eq("M13"),"status"].iloc[0]=="conditional"


def test_named_literature_tio2_profile_never_receives_dataset_prediction():
    scenario=load_demo("demo_ml")
    scenario["profile_choices"]={"M02":"P02"}
    frame=recommend(scenario).set_index("material_id")
    assert frame.loc["M02","profile_id"]=="P02"
    assert pd.isna(frame.loc["M02","prediction"])
    assert "E002" in frame.loc["M02","evidence_ids"]


def test_prediction_magnitude_is_not_added_to_policy_score():
    real=TiO2Predictor()
    class ChangedPrediction:
        def predict(self,scenario):
            answer=real.predict(scenario)
            if answer["prediction"] is not None:
                answer["prediction"]+=1000
            return answer
    a=RecommendationEngine(predictor=real).recommend(load_demo("demo_ml"))
    b=RecommendationEngine(predictor=ChangedPrediction()).recommend(load_demo("demo_ml"))
    for col in ["score_min","score_max","preference_tier"]:
        assert a[col].equals(b[col])
    assert a.loc[a.material_id.eq("M02"),"prediction"].iloc[0]!=b.loc[b.material_id.eq("M02"),"prediction"].iloc[0]


def test_input_table_order_cannot_change_rankings():
    a=RecommendationEngine()
    b=RecommendationEngine()
    b.materials=b.materials.sample(frac=1,random_state=19)
    b.profiles=b.profiles.sample(frac=1,random_state=19)
    b.evidence=b.evidence.sample(frac=1,random_state=19)
    first=a.recommend(load_demo("demo_lead"))
    second=b.recommend(load_demo("demo_lead"))
    cols=["material_id","status","profile_id","score_min","score_max","preference_tier"]
    assert first[cols].equals(second[cols])


def test_interval_dominance_is_not_midpoint_sorting():
    rows=[{"material_id":"A","rank_eligible":True,"score_min":80,"score_max":90},
          {"material_id":"B","rank_eligible":True,"score_min":70,"score_max":85},
          {"material_id":"C","rank_eligible":True,"score_min":60,"score_max":75}]
    assert rank_intervals(rows)==["A","B"]
    assert rows[2]["preference_tier"]==2
    assert rows[1]["rank_best"]==1 and rows[1]["rank_worst"]==3


def test_unknown_ratings_keep_full_range_without_renormalisation():
    assert score_bounds({"suitability":1,"setup":2,"recovery":None},{"suitability":.6,"setup":.25,"recovery":.15})==(55,70)
    assert score_bounds({"suitability":None,"setup":None,"recovery":None},{"suitability":.6,"setup":.25,"recovery":.15})==(0,100)


def test_negative_weights_are_rejected():
    with pytest.raises(ValueError):
        score_bounds({"suitability":1,"setup":2,"recovery":None},{"suitability":2,"setup":-1,"recovery":0})


def test_weight_sensitivity_detects_a_changed_shortlist():
    engine=RecommendationEngine()
    config=copy.deepcopy(engine.config)
    config["alternative_weights"]=[{"suitability":0,"setup":0,"recovery":1}]
    result=RecommendationEngine(config=config).recommend(load_demo("demo_lead"))
    assert result.attrs["summary"]["weight_sensitive"] is True


def test_input_case_does_not_change_the_demo_result():
    original=load_demo("demo_ml")
    variant=dict(original,light_type="uv",available_equipment=["Mixer","Centrifuge","Filtration"])
    a=recommend(original)
    b=recommend(variant)
    assert a.attrs["summary"]["top_candidates"]==b.attrs["summary"]["top_candidates"]
    assert a.prediction.equals(b.prediction)


@pytest.mark.parametrize("changes",[
    {"pH":99},{"concentration_mg_L":float("inf")},{"dose_g_L":True},
    {"available_equipment":"centrifuge"},{"allow_conditional_ranking":"yes"},
    {"requested_endpoint":"invented"},{"profile_choices":{"M02":"P09"}},
])
def test_invalid_scenario_is_rejected(changes):
    scenario=dict(load_demo("demo_ml"),**changes)
    with pytest.raises(ValueError):
        recommend(scenario)


def test_aliases_preserve_explicit_lead_species():
    assert recommend({"pollutant_id":"SMX"}).attrs["summary"]["pollutant_id"]=="sulfamethoxazole"
    assert recommend({"pollutant_id":"Pb2+"}).attrs["summary"]["pollutant_id"]=="lead_ii"
    assert recommend({"pollutant_id":"lead"}).attrs["summary"]["request_supported"] is False
