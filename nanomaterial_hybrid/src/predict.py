"""Conservative eligibility checks and saved TiO2 target prediction."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances

ROOT=Path(__file__).resolve().parents[1]
NUMERIC=["I","T","D","C0","pH"]
FEATURES=NUMERIC+["SMILES"]
INPUT_MAP={"I":"light_intensity_mW_cm2","T":"temperature_C","D":"dose_g_L",
           "C0":"concentration_mg_L","pH":"pH"}
PROFILE="dataset_unspecified_tio2"


def build_domain(train, policy):
    """Use training inputs only, never outcomes or final test values."""
    domain={"pollutants":{},"aliases":{},"policy":policy}
    for smiles, part in train.groupby("SMILES",sort=True):
        unique=part[NUMERIC].drop_duplicates()
        names=sorted(set(part.Molecule_Name))
        for name in names:
            domain["aliases"][name.strip().casefold()]=smiles
            domain["aliases"][name.strip().casefold().replace(" ","_")]=smiles
        lower=unique.min().to_numpy(dtype=float)
        upper=unique.max().to_numpy(dtype=float)
        span=upper-lower
        scale=np.where(span>0,span,1.0)
        points=unique.to_numpy(dtype=float)
        if len(points)>1:
            distances=pairwise_distances((points-lower)/scale)
            np.fill_diagonal(distances,np.inf)
            nearest=distances.min(axis=1)
            cutoff=float(np.quantile(nearest,policy["local_distance_quantile"])*policy["local_distance_multiplier"])
        else:
            cutoff=policy["local_distance_floor"]
        cutoff=float(np.clip(cutoff,policy["local_distance_floor"],policy["local_distance_cap"]))
        domain["pollutants"][smiles]={"display_name":names[0],"training_rows":len(part),
            "distinct_conditions":len(unique),"minimum":lower.tolist(),"maximum":upper.tolist(),
            "scale":scale.tolist(),"points":points.tolist(),"distance_limit":cutoff,
            "eligible_category":len(unique)>=policy["minimum_distinct_training_conditions_per_pollutant"]}
    return domain


def assess_inputs(scenario, domain):
    reasons=[]
    if scenario.get("material_id")!="M02":
        reasons.append("This model covers TiO2 M02 only.")
    if scenario.get("profile_id")!=PROFILE:
        reasons.append("Use the explicitly unspecified dataset TiO2 profile; named grades or literature profiles are not validated.")
    if scenario.get("light_type")!="UV":
        reasons.append("The dataset describes UV irradiation; this model does not support dark, visible only or sunlight scenarios.")
    if scenario.get("water_matrix")!="laboratory_solution":
        reasons.append("Only a provisional laboratory solution scenario is permitted; real water matrix effects are unmodelled.")
    if scenario.get("requested_endpoint")!="mlogk":
        reasons.append("Only the reported mlogk target is supported; no percent removal or physical rate conversion.")
    pollutant=scenario.get("pollutant_id")
    smiles=domain["aliases"].get(str(pollutant).strip().casefold())
    if smiles is None:
        reasons.append("Pollutant is absent from the model training categories.")
    values=[]
    for field in NUMERIC:
        name=INPUT_MAP[field]
        value=scenario.get(name)
        if isinstance(value,bool):
            value=None
        try:
            value=float(value)
            if not np.isfinite(value):
                raise ValueError("nonfinite")
        except (TypeError,ValueError):
            reasons.append(f"Missing or nonfinite required input: {name}.")
            value=np.nan
        values.append(value)
    result={"eligible":False,"reasons":reasons,"nearest_condition_distance":None,
            "exact_training_conditions":False,"smiles":smiles,"input_values":values}
    if smiles is None or not np.isfinite(values).all():
        return result
    local=domain["pollutants"][smiles]
    if not local["eligible_category"]:
        reasons.append("Too few distinct training conditions for this pollutant under the declared support policy.")
    values=np.asarray(values)
    lower=np.asarray(local["minimum"])
    upper=np.asarray(local["maximum"])
    outside=(values<lower-1e-10)|(values>upper+1e-10)
    for field in np.asarray(NUMERIC)[outside]:
        reasons.append(f"{INPUT_MAP[field]} is outside the pollutant specific training range.")
    distances=np.sqrt(np.sum(((np.asarray(local["points"])-values)/np.asarray(local["scale"]))**2,axis=1))
    nearest=float(distances.min())
    result["nearest_condition_distance"]=nearest
    result["exact_training_conditions"]=nearest<1e-10
    if nearest>local["distance_limit"]+1e-10:
        reasons.append("Operating condition combination is too far from observed training conditions under the heuristic support rule.")
    result["eligible"]=not reasons
    return result


def scenario_from_row(row):
    scenario={"material_id":"M02","profile_id":PROFILE,"pollutant_id":row["Molecule_Name"],
              "light_type":"UV","water_matrix":"laboratory_solution","requested_endpoint":"mlogk"}
    scenario.update({INPUT_MAP[k]:float(row[k]) for k in NUMERIC})
    return scenario


class TiO2Predictor:
    def __init__(self, model_dir=None):
        self.model_dir=Path(model_dir) if model_dir else ROOT / "models"
        self.card=json.loads((self.model_dir / "model_card.json").read_text(encoding="utf-8"))
        self.domain=json.loads((self.model_dir / "domain.json").read_text(encoding="utf-8"))
        self.pipeline=None

    def predict(self,scenario):
        check=assess_inputs(scenario,self.domain)
        answer={"status":"evidence_only","prediction":None,"prediction_target":"mlogk",
                "prediction_unit":"reported negative log rate target; logarithm base unverified",
                "prediction_basis":"unavailable","reasons":check["reasons"].copy(),
                "nearest_condition_distance":check["nearest_condition_distance"],
                "exact_training_conditions":check["exact_training_conditions"],
                "limitations":self.card["limitations"]}
        if not self.card["enabled_for_prototype"]:
            answer["reasons"].append("The model did not pass the declared usefulness gate.")
        if answer["reasons"]:
            return answer
        if self.pipeline is None:
            # Load only our locally produced trusted artifact; never load arbitrary downloaded pickles.
            artifact=self.model_dir / self.card["artifact_filename"]
            if hashlib.sha256(artifact.read_bytes()).hexdigest()!=self.card["artifact_sha256"]:
                raise ValueError("Saved model artifact does not match the model card hash; regenerate with src.train.")
            self.pipeline=joblib.load(artifact)
            # Fix tree reduction order for repeatable inference on this PC.
            # The saved fit is unchanged; only prediction parallelism changes.
            model=self.pipeline.named_steps.get("model")
            if hasattr(model,"n_jobs"):
                model.n_jobs=1
        row=dict(zip(NUMERIC,check["input_values"]))
        row["SMILES"]=check["smiles"]
        answer.update(status="experimental_ml_prediction",
                      prediction=float(self.pipeline.predict(pd.DataFrame([row],columns=FEATURES))[0]),
                      prediction_basis="preliminary held out input group evaluation; not independent study validation")
        return answer


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--scenario",type=Path,default=ROOT / "config/demo_ml_scenario.json")
    args=parser.parse_args()
    scenario=json.loads(args.scenario.read_text(encoding="utf-8"))
    print(json.dumps(TiO2Predictor().predict(scenario),indent=2))


if __name__=="__main__":
    main()
