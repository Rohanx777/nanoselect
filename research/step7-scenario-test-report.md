# Step 7: Scenario and edge-case checks

Checked 27 October 2026 against the current local project. These are software and decision-policy checks, not laboratory experiments or independent validation of treatment performance.

## Automated results

The following command completed with **87 passed, 1 deselected**:

```powershell
cd nanomaterial_hybrid
.\.venv\Scripts\python.exe -m pytest tests/test_scenario_matrix.py tests/test_model.py tests/test_recommend.py tests/test_webapp.py tests/test_catalogue.py -q -k 'not cached_full_text'
```

The excluded check needs cached original paper files that are missing from this checkout. This command does not cover every test in the repository: the source-acquisition/data-audit suite was not run because its raw inputs are absent. The tests use the local HTTP server on loopback and the saved model; they do not retrain it.

| Case | Observed software behavior |
| --- | --- |
| SMX, UV preset | Five conditional candidates occupy the leading interval tier: TiO₂, ZnO, nZVI, graphene oxide, and CNT. Only TiO₂ has an eligible numerical ML estimate. |
| SMX, dark preset | TiO₂ and ZnO documented photocatalytic routes are setup mismatches. nZVI, graphene oxide, and CNT remain conditional; the reviewed nZVI and graphene oxide sources do not establish a light requirement. |
| Lead preset | Nano-hydroxyapatite profile P09 is source matched and uniquely leads under the preset's specified assumptions. This policy match is not independent validation. |
| Unknown pollutant | No material receives a rank or ML estimate. |
| Amaranth, saved eligible TiO₂ test-row inputs | An amaranth holdout row accepted by the existing domain policy receives a TiO₂ estimate; no other material receives an ML estimate. Reusing a saved holdout row is a software check, not a new test set. |
| Lead: change pH, dose, temperature, time, concentration, or water type | Each tested individual change removes the source-matched status from nano-hydroxyapatite. |
| Lead: remove centrifuge | The selected nano-hydroxyapatite profile becomes incompatible with the stated equipment. |
| Missing SMX light intensity | The TiO₂ ML estimate is withheld with a reason; other evidence-based candidates are still assessed. |
| 100% recovery priority | The lead shortlist changes, and a subsequent default-priority request returns the original shortlist; preferences do not leak between requests. |
| Arsenic, chromium, methylene blue, or blank pollutant | No rank or ML estimate is fabricated. |
| Invalid pH, zero or negative values where prohibited, nonfinite intensity, or removal target above 100% | The engine rejects the scenario with a validation error. |
| Upper-bound, maximum, range, or approximate observations | They cannot be used as exact evidence of reaching a specified removal target. |

## Browser checks

Using a separate test tab against the running local application:

- Changing the priority total from 100% to 80% showed an actionable error and marked the previous result as stale.
- Resetting the weights and choosing **Lead · Lab conditions** displayed the source-matched nano-hydroxyapatite result.
- Changing lead concentration from 200 to 1 mg/L displayed a stale-result notice; rerunning changed the result to an uncertain shortlist.
- Choosing **Unsupported pollutant** displayed “No supported recommendation”, zero ranked candidates, and 15 evidence gaps.
- Choosing **Amaranth dye** and running the analysis returned 15 assessments, with two ranked under the selected conditions and 13 evidence gaps. This was an interface check; the selected values are not recommended operating conditions.
- The browser console showed no error messages in these checks.

## Remaining limitations

The source-matched scenarios test implementation against the records currently in the catalogue; they do not independently verify the underlying studies. The data still covers only three evidence pollutants and 13 of 45 material–pollutant combinations. Arsenic and chromium remain unsupported in the live ranking, and the original source files needed for complete acquisition/hash checks are missing. HTML/PDF report content, presentation materials and final handoff are scheduled for the next steps.
