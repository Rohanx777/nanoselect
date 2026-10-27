"""Deterministic 15-family screening with explicit evidence and score intervals."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from .predict import ROOT, PROFILE, TiO2Predictor

CRITERIA=["suitability","setup","recovery"]
STATUS_ORDER={"supported":0,"conditional":1,"incompatible_with_setup":2,"insufficient_evidence":3}
MATCH_FIELDS=["pH","concentration_mg_L","dose_g_L","temperature_C","time_min"]


def missing(value):
    return value is None or (not isinstance(value,(list,dict)) and pd.isna(value))


def score_bounds(ratings,weights):
    if (set(weights)!=set(CRITERIA) or any(not isinstance(v,(int,float)) or not np.isfinite(v) or v<0 for v in weights.values())
            or not np.isclose(sum(weights.values()),1)):
        raise ValueError("Ranking weights must cover the three criteria and sum to one.")
    lower=upper=0.0
    for criterion in CRITERIA:
        value=ratings[criterion]
        if value is not None and value not in (0,1,2):
            raise ValueError("Ratings must be zero, one, two or unknown.")
        lower+=weights[criterion]*(0 if value is None else value)/2
        upper+=weights[criterion]*(2 if value is None else value)/2
    return round(100*lower,6),round(100*upper,6)


def rank_intervals(rows):
    """Use strict interval dominance; stable IDs only order the display."""
    for row in rows:
        row.update(preference_tier=None,rank_best=None,rank_worst=None)
    eligible=[row for row in rows if row["rank_eligible"]]
    for row in eligible:
        row["rank_best"]=1+sum(other["score_min"]>row["score_max"]+1e-9 for other in eligible)
        row["rank_worst"]=len(eligible)-sum(row["score_min"]>other["score_max"]+1e-9 for other in eligible)
    remaining=eligible.copy()
    tier=1
    while remaining:
        frontier=[row for row in remaining if not any(other["score_min"]>row["score_max"]+1e-9 for other in remaining)]
        for row in frontier:
            row["preference_tier"]=tier
        ids={row["material_id"] for row in frontier}
        remaining=[row for row in remaining if row["material_id"] not in ids]
        tier+=1
    return sorted(row["material_id"] for row in eligible if row["preference_tier"]==1)


def normalise_pollutant(value,pollutants):
    key=str(value or "").strip().casefold().replace("_"," ")
    for row in pollutants.to_dict("records"):
        names=[row["pollutant_id"],row["display_name"]]+str(row["aliases"]).split(";")
        if key in {str(name).strip().casefold().replace("_"," ") for name in names}:
            return row["pollutant_id"]
    return None


def validate_scenario(scenario):
    for field in ["pH","dose_g_L","concentration_mg_L","temperature_C","time_min","light_intensity_mW_cm2","required_removal_percent"]:
        value=scenario.get(field)
        if value is None:
            continue
        if isinstance(value,bool):
            raise ValueError(f"{field} must be a finite number.")
        try:
            number=float(value)
        except (TypeError,ValueError):
            raise ValueError(f"{field} must be a finite number.") from None
        if not np.isfinite(number):
            raise ValueError(f"{field} must be a finite number.")
        if field in ["dose_g_L","concentration_mg_L","time_min","light_intensity_mW_cm2"] and number<=0:
            raise ValueError(f"{field} must be positive when supplied.")
        if field=="pH" and not 0<=number<=14:
            raise ValueError("pH must be between zero and fourteen.")
        if field=="required_removal_percent" and not 0<=number<=100:
            raise ValueError("required_removal_percent must be between zero and one hundred.")
    for flag in ["consider_study_profiles","allow_conditional_ranking","include_ml"]:
        if flag in scenario and not isinstance(scenario[flag],bool):
            raise ValueError(f"{flag} must be a boolean.")
    if "available_equipment" in scenario and not isinstance(scenario["available_equipment"],list):
        raise ValueError("available_equipment must be a list; omit it if unknown.")
    if scenario.get("requested_endpoint","qualitative_remediation") not in ["qualitative_remediation","removal_percent","mlogk","adsorption_capacity"]:
        raise ValueError("Unsupported requested_endpoint.")
    if not isinstance(scenario.get("profile_choices",{}),dict):
        raise ValueError("profile_choices must map material IDs to profile IDs.")
    if not all(isinstance(k,str) and isinstance(v,str) for k,v in scenario.get("profile_choices",{}).items()):
        raise ValueError("profile_choices keys and values must be registered ID strings.")


def light_rating(requirement,provided):
    light=str(provided or "unspecified").casefold()
    if requirement=="not_required_for_reported_adsorption":
        return 2,"The reported adsorption route does not require illumination."
    if light in ["dark","none"]:
        return 0,"The documented photocatalytic route requires light, which is explicitly unavailable."
    if light in ["unspecified","unknown"]:
        return None,"Illumination is unspecified."
    if requirement=="UVA":
        if light=="uva": return 2,"UVA is available for the documented route."
        if light in ["visible","uvb","uvc"]: return 0,"The supplied illumination does not match this documented UVA route."
        return 1,"UVA content or wavelength is unresolved; do not assume an exact irradiation match."
    if requirement=="UV_unspecified_band":
        if light in ["uv","uva","uvb","uvc"]: return 2,"UV is available; the source does not specify an exact band."
        if light=="visible": return 0,"Visible only illumination does not match the reported UV route."
        return 1,"UV content of the available illumination is unresolved."
    if requirement=="natural_sunlight":
        return (2,"Natural sunlight matches the documented light type.") if light=="sunlight" else (1,"The study used natural sunlight; the supplied lamp is not an exact source match.")
    return 1,"The source reports light activation without an extracted wavelength."


def matches_observation(observation,scenario):
    matched=[]
    mismatched=[]
    unknown=[]
    for field in MATCH_FIELDS:
        a=observation.get(field)
        b=scenario.get(field)
        if missing(a) or b is None:
            unknown.append(field)
        elif np.isclose(float(a),float(b),rtol=1e-6,atol=1e-6):
            matched.append(field)
        else:
            mismatched.append(field)
    return matched,mismatched,unknown


def observed_target_support(observation,scenario):
    matched,mismatched,unknown=matches_observation(observation,scenario)
    target=scenario.get("required_removal_percent")
    value=observation.get("result_value")
    # An 'up to' maximum cannot establish target attainment for a requested case.
    qualifier=observation.get("result_qualifier")
    endpoint=scenario.get("requested_endpoint","qualitative_remediation")
    supported=(endpoint=="removal_percent" and target is not None and not missing(value)
               and observation.get("result_unit")=="percent" and qualifier!="up_to"
               and len(matched)==len(MATCH_FIELDS) and not mismatched and not unknown
               and float(value)>=float(target) and scenario.get("water_matrix")=="laboratory_solution")
    return supported,matched,mismatched,unknown


class RecommendationEngine:
    def __init__(self,data_dir=None,config=None,predictor=None):
        self.data_dir=Path(data_dir) if data_dir else ROOT / "data"
        self.materials=pd.read_csv(self.data_dir / "materials.csv")
        self.profiles=pd.read_csv(self.data_dir / "material_profiles.csv")
        self.evidence=pd.read_csv(self.data_dir / "evidence.csv")
        self.pollutants=pd.read_csv(self.data_dir / "pollutants.csv")
        self.sources=pd.read_csv(self.data_dir / "sources.csv")
        self.source_urls=self.sources.set_index("source_id").url.to_dict()
        self.config=config or json.loads((ROOT / "config/ranking.json").read_text())
        self.predictor=predictor
        self.profile_map=self.profiles.set_index("profile_id").to_dict("index")
        self.profile_materials={p:v["material_id"] for p,v in self.profile_map.items()}
        self.profile_materials[PROFILE]="M02"

    def _profile(self,profile_id,records,scenario):
        profile=self.profile_map[profile_id]
        reasons=[]
        supported_rows=[]
        all_matches=[]
        for observation in records.to_dict("records"):
            supported,matched,mismatched,unknown=observed_target_support(observation,scenario)
            all_matches.append({"evidence_id":observation["evidence_id"],"matched":matched,
                                "different":mismatched,"unknown":unknown})
            if supported:
                supported_rows.append(observation["evidence_id"])
        suitability=2 if supported_rows else 1
        if supported_rows:
            reasons.append("A source observation matches the five checked operating inputs and reports the requested removal target; this is literature support, not a new prediction.")
        else:
            reasons.append("Relevant formulation and pollutant evidence exists, but the requested treatment objective is not fully matched by an extracted observation.")
        if all_matches:
            nearest=sorted(all_matches,key=lambda item:(-len(item["matched"]),item["evidence_id"]))[0]
            reasons.append(f"Closest extracted observation {nearest['evidence_id']}: matching fields {', '.join(nearest['matched']) or 'none'}; different fields {', '.join(nearest['different']) or 'none'}; unknown fields {', '.join(nearest['unknown']) or 'none'}.")
        if scenario.get("water_matrix")!="laboratory_solution":
            reasons.append("A matching laboratory water matrix assumption is absent; transfer to the requested water is unvalidated.")
        light,light_reason=light_rating(profile["light_requirement"],scenario.get("light_type"))
        reasons.append(light_reason)
        setup=light
        requirements=self.config["profile_requirements"].get(profile_id,{})
        equipment=scenario.get("available_equipment")
        if requirements.get("mixing_required"):
            if equipment is None:
                setup=None if light is None else min(light,1)
                reasons.append("Batch mixing availability is unknown under the prototype setup policy.")
            elif "mixer" not in equipment:
                setup=0
                reasons.append("The prototype batch setup requires mixing, which is absent from the declared equipment list.")
        recovery=None
        recovery_equipment=requirements.get("recovery_equipment")
        if recovery_equipment:
            if equipment is None:
                reasons.append(f"Availability of the reported {recovery_equipment} method is unknown.")
            elif recovery_equipment in equipment:
                recovery=requirements["recovery_rating"]
                reasons.append(str(profile["recovery_method"]))
            else:
                recovery=0
                reasons.append(f"The reported {recovery_equipment} separation method is absent; another method is not validated here.")
        else:
            reasons.append("Recovery performance is not established by the inspected source scope.")
        if requirements.get("setup_incompletely_documented") and setup is not None:
            setup=min(setup,1)
            reasons.append("Standalone control setup details are incomplete; composite setup claims are not transferred.")
        selected=scenario.get("profile_choices",{}).get(profile["material_id"])
        profile_accepted=selected==profile_id or scenario.get("consider_study_profiles",False)
        if not profile_accepted:
            reasons.append("The specific literature formulation has not been selected or accepted as a proposed study profile.")
        status="conditional"
        if setup==0 or recovery==0:
            status="incompatible_with_setup"
        elif suitability==2 and setup==2 and recovery==2 and profile_accepted:
            status="supported"
        return {"material_id":profile["material_id"],"profile_id":profile_id,"formulation":profile["formulation"],
                "status":status,"suitability":suitability,"setup":setup,"recovery":recovery,
                "profile_accepted":profile_accepted,"evidence_ids":sorted(records.evidence_id.tolist()),
                "source_ids":sorted(records.source_id.unique().tolist()),"source_scope":"; ".join(sorted(records.reviewed_scope.unique())),
                "matched_target_evidence_ids":supported_rows,"condition_matches":all_matches,
                "prediction":None,"prediction_target":None,"prediction_unit":None,"prediction_basis":None,
                "prediction_profile_id":None,"ml_fallback_reasons":[],"reasons":reasons}

    def _ml_profile(self,scenario):
        if not scenario.get("include_ml",False) or scenario.get("prediction_endpoint")!="mlogk":
            return None,["The dataset profile requires include_ml=true and an explicit prediction_endpoint=mlogk request."]
        if self.predictor is None:
            self.predictor=TiO2Predictor()
        request=dict(scenario,material_id="M02",profile_id=PROFILE,requested_endpoint="mlogk")
        answer=self.predictor.predict(request)
        if answer["prediction"] is None:
            known=self.predictor.domain["aliases"].get(str(scenario.get("pollutant_id","")).strip().casefold())
            if known is None:
                return None,answer["reasons"]
            light=str(scenario.get("light_type","")).casefold()
            unavailable=light in ["dark","none","visible"]
            candidate={"material_id":"M02","profile_id":PROFILE,"formulation":"Unspecified TiO2 grade in the training dataset",
                       "status":"incompatible_with_setup" if unavailable else "conditional",
                       "suitability":1,"setup":0 if unavailable else None,"recovery":None,"profile_accepted":True,
                       "evidence_ids":[],"source_ids":["A01","A02"],"source_scope":"model_scope_only_no_eligible_prediction",
                       "matched_target_evidence_ids":[],"condition_matches":[],"prediction":None,
                       "prediction_target":None,"prediction_unit":None,"prediction_basis":None,"prediction_profile_id":None,
                       "ml_fallback_reasons":answer["reasons"],
                       "reasons":["This pollutant is in the TiO2 training categories, but this request is not eligible for numerical prediction."]+answer["reasons"]}
            return candidate,answer["reasons"]
        return {"material_id":"M02","profile_id":PROFILE,"formulation":"Unspecified TiO2 grade in the training dataset",
                "status":"conditional","suitability":1,"setup":2,"recovery":None,"profile_accepted":True,
                "evidence_ids":[],"source_ids":["A01","A02"],"source_scope":"preliminary_input_group_ML_evaluation",
                "matched_target_evidence_ids":[],"condition_matches":[],
                "prediction":answer["prediction"],"prediction_target":answer["prediction_target"],
                "prediction_unit":answer["prediction_unit"],"prediction_basis":answer["prediction_basis"],
                "prediction_profile_id":PROFILE,"ml_fallback_reasons":[],
                "reasons":["Eligible experimental ML estimate attached separately; no numerical treatment efficiency or extra ranking score is inferred.",
                           "Catalyst grade and recovery are unmodelled, so this remains a conditional research candidate."]+answer["limitations"]},[]

    def recommend(self,scenario):
        scenario=dict(scenario)
        validate_scenario(scenario)
        if "light_type" in scenario:
            light=str(scenario["light_type"]).strip().casefold()
            scenario["light_type"]={"uv":"UV","uva":"UVA","uvb":"UVB","uvc":"UVC"}.get(light,light)
        if "available_equipment" in scenario:
            if not all(isinstance(item,str) for item in scenario["available_equipment"]):
                raise ValueError("available_equipment entries must be names.")
            scenario["available_equipment"]=[item.strip().casefold() for item in scenario["available_equipment"]]
        choices=scenario.get("profile_choices",{})
        known_ids=set(self.materials.material_id)
        for material_id,profile_id in choices.items():
            if material_id not in known_ids or self.profile_materials.get(profile_id)!=material_id:
                raise ValueError(f"Profile choice {material_id}: {profile_id} is not a registered matching formulation.")
        pollutant=normalise_pollutant(scenario.get("pollutant_id"),self.pollutants)
        if pollutant:
            scenario["pollutant_id"]=pollutant
        all_details=[]
        rows=[]
        for material in self.materials.sort_values("material_id").to_dict("records"):
            material_id=material["material_id"]
            family=self.evidence.loc[(self.evidence.material_id==material_id)&(self.evidence.pollutant_id==pollutant)]
            selected_id=choices.get(material_id)
            candidates=[]
            ml_reasons=[]
            for profile_id,records in family.groupby("profile_id",sort=True):
                if selected_id and profile_id!=selected_id:
                    continue
                candidates.append(self._profile(profile_id,records,scenario))
            # The dataset profile is opt-in and never silently assigned to a literature grade.
            if pollutant and material_id=="M02" and selected_id==PROFILE:
                ml,ml_reasons=self._ml_profile(scenario)
                if ml is not None:
                    candidates.append(ml)
            for candidate in candidates:
                lo,hi=score_bounds(candidate,self.config["weights"])
                candidate.update(score_min=lo,score_max=hi)
            if candidates:
                # Documented conservative profile selection, never averaging unknown ratings.
                candidates.sort(key=lambda c:(STATUS_ORDER[c["status"]],-c["score_min"],c["profile_id"]))
                chosen=candidates[0]
                alternatives=[c["profile_id"] for c in candidates[1:]
                              if c["status"]==chosen["status"] and c["score_max"]>=chosen["score_min"]
                              and chosen["score_max"]>=c["score_min"]]
                rank_eligible=(chosen["profile_accepted"] and (chosen["status"]=="supported" or
                               (chosen["status"]=="conditional" and scenario.get("allow_conditional_ranking",False))))
                row={k:chosen[k] for k in ["status","profile_id","formulation","suitability","setup","recovery",
                     "prediction","prediction_target","prediction_unit","prediction_basis","prediction_profile_id","source_scope"]}
                row.update(material_id=material_id,material_name=material["material_name"],rank_eligible=rank_eligible,
                           score_min=chosen["score_min"] if rank_eligible else None,
                           score_max=chosen["score_max"] if rank_eligible else None,
                           evidence_ids=";".join(chosen["evidence_ids"]),source_ids=";".join(chosen["source_ids"]),
                           related_family_evidence_ids=";".join(sorted(family.evidence_id)),
                           profile_selection_uncertain=bool(alternatives),alternative_profile_ids=";".join(alternatives),
                           ml_fallback_reason="; ".join(ml_reasons),reason=" ".join(chosen["reasons"]))
                all_details.extend(candidates)
            else:
                reason="No verified profile evidence for this material and pollutant in the bounded database."
                if not pollutant:
                    reason="Pollutant is outside the three pollutant evidence catalogue; no material recommendation is inferred."
                if selected_id and len(family):
                    reason="Related family evidence exists, but none applies to the explicitly chosen profile."
                row={"material_id":material_id,"material_name":material["material_name"],"status":"insufficient_evidence",
                     "profile_id":selected_id,"formulation":None,"suitability":None,"setup":None,"recovery":None,
                     "rank_eligible":False,"score_min":None,"score_max":None,"prediction":None,
                     "prediction_target":None,"prediction_unit":None,"prediction_basis":None,"prediction_profile_id":None,
                     "source_scope":"no_applicable_record","evidence_ids":"","source_ids":"",
                     "related_family_evidence_ids":";".join(sorted(family.evidence_id)),
                     "profile_selection_uncertain":False,"alternative_profile_ids":"",
                     "ml_fallback_reason":"; ".join(ml_reasons),"reason":reason}
            rows.append(row)
            row["source_urls"]="; ".join(self.source_urls[source_id] for source_id in row["source_ids"].split(";") if source_id in self.source_urls)
        top=rank_intervals(rows)
        sensitivity=[]
        for weights in self.config["alternative_weights"]:
            alternate=[]
            for row in rows:
                item=dict(row)
                if item["rank_eligible"]:
                    item["score_min"],item["score_max"]=score_bounds(item,weights)
                alternate.append(item)
            sensitivity.append({"weights":weights,"top_candidates":rank_intervals(alternate)})
        winner=top[0] if len(top)==1 else None
        winner_status=next((row["status"] for row in rows if row["material_id"]==winner),None)
        summary={"pollutant_id":pollutant,"request_supported":pollutant is not None,
                 "all_materials_assessed":len(rows),"ranked_candidates":sum(r["rank_eligible"] for r in rows),
                 "top_candidates":top,"unique_policy_winner":winner,
                 "recommendation_type":("unique source matched policy candidate" if winner_status=="supported" else "unique conditional policy candidate") if winner else ("uncertain shortlist" if top else "no justified ranking"),
                 "ranking_scope":"Among scored candidates and chosen profiles only; unscored evidence gaps can conceal other effective materials.",
                 "weight_sensitive":any(item["top_candidates"]!=top for item in sensitivity),
                 "alternative_weight_results":sensitivity,"score_meaning":self.config["score_meaning"],
                 "sensitivity_scope":"Two alternate weight choices with chosen material profiles held fixed; not proof of global ranking robustness.",
                 "profile_selection_policy":"Within each family: status, then largest lower score bound, then profile ID for stable display. Overlapping profile alternatives are flagged.",
                 "assumptions":self.config["design_assumptions"]+[
                     f"Study profile proposals accepted: {scenario.get('consider_study_profiles',False)}.",
                     f"Conditional research candidates included in ranking: {scenario.get('allow_conditional_ranking',False)}.",
                     "Matching a literature observation is not an independent validation or proof of the requested performance.",
                     "No source quantity or ML prediction is numerically added to the decision score."],
                 "scenario":scenario}
        frame=pd.DataFrame(rows)
        for column in ["preference_tier","rank_best","rank_worst"]:
            frame[column]=frame[column].astype("Int64")
        frame["_status_order"]=frame.status.map(STATUS_ORDER)
        frame=frame.sort_values(["preference_tier","_status_order","material_id"],na_position="last").drop(columns="_status_order").reset_index(drop=True)
        frame.attrs["summary"]=summary
        frame.attrs["profile_assessments"]=all_details
        return frame


def recommend(scenario):
    """Return 15 rows; explanations and profile details also live in DataFrame attrs."""
    return RecommendationEngine().recommend(scenario)


def export_result(frame,prefix):
    prefix=Path(prefix)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    frame.to_csv(prefix.with_suffix(".csv"),index=False)
    prefix.with_suffix(".json").write_text(json.dumps(frame.attrs["summary"],indent=2),encoding="utf-8")
    prefix.with_name(prefix.name+"_profiles.json").write_text(json.dumps(frame.attrs["profile_assessments"],indent=2),encoding="utf-8")


def load_demo(name):
    if name=="demo_ml":
        scenario=json.loads((ROOT / "config/demo_holdout_scenario.json").read_text())
        scenario.pop("material_id",None)
        scenario.pop("profile_id",None)
        scenario.update(requested_endpoint="qualitative_remediation",prediction_endpoint="mlogk",include_ml=True,
                        profile_choices={"M02":PROFILE},consider_study_profiles=True,allow_conditional_ranking=True,
                        available_equipment=["mixer","centrifuge","filtration"])
        return scenario
    if name=="demo_dark":
        return dict(load_demo("demo_ml"),light_type="dark")
    if name=="demo_unknown":
        return dict(load_demo("demo_ml"),pollutant_id="unknown_pollutant")
    if name=="demo_lead":
        return {"pollutant_id":"lead_ii","pH":5,"dose_g_L":4,"concentration_mg_L":200,
                "temperature_C":25,"time_min":10,"light_type":"dark","water_matrix":"laboratory_solution",
                "available_equipment":["mixer","centrifuge","filtration"],"profile_choices":{"M13":"P09"},
                "consider_study_profiles":True,"allow_conditional_ranking":True,"include_ml":False,
                "requested_endpoint":"removal_percent","required_removal_percent":90,
                "demo_note":"Literature matched hydroxyapatite batch case; no new experiment or guaranteed treatment outcome."}
    raise ValueError("Unknown demonstration scenario")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",choices=["demo_ml","demo_dark","demo_unknown","demo_lead"],default="demo_ml")
    parser.add_argument("--input",type=Path,help="Optional custom scenario JSON, instead of a named demo")
    args=parser.parse_args()
    scenario=json.loads(args.input.read_text()) if args.input else load_demo(args.scenario)
    frame=recommend(scenario)
    label=args.input.stem if args.input else args.scenario
    export_result(frame,ROOT / "outputs" / f"ranking_{label}")
    print(json.dumps(frame.attrs["summary"],indent=2))
    print(frame[["material_id","material_name","status","preference_tier","score_min","score_max","prediction"]].to_string(index=False))


if __name__=="__main__":
    main()
