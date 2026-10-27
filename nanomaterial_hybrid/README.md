# Nanomaterial hybrid research prototype

All five stages are complete: data audit, the 15 material catalogue, reviewed evidence, an evaluated TiO2 regression model, deterministic hybrid ranking and final local verification.

## Start the completed demo

Double-click **run.bat** in the parent IDP 2026 folder, or **START_DEMO.cmd** here, to open the local **NanoSelect webpage**. Enter inputs and click **Rank materials**. The normal address is **http://127.0.0.1:8765/**. No notebook or retraining is needed. See **START_HERE.md** for the interface instructions. The old notebooks and static HTML preview remain supporting artifacts.

The launcher can be checked without opening a browser using `.\START_DEMO.cmd --check`. Use `.\START_DEMO.cmd --text` for a terminal demonstration. To edit inputs, change **config/my_scenario.json** and run `.\.venv\Scripts\python.exe -m src.recommend --input config\my_scenario.json`.

Final verification passed in fresh processes with external network connections blocked. All 51 tests and the main notebook passed; model artifacts were unchanged. See **outputs/final_verification.md** for the method and per case results. Saved inference uses a single thread to keep floating point reduction order stable on this PC.

## Local environment

Project: `C:\Users\Rohan\Desktop\IDP 2026\nanomaterial_hybrid`.

Base interpreter: `C:\Users\Rohan\AppData\Local\Programs\Python\Python310\python.exe` (Python 3.10.11). The `py` launcher does not detect this installation, so use the explicit interpreter or the project virtual environment.

The following are development reproduction commands, not steps required before every presentation. From this project folder in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m src.acquire
.\.venv\Scripts\python.exe -m src.data_audit
.\.venv\Scripts\python.exe -m src.acquire_evidence
.\.venv\Scripts\python.exe -m src.catalogue
.\.venv\Scripts\python.exe -m src.train
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m src.notebook --execute
.\.venv\Scripts\python.exe -m src.notebook
.\.venv\Scripts\python.exe -m src.notebook --name 02_catalogue_evidence --execute
.\.venv\Scripts\python.exe -m src.notebook --name 02_catalogue_evidence
.\.venv\Scripts\python.exe -m src.predict --scenario config\demo_holdout_scenario.json
.\.venv\Scripts\python.exe -m src.notebook --name 03_model_evaluation --execute
.\.venv\Scripts\python.exe -m src.notebook --name 03_model_evaluation
.\.venv\Scripts\python.exe -m src.build_demo
.\.venv\Scripts\python.exe -m src.recommend --scenario demo_ml
.\.venv\Scripts\python.exe -m src.recommend --scenario demo_dark
.\.venv\Scripts\python.exe -m src.recommend --scenario demo_lead
.\.venv\Scripts\python.exe -m src.recommend --scenario demo_unknown
.\.venv\Scripts\python.exe -m src.notebook --name 04_hybrid_demo --execute
.\.venv\Scripts\python.exe -m src.notebook --name 04_hybrid_demo
```

Acquisition needs internet only for uncached files. The audit and notebook use cached files. Upstream code is retained for inspection, not executed. `requirements-lock.txt` records the installed environment. The notebook launcher keeps temporary and configuration files in the ignored `.runtime` directory.

Verified on 25 October 2026: dependency check passed, 51 pytest checks passed and all four notebooks executed through Jupyter kernels. The main demo was also re-executed with external socket access blocked. Executed copies have `_executed.ipynb` suffixes. Use the saved model during a demo; retraining is only needed to reproduce the development stage or after intentional training changes.

If rebuilding the environment:

```powershell
& 'C:\Users\Rohan\AppData\Local\Programs\Python\Python310\python.exe' -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

## Data decision

- Original spreadsheet: 443 rows, 75 pollutant names after whitespace normalisation.
- Deterministically retained: 440 rows; remove one exact duplicate and two zero dose rows.
- Outcome: reported `mlogk`, defined as negative log of the rate constant. Logarithm base remains unverified; do not convert into physical rates or removal percentages yet.
- Inputs: UV intensity, temperature, dose, initial concentration, pH and pollutant identity.
- No surface area, particle size, catalyst grade or study IDs are supplied.
- Methylene blue is absent. Sulfamethoxazole is used for the live numerical demonstration; amaranth is also represented in the data and evidence catalogue.
- Default to the original workbook because the curated workbook removed points using model residuals.

Read `outputs/data_audit.md` before training. Exact input grouping is available to avoid splitting identical conditions, but does not constitute independent study validation. No repository licence was located; verify reuse terms before redistribution or publication.

## Evidence catalogue

