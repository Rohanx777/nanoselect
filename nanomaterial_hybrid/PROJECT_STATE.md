# Project state

Updated 25 October 2026.

## Current stage

All five original stages complete. The user then requested a proper webpage interface instead of Jupyter. NanoSelect is implemented locally in web/ with a stdlib HTTP server, and the default run.bat launcher now opens that interface directly.

## Completed

- Read the user supplied build plan as project context. No AGENTS.md found in the checked project and ancestor locations.
- Created isolated nanomaterial_hybrid directory; existing document files left untouched.
- Downloaded two real TiO2 workbooks and relevant upstream code at commit c59e1a748b36b87eb051d9ce0acf6962bab1d118.
- Cached full article XML via Europe PMC and recorded source hashes.
- Wrote repeatable acquisition and audit modules, audit reports, coverage and exclusion tables, and initial notebook.
- Selected original 443 row workbook; retained 440 rows after one exact duplicate and two zero dose exclusions.
- Installed the project .venv using Python 3.10.11 and saved requirements-lock.txt. pip check passed.
- Re-ran the audit in the project environment; three pytest checks passed.
- Executed notebooks/01_data_audit.ipynb through a real Jupyter kernel, producing 01_data_audit_executed.ipynb.
- Added src.notebook launcher so config and temporary files stay inside the project, avoiding restricted user profile paths.
- Created all 15 material families, 11 specific study profiles and 16 literature observations from 11 papers.
- Registered three evidence pollutants: sulfamethoxazole, amaranth dye and dissolved lead II.
- Created the complete 45 pair coverage table: 10 pairs have profile evidence and 35 remain insufficient evidence. Eight material families are covered; M04, M05, M07, M09, M11, M12 and M14 have no verified records for these three pollutants in the bounded database.
- Preserved source scope, URLs, notes, unknown conditions, reported units and four rejected evidence transfers. User property ranges remain unverified display fields.
- Cached two Stage B OA full text XML files. Other papers are abstract scoped or reviewed PDF sections; sources.csv makes access limits explicit.
- Added a reproducible offline catalogue builder, optional OA cache restoration and the Stage B notebook. Both notebooks execute successfully; the test suite now has 9 passing tests.
- Trained Dummy median, Ridge and Random Forest using five fold grouped CV on training rows only. Nine total configurations were compared. Random Forest selected without test based model selection.
- Split 440 rows into 350 training and 90 held out rows, with no identical input groups shared. Study provenance remains unknown. Split rows and CV fold IDs are saved.
- Selected Random Forest test MAE 0.1458586, RMSE 0.2127625 and R squared 0.8730815. Median baseline MAE 0.4401478. All five predeclared prototype usefulness checks passed.
- Saved the training only fitted pipeline, model card and input domain. 25 training pollutant categories meet the minimum coverage rule; 38 of 90 test records pass the heuristic domain policy.
- Implemented src.predict with explicit material/profile/light/matrix/endpoint checks, unknown pollutant and missing input rejection, per pollutant ranges and joint nearest condition checks. No physical rate or removal percentage conversion is made.
- Added distinct training condition and held out condition demo files. The latter selects the first eligible SMX test row by inputs, not prediction error.
- Added model evaluation plot, report and third notebook. The notebook executes; 26 tests pass, including split integrity, domain checks and repeatable predictions. Selected metrics reproduced with the unchanged seed and configuration.
- Implemented src.recommend: every request returns 15 rows with explicit status, selected profile, score interval, preference tier, rank position bounds, sources, units and explanations.
- Added the documented 60/25/15 policy, unknown criterion intervals, strict interval dominance and alternative weights. Conditional study profiles are ranked only under explicit scenario assumptions. ML quantities never enter decision scores or transfer to named literature profiles.
- Implemented four reproducible scenarios and output exports. UV SMX returns a tied M02/M03/M08 shortlist; dark SMX retains M08 conditionally; source matched lead selects M13/P09; unknown pollutant yields no justified rank.
- Added integrated notebook 04_hybrid_demo and a build_demo packager that uses cached inputs and the saved model, with no training or internet calls.
- Full suite now has 51 passing tests, covering all IDs, unknowns, light changes, profile boundaries, score intervals, source match sensitivity, unchanged rankings under table reordering and weight sensitivity. Integrated notebook executes successfully.
- Final verification caught a last bit floating point difference from parallel forest prediction. Saved model inference now uses one thread; the fitted artifact, training results and model file hashes are unchanged.
- Added START_DEMO.cmd and src.launch with readiness checks, notebook launch and terminal fallback. The CMD readiness path was tested from the parent directory, including spaces in the project path.
- Added START_HERE.md, an editable my_scenario.json and PRESENTATION.md with a five minute walkthrough and likely examiner questions.
- Added fresh process offline verification for the four examples, a fixed changed concentration fixture, the actual custom input CLI, test suite and notebook. All passed under a process local external connection guard. Loopback kernel traffic was permitted; this is not a system wide firewall claim.
- Added outputs/final_verification.json and .md, detailed logs and per scenario outputs. Source and saved model files were reused without retraining. Model artifact hashes before and after final verification are identical.
- Exported outputs/hybrid_demo.html from the executed notebook with embedded/local resources and no remote asset tags. Citation hyperlinks still require internet when clicked; the preview cannot recompute inputs.

## Findings that change the proposed plan

- No methylene blue records. Prefer sulfamethoxazole (25 original records) or amaranth (24) for the initial demo, after validation.
- No study IDs, catalyst grade, size or BET surface area. Do not create those values.
- Target is mlogk; base not independently confirmed. Preserve target units and avoid physical inverse conversion for now.
- Curated spreadsheet was filtered using model errors; do not inherit that filtering in the primary evaluation.
- Identical operating inputs sometimes have conflicting targets; preserve them and group them during splitting.
- No upstream repository licence found. Retain attribution and verify reuse terms before publishing data.

## Completion

Latest interface work: web/index.html, style.css and app.js provide editable inputs, four example scenarios, setup options, a working Run button, a recommendation summary, all 15 rows, source explanations, filters, a method dialog and browser CSV export. src.webapp serves static assets and /api/meta plus /api/recommend, delegating to the existing engine. src.launch now starts src.webapp, not the notebook. No publishing or hosted service is used. START_HERE.md has the current instructions. UI checks confirmed the UV case, dark case, lead case and changed concentration recomputation.

Web handoff verified: 58 tests pass, JavaScript syntax check passes, the browser shows the real model estimate and rankings, filters and source explanations work, and unsupported pollutants remain unknown. Windows sockets use exclusive binding so repeated run.bat launches reuse one server. Verified the default launcher opens the webpage; it is currently served at http://127.0.0.1:8765/. Screenshot: outputs/web_interface.png.

No implementation stage remains. The user can start the live demonstration through START_DEMO.cmd, view the saved preview or run the CLI. Preserve disclosed limitations and conditional assumptions. Any later changes should respond to user feedback or a concrete issue; do not repeat dataset searches, train new models, force a unique winner or add a website without a new request.

## Resume commands

Use START_HERE.md for the exact user steps. Main launcher: run.bat in the parent IDP 2026 folder, which opens the local webpage through START_DEMO.cmd. Default URL: http://127.0.0.1:8765/. Earlier notebooks and static previews are supporting artifacts. Final backend verification can be reproduced with .\.venv\Scripts\python.exe -m src.verify_demo; it does not retrain the model. User edits to config/my_scenario.json are separate from the fixed verification fixture, so final checks do not overwrite those edits.
