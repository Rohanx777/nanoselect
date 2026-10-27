# Stage C model evaluation

## Result

Selected **Random Forest** by the lowest training cross validation MAE. Prototype numerical prediction enabled: **True**. No model ranking used final test outcomes. The predeclared usefulness checks are recorded in the model card; these are pragmatic prototype criteria, not a chemical standard.

## Data and evaluation

440 original audited records were split into 350 training and 90 test rows, with zero identical input groups shared. Five fold grouped cross validation used training rows only. Identical conditions with different measured outcomes stayed in the same split. Study identifiers are unavailable, so results are preliminary and may benefit from shared studies or apparatus across splits. No independent lab validation was performed.

Only I, T, D, C0, pH and exact SMILES category enter the pipeline. Numeric imputation and scaling and categorical encoding are fitted inside each CV training fold. Size, surface area, source row and target derived fields are excluded. Literature observations from Stage B are not pooled into this dataset.

## Final test metrics

All errors are in the reported mlogk target, not percentage removal.

| Model | MAE | RMSE | R squared |
|---|---:|---:|---:|
| Selected Random Forest | 0.1459 | 0.2128 | 0.8731 |
| Median baseline | 0.4401 | 0.5974 | -0.0006 |

Relative test MAE improvement over baseline: 66.9 percent. This is an error reduction, not prediction accuracy or pollutant removal efficiency. The complete CV comparison is `model_comparison_cv.csv`, including Ridge and Random Forest; all nine configurations appear in `cv_candidates.csv`.

## Domain coverage

25 pollutant categories have at least the required five distinct training conditions. 38 of 90 held out rows pass the provisional range and nearest condition policy. All row predictions above are evaluator diagnostics, including rows a deployed predictor would refuse; eligible subset metrics are separate in the model card. Do not report the overall metrics as a guarantee for every pollutant or operating range. Per pollutant test subsets are small.

The saved artifact is fitted only on training rows. The runtime requires the unspecified dataset TiO2 profile, UV light, a laboratory solution assumption and requested endpoint mlogk. It refuses missing or nonfinite values, unseen or sparsely represented pollutants, different materials, named catalyst profiles and conditions outside the declared support. It does not output an uncertainty interval.

## Demonstration

Run `.\.venv\Scripts\python.exe -m src.predict`. The saved example uses an actual sulfamethoxazole training condition when available. Its demonstration prediction is not part of held out validation. `exact_training_conditions` makes that distinction explicit.

No logarithm base was invented. The output is the original reported negative log rate target. Do not convert it into k or removal percentage. The model cannot rank TiO2 against 14 other families by numerical efficiency; the next stage combines this limited module with source backed evidence and deterministic decision rules.

Method references: https://scikit-learn.org/stable/modules/cross_validation.html and https://scikit-learn.org/stable/common_pitfalls.html
