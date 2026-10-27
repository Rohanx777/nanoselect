# Stage A data audit

## Decision

Proceed with a preliminary TiO2 operating condition regression task predicting the reported `mlogk` target. Use the original workbook, not the outcome curated workbook, as the source for our own evaluation. No model has been trained yet. This dataset cannot train a 15 material comparison.

## Actual downloaded files

Repository commit: `c59e1a748b36b87eb051d9ce0acf6962bab1d118`.
Original: 443 rows. Curated: 439 rows. Both have one sheet and eight columns. The paper describes an earlier 446 record collection; use the actual downloaded counts in our report.

The original workbook has 1 exact duplicate and 75 pollutant names after whitespace normalisation, matching 75 distinct SMILES strings. All eight raw columns are populated. Exact SMILES strings are not chemically canonicalised or independently validated in this audit.

After deterministic exclusions: **440 rows**. Excluded 3 rows; see `excluded_rows.csv`. This removes exact duplicates and nonpositive catalyst doses, which cannot support a TiO2 treatment prediction. Other identical inputs with different measured targets remain; they may reflect repeats or missing context. Keep those inputs together in later splits.

## Features and outcome

Five operating inputs: I (UV intensity in mW/cm^2), T (degrees C), D (TiO2 dose in g/L), C0 (mg/L), and pH. Pollutant identity is supplied by SMILES or its verified name mapping. The human readable name is not an additional independent chemical descriptor.

The paper defines the target as -log(k), with k in min^-1. The inspected text and upstream code do not explicitly establish the logarithm base. **Train and label only `mlogk` for now; do not convert to k or removal percentage until the base is verified.** The supplied data does not include particle size, BET surface area, time, catalyst grade, batch, reactor geometry, wavelength or source study identifiers.

## Pollutant coverage

Methylene blue is absent. Switch the proposed ML demonstration to sulfamethoxazole or amaranth, subject to later validation and evidence matching. Do not claim predictions for methylene blue from this dataset.

| Pollutant | Cleaned records | Distinct input groups |
|---|---:|---:|
| Sulfamethoxazole | 25 | 22 |
| Amaranth | 24 | 24 |
| Benzylparaben | 14 | 14 |
| Bisphenol A | 13 | 13 |
| Atenolol | 13 | 13 |
| Tebuthiuron | 13 | 13 |
| Propachlor | 13 | 13 |
| Dinoseb | 12 | 12 |
| Propham | 12 | 12 |
| Ofloxacin | 11 | 11 |

The complete table is `pollutant_coverage.csv`. All numeric ranges and missing values are in `data_audit.json`; units are in `data_dictionary.csv`.

## Provenance and evaluation limitations

No row level study identifiers exist in either workbook. Identical input grouping can prevent direct duplicate leakage but cannot establish independent study performance. Prefer recovering original study provenance if possible within the time budget; otherwise label evaluation preliminary and explicitly state that study overlap may inflate results. A pollutant holdout can be an additional diagnostic for unseen molecules, not a substitute for study provenance.

The associated paper reports removing four points based on model residuals to create the curated dataset. To avoid inheriting this outcome informed filtering, our default is the original workbook with only documented input validity and duplicate exclusions. Do not remove rows merely because a model predicts them poorly.

There are 6 original identical input groups with different targets. Missing experimental context limits identifiability. No material grade should be invented, and no claim of validation for a commercial grade is justified by these files alone.

## Sources and reuse

Data and upstream code: https://github.com/mahyavs/GNN_photodegradation

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC12126497/

Cached full text XML: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12126497/fullTextXML

Original dataset paper DOI given by the associated paper: https://doi.org/10.1016/j.envres.2020.109697

Raw files are cached unchanged. `data/source_manifest.json` records URLs, commit and SHA256 values. No repository licence was located in the audited tree. Do not assume permission to redistribute the raw dataset; retain attribution and review reuse terms before publishing.

## Next stage

Build the 15 family catalogue and verified evidence records for a small pollutant set. Prefer one actual dataset pollutant for the first numerical demo. Then compare a baseline, Ridge and Random Forest using leakage aware evaluation. Training, evidence ranking and the full demo are not part of this completed setup stage.