The catalogue contains all 15 families. The initial evidence database contains 16 observations from 11 papers, covering 10 of 45 family and pollutant pairs across sulfamethoxazole, amaranth and dissolved lead II. Eight families have relevant profile evidence; the remaining seven are visible as evidence gaps. A zero in coverage means no verified record in this bounded database, not that treatment fails.

- `data/materials.csv`: supplied material descriptions, with seed ranges explicitly unverified.
- `data/material_profiles.csv`: the actual study formulations, dimensions and light requirements.
- `data/evidence.csv`: observations with endpoints, units, conditions, source links and limitations.
- `data/sources.csv`: literature registry and review scope; raw data acquisition metadata remains in `source_manifest.json`.
- `data/pollutants.csv`: three supported evidence pollutants and explicit species.
- `data/excluded_transfers.csv`: composite and measurement claims that must not be assigned to another material or outcome.
- `outputs/evidence_coverage.csv`: the complete 15 by 3 evidence matrix.
- `outputs/evidence_audit.md`: interpretation and ranking boundaries.

To restore the two Stage B open access papers if missing, run `.\.venv\Scripts\python.exe -m src.acquire_evidence` before rebuilding the catalogue. Other source notes are curated observations scoped to the inspected abstract or full text sections; full texts are not silently assumed. The literature rows are not pooled ML training data.

## Completion and future work

The requested local prototype and demonstration package are complete. Rehearse using PRESENTATION.md. Future extensions would require better comparable data and study provenance rather than additional interface features. No new data acquisition or model training is needed to present the existing work.

## Integrated recommendation

The main user interface is now the local webpage in `web/`, served by `src.webapp` using Python's standard library. Its JSON API calls the same tested RecommendationEngine; no model or scoring rule was replaced. It binds to 127.0.0.1 only, uses local assets and rejects unrelated browser origins. The default launcher opens the HTTP URL directly, avoiding the HTML file association prompt from Jupyter.

The webpage calls `recommend(scenario)` from `src.recommend`, which returns all 15 material IDs. The summary and profile assessments include source matching and policy boundaries. `notebooks/04_hybrid_demo.ipynb` remains a supporting development view. `outputs/hybrid_integration.md` documents exact inputs and policy boundaries. The full suite now has 58 passing tests, including the local HTTP API.

The UV SMX example produces an uncertain shortlist of M02, M03 and M08. Only M02 receives an eligible numerical mlogk estimate. The dark version excludes the documented photocatalytic routes and retains CNTs as a conditional research candidate. The source matched lead example selects profile P09 of M13 under its stated laboratory assumptions. Unknown pollutants yield no invented preference rank.

Scores use the declared 60/25/15 suitability, setup and recovery policy. They are not pollutant removal percentages. Unknown criteria retain score intervals; overlapping candidates remain uncertain. A preference tier is an interval dominance frontier, not a forced complete ordering. Source observations and ML predictions retain their units separately. This ranks scored profiles within current evidence coverage, not all possible material formulations in the world.

Custom scenario JSON can be passed with `-m src.recommend --input config\my_scenario.json`. Use the generated `config/demo_ml.json` or `config/demo_lead.json` as examples. Specific study profiles and conditional candidates require explicit scenario flags; these are reproducible research assumptions, not hidden defaults. Named source profiles never inherit the unspecified TiO2 training profile's model.

## Trained model and limits

Random Forest was selected by training cross validation over Ridge and a median baseline. The 440 records were split into 350 training and 90 test rows, keeping identical input groups together. Test MAE is 0.1459, RMSE 0.2128 and R squared 0.8731. Baseline MAE is 0.4401. Errors are in the reported `mlogk` target, not percentage removal or percentage accuracy.

The saved model uses training rows only. Study identifiers are absent, so this is preliminary input group evaluation, not independent study validation. The runtime supports only 25 sufficiently represented training pollutant categories and checks operating ranges and nearby conditions. Of the 90 test rows, 38 pass those heuristic domain checks. It also requires M02, the explicit `dataset_unspecified_tio2` profile, UV illumination, the laboratory solution assumption and endpoint `mlogk`. It refuses other profiles, unseen pollutants, missing or nonfinite inputs and unsupported conditions.

`models/model_card.json` records exact metrics, versions, hashes and the predeclared usefulness checks. `models/domain.json` stores training input coverage. `outputs/model_comparison_cv.csv` compares all three model types; `outputs/test_predictions.csv` records the final evaluation. The training condition demo is labelled as such; `config/demo_holdout_scenario.json` instead uses the first eligible SMX holdout observation selected by inputs, not smallest error.

No physical rate conversion, removal percentage, confidence interval, or numerical comparison across material families is claimed. Read `outputs/model_evaluation.md` before presenting the results.
