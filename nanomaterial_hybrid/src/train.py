"""Stage C training with an untouched input-group test split and grouped CV."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import time

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from sklearn.model_selection import GroupKFold,GroupShuffleSplit,GridSearchCV
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder,StandardScaler

from .predict import ROOT,NUMERIC,FEATURES,build_domain,assess_inputs,scenario_from_row


def preprocessing():
    return ColumnTransformer([
        ("numeric",Pipeline([("impute",SimpleImputer(strategy="median")),("scale",StandardScaler())]),NUMERIC),
        ("pollutant",OneHotEncoder(handle_unknown="ignore",sparse_output=False),["SMILES"])
    ])


def pipeline(model):
    return Pipeline([("preprocess",preprocessing()),("model",model)])


def metrics(actual,predicted):
    return {"n":len(actual),"mae":float(mean_absolute_error(actual,predicted)),
            "rmse":float(np.sqrt(mean_squared_error(actual,predicted))),
            "r2":float(r2_score(actual,predicted)) if len(actual)>1 else None}


def make_split(frame,config):
    split=GroupShuffleSplit(n_splits=1,test_size=config["test_fraction"],random_state=config["seed"])
    train_idx,test_idx=next(split.split(frame,groups=frame.input_group_id))
    train=frame.iloc[train_idx].copy()
    test=frame.iloc[test_idx].copy()
    assert not set(train.input_group_id)&set(test.input_group_id)
    return train,test


def plot_evaluation(actual,predicted,winner):
    fig,ax=plt.subplots(figsize=(6.5,5))
    ax.scatter(actual,predicted,alpha=.75,label=f"Held out records (n={len(actual)})")
    bounds=[min(np.min(actual),np.min(predicted)),max(np.max(actual),np.max(predicted))]
    ax.plot(bounds,bounds,"--",color="gray",label="Perfect agreement")
    ax.set(xlabel="Measured mlogk (reported target)",ylabel="Predicted mlogk (reported target)",
           title=f"{winner}: preliminary holdout evaluation")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(ROOT / "outputs/predicted_vs_measured.png",dpi=160)
    plt.close(fig)


def main():
    started=time.perf_counter()
    config=json.loads((ROOT / "config/training.json").read_text())
    file=ROOT / "data/processed/tio2_audited.csv"
    frame=pd.read_csv(file)
    train,test=make_split(frame,config)
    folds=list(GroupKFold(n_splits=config["cv_folds"]).split(train,groups=train.input_group_id))
    split_rows=[]
    for split_name,part in [("train",train),("test",test)]:
        for row in part.itertuples():
            split_rows.append({"source_row":row.source_row,"input_group_id":row.input_group_id,
                               "pollutant":row.Molecule_Name,"split":split_name})
    pd.DataFrame(split_rows).to_csv(ROOT / "outputs/train_test_split.csv",index=False)
    cv_rows=[]
    for fold,(a,b) in enumerate(folds,1):
        assert not set(train.iloc[a].input_group_id)&set(train.iloc[b].input_group_id)
        for position in b:
            row=train.iloc[position]
            cv_rows.append({"fold":fold,"source_row":int(row.source_row),"input_group_id":row.input_group_id})
    pd.DataFrame(cv_rows).to_csv(ROOT / "outputs/cv_validation_folds.csv",index=False)
    choices=[
        ("Dummy median",DummyRegressor(strategy="median"),{}),
        ("Ridge",Ridge(),{"model__alpha":config["ridge_alphas"]}),
        ("Random Forest",RandomForestRegressor(n_estimators=config["forest_trees"],n_jobs=config["forest_jobs"],random_state=config["seed"]),
         {"model__max_depth":config["forest_max_depths"],"model__min_samples_leaf":config["forest_min_samples_leaf"]})
    ]
    records=[]
    fitted={}
    candidate_rows=[]
    for name,model,params in choices:
        print(f"Cross validation: {name}",flush=True)
        search=GridSearchCV(pipeline(model),params,cv=folds,scoring="neg_mean_absolute_error",refit=True,n_jobs=1,error_score="raise")
        search.fit(train[FEATURES],train.mlogk)
        best=search.best_index_
        scores=[float(-search.cv_results_[f"split{i}_test_score"][best]) for i in range(len(folds))]
        records.append({"model":name,"cv_mae_mean":float(np.mean(scores)),"cv_mae_std":float(np.std(scores)),
                        "best_parameters":json.dumps(search.best_params_),"fold_mae":scores})
        fitted[name]=search.best_estimator_
        for i,param in enumerate(search.cv_results_["params"]):
            candidate_rows.append({"model":name,"parameters":json.dumps(param),
                                   "cv_mae_mean":float(-search.cv_results_["mean_test_score"][i]),
                                   "cv_mae_std":float(search.cv_results_["std_test_score"][i])})
    table=pd.DataFrame(records).sort_values(["cv_mae_mean","model"])
    table.to_csv(ROOT / "outputs/model_comparison_cv.csv",index=False)
    pd.DataFrame(candidate_rows).to_csv(ROOT / "outputs/cv_candidates.csv",index=False)
    # Selection is complete before evaluating any test outcomes.
    winner=table.iloc[0].model
    selected=fitted[winner]
    baseline=fitted["Dummy median"]
    pred=selected.predict(test[FEATURES])
    baseline_pred=baseline.predict(test[FEATURES])
    final_metrics=metrics(test.mlogk,pred)
    baseline_metrics=metrics(test.mlogk,baseline_pred)
    cv_best=table.loc[table.model==winner].iloc[0]
    cv_baseline=table.loc[table.model=="Dummy median"].iloc[0]
    cv_gain=1-cv_best.cv_mae_mean/cv_baseline.cv_mae_mean
    test_gain=1-final_metrics["mae"]/baseline_metrics["mae"]
    fold_wins=sum(a<b for a,b in zip(cv_best.fold_mae,cv_baseline.fold_mae))
    policy=config["acceptance_policy"]
    gate={"selected_nonbaseline":winner!="Dummy median",
          "cv_mae_improvement":bool(cv_gain>=policy["minimum_relative_mae_improvement"]),
          "majority_cv_folds":bool(fold_wins>=policy["minimum_cv_folds_beating_baseline"]),
          "test_mae_improvement":bool(test_gain>=policy["minimum_relative_mae_improvement"]),
          "positive_test_r2":bool(not policy["require_positive_test_r2"] or (final_metrics["r2"] is not None and final_metrics["r2"]>0))}
    enabled=all(gate.values())
    domain=build_domain(train,config["domain_policy"])
    accepted=[]
    checks=[]
    for _,row in test.iterrows():
        check=assess_inputs(scenario_from_row(row),domain)
        accepted.append(check["eligible"])
        checks.append("; ".join(check["reasons"]))
    output=test[["source_row","input_group_id","Molecule_Name","mlogk"]].copy()
    output["predicted_mlogk"]=pred
    output["baseline_mlogk"]=baseline_pred
    output["eligible_under_domain_policy"]=accepted
    output["fallback_reason"]=checks
    output.to_csv(ROOT / "outputs/test_predictions.csv",index=False)
    eligible=np.asarray(accepted,dtype=bool)
    eligible_metrics=metrics(test.mlogk.to_numpy()[eligible],pred[eligible]) if eligible.any() else None
    limits=["Preliminary input group holdout; missing study identifiers prevent independent study validation.",
            "Only TiO2 family and known pollutants; catalyst phase, grade, size, surface area and reactor geometry are unmodelled.",
            "Only the reported mlogk target is predicted; logarithm base is unverified so no physical k or removal percentage is returned.",
            "Laboratory solution is a demonstration assumption; water matrix was not recorded per row, and real water effects are unvalidated.",
            "Range and nearest condition checks are heuristics, not calibrated prediction intervals or proof of applicability.",
            "Pollutant identity is encoded categorically; no generalisation to unseen chemicals is supported."]
    card={"model_name":winner,"enabled_for_prototype":enabled,"artifact_filename":"tio2_pipeline.joblib" if enabled else None,
          "target":"mlogk","target_definition":"reported -log(k), k in min^-1; base unverified",
          "input_features":FEATURES,"train_rows":len(train),"test_rows":len(test),
          "train_groups":train.input_group_id.nunique(),"test_groups":test.input_group_id.nunique(),
          "split_strategy":"GroupShuffleSplit on exact input groups; GroupKFold CV within training only",
          "study_independent_validation":False,"random_seed":config["seed"],
          "selected_parameters":json.loads(cv_best.best_parameters),"cv_mae":float(cv_best.cv_mae_mean),
          "cv_mae_std":float(cv_best.cv_mae_std),"cv_relative_mae_gain":float(cv_gain),
          "cv_fold_wins_against_baseline":int(fold_wins),"test_relative_mae_gain":float(test_gain),
          "test_metrics":final_metrics,"baseline_test_metrics":baseline_metrics,
          "eligible_test_rows":int(eligible.sum()),"eligible_test_metrics":eligible_metrics,
          "usefulness_checks":gate,"acceptance_policy":policy,
          "data_sha256":hashlib.sha256(file.read_bytes()).hexdigest(),
          "training_config_sha256":hashlib.sha256((ROOT / "config/training.json").read_bytes()).hexdigest(),
          "package_versions":{"python":platform.python_version(),"scikit_learn":sklearn.__version__,"pandas":pd.__version__,"numpy":np.__version__,"joblib":joblib.__version__},
          "limitations":limits,"elapsed_training_seconds":round(time.perf_counter()-started,2)}
    model_dir=ROOT / "models"
    model_dir.mkdir(exist_ok=True)
    if enabled:
        joblib.dump(selected,model_dir / card["artifact_filename"])
        card["artifact_sha256"]=hashlib.sha256((model_dir / card["artifact_filename"]).read_bytes()).hexdigest()
    # The saved fitted model uses training rows only; test observations are not refitted.
    (model_dir / "model_card.json").write_text(json.dumps(card,indent=2),encoding="utf-8")
    (model_dir / "domain.json").write_text(json.dumps(domain,indent=2),encoding="utf-8")
    eligible_names=[p["display_name"] for p in domain["pollutants"].values() if p["eligible_category"]]
    (ROOT / "outputs/prediction_supported_pollutants.json").write_text(json.dumps(eligible_names,indent=2),encoding="utf-8")
    preferred=train.loc[train.Molecule_Name.eq("Sulfamethoxazole")]
    if preferred.empty or not domain["pollutants"][preferred.iloc[0].SMILES]["eligible_category"]:
        preferred=train.loc[train.Molecule_Name.isin(eligible_names)]
    if len(preferred):
        example=preferred.iloc[0]
        scenario=scenario_from_row(example)
        scenario["demo_note"]="Existing training conditions used to demonstrate API operation; this is not a new validation experiment."
        scenario["source_row"]=int(example.source_row)
        (ROOT / "config/demo_ml_scenario.json").write_text(json.dumps(scenario,indent=2),encoding="utf-8")
    eligible_holdout=test.iloc[np.flatnonzero(eligible)]
    preferred_holdout=eligible_holdout.loc[eligible_holdout.Molecule_Name.eq("Sulfamethoxazole")]
    if preferred_holdout.empty:
        preferred_holdout=eligible_holdout
    if len(preferred_holdout):
        example=preferred_holdout.iloc[0]
        scenario=scenario_from_row(example)
        scenario["demo_note"]="First eligible sulfamethoxazole holdout row, otherwise first eligible holdout row; chosen by inputs, not smallest prediction error."
        scenario["source_row"]=int(example.source_row)
        (ROOT / "config/demo_holdout_scenario.json").write_text(json.dumps(scenario,indent=2),encoding="utf-8")
    plot_evaluation(test.mlogk,pred,winner)
    report=f"""# Stage C model evaluation

