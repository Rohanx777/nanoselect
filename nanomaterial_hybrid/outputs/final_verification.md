# Final demonstration verification

Status: passed on 25 October 2026.

Each scenario ran in a new Python process. A process local audit hook blocked non-loopback connections and external name lookups. Every scenario confirmed the guard by attempting a blocked external connection, then ran successfully from cached files. Loopback communication was allowed for the notebook kernel. This is a verification control, not a system wide firewall or proof of scientific validity.

| Check | Result | Seconds |
|---|---|---:|
| readiness | Passed | 1.78 |
| demo_ml | Passed | 1.91 |
| demo_dark | Passed | 1.76 |
| demo_unknown | Passed | 1.76 |
| demo_lead | Passed | 1.79 |
| edited_input | Passed | 1.77 |
| custom_cli | Passed | 1.77 |
| tests | Passed | 3.34 |
| notebook | Passed | 9.55 |

All five scenario runs returned exactly 15 unique material IDs. The four named examples matched their saved outputs. The edited input example changed the lead concentration and correctly lost its exact source matched winner. The test suite ran under the same guard, and the main notebook executed all seven code cells without errors. No model file changed, and no retraining occurred.

An offline static preview is available at outputs/hybrid_demo.html. Automatically loaded asset tags contain no remote URLs; research citations still require internet when clicked. This preview shows saved results and cannot recompute inputs. Use START_DEMO.cmd or the terminal command to run live predictions and rankings.

Exact process results and model hashes are in final_verification.json. Logs and per scenario outputs are in outputs/final_verification. The existing model remains preliminary, the score remains a decision policy rather than removal percentage, and unsupported evidence pairs remain unknown.
