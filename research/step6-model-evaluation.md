# Step 6: Model evaluation and feasibility

Reviewed 27 October 2026. This check replayed the **existing** 90-row input-group holdout with the existing fitted TiO₂ model; it is a reproducibility check, not a new independent test. The fitted model, training data, split and catalogue were not changed. The reproducible results and integrity flags are in [step6-model-audit.json](step6-model-audit.json), and the audit can be rerun with `research/step6_evaluate_model.py` using the project Python.

## TiO₂ holdout reproduction

| Measure | 90 held-out rows | 38 rows accepted by the existing domain rules |
| --- | ---: | ---: |
| Mean absolute error (MAE), mlogk | 0.14586 | 0.10236 |
| Root mean squared error (RMSE), mlogk | 0.21276 | 0.15394 |
| R² | 0.87308 | 0.90286 |

The stored median-baseline predictions have MAE 0.44015 on all 90 rows. The Random Forest's 90 predictions, eligibility decisions and reported model-card metrics were reproduced. Exact operating-input groups do not cross the saved training/test split. The accepted subgroup is selected by a heuristic domain rule, not an independent validation set; its metrics should not be generalized beyond the described subset.

On the same saved holdout, SMX has 10 rows (9 pass the domain policy) and all-row MAE 0.11120 mlogk; amaranth has six rows (3 pass) and all-row MAE 0.30851 mlogk. These are very small subgroups from a single existing split and are not a reliable comparison of pollutant performance. They are included to make uneven evaluation coverage visible, not as new tests or model-selection results.

The Random Forest was selected using grouped cross-validation before its saved holdout evaluation; its recorded CV MAE was 0.15941 versus 0.19148 for Ridge and 0.41674 for the median baseline. R² is not percentage accuracy. The model predicts the reported `mlogk` target; the logarithm base remains unverified, so no rate or percentage-removal conversion is justified.

## Integrity and the CSV hash difference

The saved model and training configuration match their recorded SHA-256 hashes. The processed CSV's raw bytes do **not** match the model card: its current file uses LF line endings. Converting those bytes to CRLF without changing the content yields the exact recorded training-data SHA-256. This verifies consistency up to that line-ending transformation; the original raw workbooks remain absent and were not independently checked during this step.

All 440 processed source-row IDs match the saved split; there are 350 training and 90 test rows and no overlapping exact input groups. The model's 25 sufficiently represented pollutant categories are part of its own domain policy. The webpage's evidence catalogue currently recognizes only SMX, amaranth and dissolved lead, and the ML branch still applies only to eligible TiO₂ inputs.

## Limits that remain

- Study IDs are missing from the 440-row dataset. Grouping identical inputs does not establish study-independent validation or rule out related experimental data across splits.
- The model has no observed catalyst grade, particle size, surface area, reactor geometry or per-row water-matrix identity. The laboratory-solution setting is an assumption, not a property verified for each training row.
- Fifty-two of the 90 saved holdout rows fail at least one existing domain criterion. The domain criteria are heuristic screening rules rather than calibrated uncertainty or proof of applicability.
- Source workbooks and cached original papers are absent in this checkout. Their restoration and hash verification remain outstanding; model reproducibility from source acquisition and retraining was not checked.

## Feasibility of models for the other materials

No additional material-specific model is justified by the current data. The 19 catalogue evidence rows are literature claims, all deliberately marked ineligible for ML training; most represent different endpoints, formulations, pollutants and incomplete conditions. Several other families have no reviewed study profile. The 18 staged review rows from 11 studies include multiple observations from the same study, held composites, unconfirmed conditions and incompatible endpoints. They are not 18 independent comparable training experiments.

To assess a future model, first collect substantially more comparable row-level experiments for a defined material/formulation and target, with measured conditions, units and source-study identifiers. Preserve missing values and separate composites, pollutant species, adsorption capacity, percent removal and kinetic targets. Establish sufficient diversity and enough independent studies for study-grouped evaluation, compare with a simple baseline, and reserve an independent test before claiming prediction performance. There is no defensible fixed minimum number demonstrated by the present data.

## Verification

`tests/test_model.py`: 17 passed. The audit script checked model and configuration hashes, the processed-data line-ending explanation, source-row coverage, split group separation, saved predictions, domain eligibility and recorded metrics. It did not retrain or perform study-independent validation.