## Result

Selected **{winner}** by the lowest training cross validation MAE. Prototype numerical prediction enabled: **{enabled}**. No model ranking used final test outcomes. The predeclared usefulness checks are recorded in the model card; these are pragmatic prototype criteria, not a chemical standard.

## Data and evaluation

{len(frame)} original audited records were split into {len(train)} training and {len(test)} test rows, with zero identical input groups shared. Five fold grouped cross validation used training rows only. Identical conditions with different measured outcomes stayed in the same split. Study identifiers are unavailable, so results are preliminary and may benefit from shared studies or apparatus across splits. No independent lab validation was performed.

Only I, T, D, C0, pH and exact SMILES category enter the pipeline. Numeric imputation and scaling and categorical encoding are fitted inside each CV training fold. Size, surface area, source row and target derived fields are excluded. Literature observations from Stage B are not pooled into this dataset.

## Final test metrics

All errors are in the reported mlogk target, not percentage removal.

| Model | MAE | RMSE | R squared |
|---|---:|---:|---:|
| Selected {winner} | {final_metrics['mae']:.4f} | {final_metrics['rmse']:.4f} | {final_metrics['r2']:.4f} |
| Median baseline | {baseline_metrics['mae']:.4f} | {baseline_metrics['rmse']:.4f} | {baseline_metrics['r2']:.4f} |

