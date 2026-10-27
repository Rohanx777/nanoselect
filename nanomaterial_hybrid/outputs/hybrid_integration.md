# Stage D hybrid integration

## Working local interface

`from src.recommend import recommend` exposes the integrated function. It returns a pandas table with exactly 15 material families. `table.attrs['summary']` contains the shortlist, scope, assumptions and weight checks; `table.attrs['profile_assessments']` contains the detailed formulation and source matching results.

No website is required. Run `.\.venv\Scripts\python.exe -m src.recommend --scenario demo_ml`, or open `04_hybrid_demo.ipynb` using the notebook launcher. Saved models and cached evidence are reused; no internet or retraining is needed for the examples.

## Example results

| Scenario | Top candidates among scored profiles | Result type | Ranked candidates |
|---|---|---|---:|
| demo_ml | Titanium dioxide, Zinc oxide, Carbon nanotubes | uncertain shortlist | 3 |
| demo_dark | Carbon nanotubes | unique conditional policy candidate | 1 |
| demo_unknown | No justified candidate | no justified ranking | 0 |
| demo_lead | Nano hydroxyapatite | unique source matched policy candidate | 5 |

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

Run `.\.venv\Scripts\python.exe -m src.recommend --input config\my_scenario.json`. Results are written as CSV, summary JSON and profile explanation JSON in outputs. These contain source IDs, URLs and reasons for unsupported or incompatible candidates.

## Next stage

Perform the final demonstration checks, prepare a short presentation walkthrough and verify the whole demo from a clean local session. The working integration is complete; no additional model training is needed.
