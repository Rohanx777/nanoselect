"""Package the Stage D notebook and reproducible example outputs without training."""
import json

from .recommend import ROOT,RecommendationEngine,export_result,load_demo


def main():
    engine=RecommendationEngine()
    examples=[]
    material_names=engine.materials.set_index("material_id").material_name.to_dict()
    for name in ["demo_ml","demo_dark","demo_unknown","demo_lead"]:
        scenario=load_demo(name)
        (ROOT / f"config/{name}.json").write_text(json.dumps(scenario,indent=2),encoding="utf-8")
        frame=engine.recommend(scenario)
        export_result(frame,ROOT / f"outputs/ranking_{name}")
        summary=frame.attrs["summary"]
        top=", ".join(material_names[item] for item in summary["top_candidates"]) or "No justified candidate"
        examples.append((name,top,summary["recommendation_type"],summary["ranked_candidates"]))
    rows="\n".join(f"| {name} | {top} | {kind} | {count} |" for name,top,kind,count in examples)
    report=f"""# Stage D hybrid integration

## Working local interface

`from src.recommend import recommend` exposes the integrated function. It returns a pandas table with exactly 15 material families. `table.attrs['summary']` contains the shortlist, scope, assumptions and weight checks; `table.attrs['profile_assessments']` contains the detailed formulation and source matching results.

No website is required. Run `.\\.venv\\Scripts\\python.exe -m src.recommend --scenario demo_ml`, or open `04_hybrid_demo.ipynb` using the notebook launcher. Saved models and cached evidence are reused; no internet or retraining is needed for the examples.

## Example results

| Scenario | Top candidates among scored profiles | Result type | Ranked candidates |
|---|---|---|---:|
{rows}

All four results include all 15 families. Unknown pairs remain visible with no score or rank. The light change case can recommend only a conditional research candidate, not a guaranteed treatment. The lead case is deliberately matched to the published hydroxyapatite batch observation and demonstrates source matching, not independent validation or a universal material winner.

## Policy and score interpretation

The declared weights are 60 percent treatment suitability, 25 percent setup compatibility and 15 percent recovery practicality. The ordinal ratings are documented in `config/ranking.json`. Suitability one means partial relevance; it is not an estimate of removal. Two requires a matched reported removal observation and a stated target. The score measures this project policy, not physical efficiency, accuracy or a probability.

An unknown criterion contributes a full zero to two interval. No midpoint is invented and weights are not renormalised. Candidate A certainly outranks B under the declared policy only if A's lower score exceeds B's upper score. Frontiers are labelled preference tiers; overlapping candidates remain an uncertain shortlist. Rank best and rank worst show the interval of possible preference positions. ID ordering is only for stable display within a tier. Tiers are not claims that every pair in different frontiers is strictly ordered.

Within a family, the chosen profile is selected by applicability status, then largest lower score bound, then stable profile ID. Other overlapping profiles are flagged. Weight checks use 50/30/20 and 70/20/10 with chosen profiles held fixed. Stability under these two alternatives is not proof of global robustness.

## Scientific boundaries enforced

- ML is attached only to the explicitly selected `dataset_unspecified_tio2` profile with a separate `prediction_endpoint=mlogk` request. Named literature grades never inherit the dataset model.
- ML prediction magnitude is not added to a decision score, and simply having ML does not increase a candidate's score.
- The published endpoints stay separate. Capacity, rate constant, percent removal and the reported mlogk are not converted into one performance metric.
- The source matching rule checks pH, initial concentration, dose, temperature and contact time. It also requires the laboratory solution assumption and available setup. A source match supports the literature observation; it does not promise repeat performance.
- Composite results, unknown recovery and unverified catalogue property ranges cannot populate missing criteria.
- Specific study formulations must be selected or explicitly accepted as proposed candidates. Conditional candidates receive ranks only when the scenario explicitly permits it.
- The supported evidence catalogue contains sulfamethoxazole, amaranth dye and dissolved lead II. Other pollutants do not receive invented evidence rankings even if the standalone model has a broader numerical category list.

## Scenario fields to edit

Use `config/demo_ml.json` or `config/demo_lead.json` as a starting point. Main inputs are pollutant_id, pH, concentration_mg_L, dose_g_L, time_min, temperature_C, light_type and available_equipment. Missing optional inputs remain unknown. Profile choices map a family ID to a documented profile; consider_study_profiles explicitly allows other study formulations as proposals.

For a source based removal target set requested_endpoint to removal_percent and required_removal_percent to a value from zero to one hundred. For an optional ML estimate set include_ml true, prediction_endpoint mlogk and choose the unspecified dataset profile for M02. That optional estimate is separate from the ranking objective.

Run `.\\.venv\\Scripts\\python.exe -m src.recommend --input config\\my_scenario.json`. Results are written as CSV, summary JSON and profile explanation JSON in outputs. These contain source IDs, URLs and reasons for unsupported or incompatible candidates.

## Next stage

Perform the final demonstration checks, prepare a short presentation walkthrough and verify the whole demo from a clean local session. The working integration is complete; no additional model training is needed.
"""
    (ROOT / "outputs/hybrid_integration.md").write_text(report,encoding="utf-8")
    def markdown(cell_id,text):
        return {"cell_type":"markdown","id":cell_id,"metadata":{},"source":[text]}
    def code(cell_id,lines):
        return {"cell_type":"code","id":cell_id,"metadata":{},"execution_count":None,"outputs":[],"source":[line+"\n" for line in lines]}
    cells=[
        markdown("intro","# Hybrid nanomaterial selection demonstration\nLocal demonstration using cached research and a saved TiO2 model. All 15 material families appear. A decision score is not removal percentage, probability or ML accuracy. Unsupported candidates receive no invented score."),
        code("imports",["from pathlib import Path","import json, sys","import pandas as pd","from IPython.display import display, Markdown","ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent","if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))","from src.recommend import RecommendationEngine, load_demo","engine = RecommendationEngine()","columns = ['material_id', 'material_name', 'profile_id', 'status', 'preference_tier', 'score_min', 'score_max', 'prediction', 'prediction_target']"]),
        markdown("scenario-note","## Set water and equipment conditions\nThese published SMX conditions are a held out model example. The scenario explicitly accepts study profiles and conditional candidates as research proposals. Edit this dictionary or load your own scenario JSON."),
        code("scenario",["scenario = load_demo('demo_ml')","scenario"]),
        code("rank",["ranking = engine.recommend(scenario)","display(ranking[columns])","print('Top candidate IDs:', ranking.attrs['summary']['top_candidates'])","print('Result:', ranking.attrs['summary']['recommendation_type'])","print('Score meaning:', ranking.attrs['summary']['score_meaning'])"]),
        markdown("explanation-note","## Inspect the prediction and its limits\nThe numerical mlogk output belongs to the unspecified TiO2 dataset profile. It is not assigned to the source's brookite or anatase formulations, and it does not break the tied evidence shortlist."),
        code("explain",["tio2 = ranking.set_index('material_id').loc['M02']","print(tio2['reason'])","print('Prediction profile:', tio2['prediction_profile_id'])","print('Sources:', tio2['source_urls'])","print('Alternate weights:', ranking.attrs['summary']['alternative_weight_results'])"]),
        markdown("dark-note","## Change available light\nThe documented photocatalytic routes cannot run in the dark. CNT adsorption remains a conditional research candidate; a unique policy candidate is not a performance guarantee."),
        code("dark",["dark = engine.recommend(dict(scenario, light_type='dark'))","display(dark[columns])","print(dark.attrs['summary']['recommendation_type'], dark.attrs['summary']['top_candidates'])"]),
        markdown("lead-note","## Source matched lead example\nThis case deliberately matches the published hydroxyapatite batch observation. The 100 point policy score means complete checked rubric support, not 100 percent removal. The observed removal and source limitations remain separate."),
        code("lead",["lead = engine.recommend(load_demo('demo_lead'))","display(lead[columns])","print('Policy winner:', lead.attrs['summary']['unique_policy_winner'])","print(lead.set_index('material_id').loc['M13', 'reason'])","print('Source:', lead.set_index('material_id').loc['M13', 'source_urls'])"]),
        markdown("unknown-note","## Unsupported pollutant\nNo material performance or rank is fabricated when the pollutant is outside the evidence catalogue."),
        code("unknown",["unknown = engine.recommend(load_demo('demo_unknown'))","display(unknown[['material_id', 'material_name', 'status', 'score_min', 'prediction']])","print(unknown.attrs['summary']['recommendation_type'])"]),
        markdown("end","## What the prototype establishes\nThe local system integrates conditional evidence screening, fixed decision rules, interval ranking and one evaluated ML module. It covers all 15 families as candidates, with numerical prediction only in its documented subset. No independent study validation, lab validation or drinking water certification is claimed. Read outputs/hybrid_integration.md and outputs/model_evaluation.md for scope and exact metrics.")
    ]
    notebook={"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":cells}
    (ROOT / "notebooks/04_hybrid_demo.ipynb").write_text(json.dumps(notebook,indent=2),encoding="utf-8")
    print("Built integrated notebook, four scenario files and four result exports without training.")


if __name__=="__main__":
    main()