Relative test MAE improvement over baseline: {100*test_gain:.1f} percent. This is an error reduction, not prediction accuracy or pollutant removal efficiency. The complete CV comparison is `model_comparison_cv.csv`, including Ridge and Random Forest; all nine configurations appear in `cv_candidates.csv`.

## Domain coverage

{len(eligible_names)} pollutant categories have at least the required five distinct training conditions. {int(eligible.sum())} of {len(test)} held out rows pass the provisional range and nearest condition policy. All row predictions above are evaluator diagnostics, including rows a deployed predictor would refuse; eligible subset metrics are separate in the model card. Do not report the overall metrics as a guarantee for every pollutant or operating range. Per pollutant test subsets are small.

The saved artifact is fitted only on training rows. The runtime requires the unspecified dataset TiO2 profile, UV light, a laboratory solution assumption and requested endpoint mlogk. It refuses missing or nonfinite values, unseen or sparsely represented pollutants, different materials, named catalyst profiles and conditions outside the declared support. It does not output an uncertainty interval.

## Demonstration

Run `.\\.venv\\Scripts\\python.exe -m src.predict`. The saved example uses an actual sulfamethoxazole training condition when available. Its demonstration prediction is not part of held out validation. `exact_training_conditions` makes that distinction explicit.

No logarithm base was invented. The output is the original reported negative log rate target. Do not convert it into k or removal percentage. The model cannot rank TiO2 against 14 other families by numerical efficiency; the next stage combines this limited module with source backed evidence and deterministic decision rules.

Method references: https://scikit-learn.org/stable/modules/cross_validation.html and https://scikit-learn.org/stable/common_pitfalls.html
"""
    (ROOT / "outputs/model_evaluation.md").write_text(report,encoding="utf-8")
    nb={"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":[
        {"cell_type":"markdown","id":"scope","metadata":{},"source":["# TiO2 model training and evaluation\n","Stage C uses the saved model and metrics. It does not retrain during the demonstration. Validation is preliminary: exact input groups are separated, but independent study IDs are unavailable. Outputs are in reported mlogk units, not removal percentages."]},
        {"cell_type":"code","id":"load","metadata":{},"execution_count":None,"outputs":[],"source":["from pathlib import Path\n","import json, sys\n","import pandas as pd\n","from IPython.display import Image, display\n","ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\n","if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))\n","from src.predict import TiO2Predictor\n","card = json.loads((ROOT / 'models/model_card.json').read_text())\n","print('Selected model:', card['model_name'])\n","print('Training rows:', card['train_rows'], '| held out rows:', card['test_rows'])\n","print('Numerical prototype enabled:', card['enabled_for_prototype'])\n","pd.read_csv(ROOT / 'outputs/model_comparison_cv.csv')[['model', 'cv_mae_mean', 'cv_mae_std', 'best_parameters']]"]},
        {"cell_type":"markdown","id":"holdout-note","metadata":{},"source":["## Untouched final test results\n","The model was selected using training CV before evaluating these test outcomes. R squared is not percent accuracy. MAE is in the reported transformed target."]},
        {"cell_type":"code","id":"metrics","metadata":{},"execution_count":None,"outputs":[],"source":["pd.DataFrame({'Selected model': card['test_metrics'], 'Median baseline': card['baseline_test_metrics']}).T"]},
        {"cell_type":"code","id":"plot","metadata":{},"execution_count":None,"outputs":[],"source":["display(Image(filename=str(ROOT / 'outputs/predicted_vs_measured.png')))"]},
        {"cell_type":"code","id":"coverage","metadata":{},"execution_count":None,"outputs":[],"source":["print('Held out rows passing domain policy:', card['eligible_test_rows'], '/', card['test_rows'])\n","print('Eligible subset metrics:', card['eligible_test_metrics'])\n","print('This subset is not a calibrated confidence region.')"]},
        {"cell_type":"markdown","id":"demo-note","metadata":{},"source":["## Run one numerical prediction\n","Use the first eligible held out SMX condition where available, selected by inputs rather than prediction error. This is a published test observation, not a new lab experiment. The default command line example separately uses a training condition and labels it explicitly."]},
        {"cell_type":"code","id":"predict","metadata":{},"execution_count":None,"outputs":[],"source":["demo_file = ROOT / 'config/demo_holdout_scenario.json'\n","if not demo_file.exists(): demo_file = ROOT / 'config/demo_ml_scenario.json'\n","scenario = json.loads(demo_file.read_text())\n","predictor = TiO2Predictor()\n","answer = predictor.predict(scenario)\n","print('Scenario:', scenario)\n","print({k: answer[k] for k in ['status', 'prediction', 'prediction_target', 'exact_training_conditions', 'reasons']})\n","test_predictions = pd.read_csv(ROOT / 'outputs/test_predictions.csv')\n","test_predictions.loc[test_predictions.source_row.eq(scenario['source_row']), ['Molecule_Name', 'mlogk', 'predicted_mlogk']]"]},
        {"cell_type":"markdown","id":"fallback-note","metadata":{},"source":["## Check an unsupported request\n","Methylene blue is absent from this training dataset. The API must return evidence only rather than fabricate a numerical prediction."]},
        {"cell_type":"code","id":"reject","metadata":{},"execution_count":None,"outputs":[],"source":["unsupported = dict(scenario, pollutant_id='methylene_blue')\n","fallback = predictor.predict(unsupported)\n","print({k: fallback[k] for k in ['status', 'prediction', 'reasons']})"]},
        {"cell_type":"markdown","id":"limits","metadata":{},"source":["## Limits and next stage\n","No independent study or lab validation. Phase, size, surface area, wavelength and matrix effects are unmodelled. No prediction interval is claimed and no inverse log conversion is made. Next: integrate the saved model with deterministic evidence screening and recommendation rules for all 15 families."]}
    ]}
    (ROOT / "notebooks/03_model_evaluation.ipynb").write_text(json.dumps(nb,indent=2),encoding="utf-8")
    print(json.dumps({"winner":winner,"enabled":enabled,"train_rows":len(train),"test_rows":len(test),
                      "test_metrics":final_metrics,"baseline":baseline_metrics,"eligible_test_rows":int(eligible.sum()),
                      "supported_categories":len(eligible_names),"gate":gate},indent=2),flush=True)


if __name__=="__main__":
    main()
