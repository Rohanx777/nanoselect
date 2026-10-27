# Stage B catalogue and evidence audit

## Completed scope

- All 15 material families are registered with stable IDs M01 to M15.
- 11 study specific material profiles and 16 reviewed observations from 11 independent papers.
- Three named pollutants: sulfamethoxazole, amaranth dye and dissolved lead II. The first two are present in the audited ML dataset; lead is evidence only.
- 10 of 45 material and pollutant pairs have profile specific evidence. 35 remain insufficient evidence.
- Four rejected evidence transfers are recorded to prevent composite, measurement and configuration mixups.

## Coverage by independent study count

| ID | Material | Sulfamethoxazole | Amaranth dye | Lead II |
|---|---|---:|---:|---:|
| M01 | Iron oxide magnetite | 0 | 0 | 1 |
| M02 | Titanium dioxide | 2 | 1 | 0 |
| M03 | Zinc oxide | 1 | 1 | 0 |
| M04 | Silver nanoparticles | 0 | 0 | 0 |
| M05 | Nanoscale zero valent iron | 0 | 0 | 0 |
| M06 | Graphene oxide | 0 | 0 | 1 |
| M07 | Reduced graphene oxide | 0 | 0 | 0 |
| M08 | Carbon nanotubes | 1 | 0 | 0 |
| M09 | Nano alumina | 0 | 0 | 0 |
| M10 | Magnesium oxide | 0 | 0 | 1 |
| M11 | Manganese dioxide | 0 | 0 | 0 |
| M12 | Cerium oxide | 0 | 0 | 0 |
| M13 | Nano hydroxyapatite | 0 | 0 | 1 |
| M14 | Nano clay montmorillonite | 0 | 0 | 0 |
| M15 | Chitosan nanoparticles | 0 | 0 | 1 |

Zero means no verified observation in this bounded database. It does not mean ineffective. Multiple concentrations or temperatures from one paper count as one independent study.

## How to interpret these tables

`materials.csv` preserves the user's supplied ranges in seed fields marked unverified. They are display information and cannot fill missing model descriptors. `material_profiles.csv` contains the formulations actually studied. Profile dimensions retain their meanings: ZnO rod length 755 nm is distinct from its 12 nm diameter; GO thickness is not a spherical particle diameter.

`evidence.csv` contains literature observations, not predictions. Numeric values retain their endpoint and units. The 265 mg/g hydroxyapatite batch maximum is measured, not its fitted Langmuir maximum of 263.2 mg/g. The 0.1105 mmol/g magnetite result is not a removal percentage. No values are copied into ML training data by this stage.

Only two papers have cached full XML here. The magnetite PDF was inspected in relevant sections through the web reader. Other observations are abstract scoped, with indexed publisher abstracts explicitly identified where direct access failed. Verified means the claim matches that inspected scope; it does not certify experimental quality or complete operating conditions. Sources and local hashes are in `sources.csv`; review notes are preserved in `data/curation/evidence_seed.json`.

## Boundaries needed for ranking later

1. Match a pollutant and material profile before using an observation. Default status is conditional literature support, not guaranteed effectiveness.
2. Match the water matrix, light requirements and operating conditions. Missing fields remain unknown. An optimum pH is not a validated pH range.
3. Require light for the documented photocatalytic routes. Missing wavelength or irradiance must remain explicit.
4. Do not compare capacity, rate constant and percent removal as interchangeable numerical endpoints.
5. Recovery remains unknown unless the inspected study reports it. Magnetite's magnetic character does not prove recovery was tested in that experiment.
6. A crosslinked chitosan formulation, wire supported ZnO rods and a specific TiO2 crystal phase are not interchangeable with arbitrary powders from the same family.
7. `excluded_transfers.csv` includes MgO bentonite composite results that cannot populate standalone MgO or nanoclay records. The nMgO control has its own limited record.
8. `verified_profile_evidence` in the coverage matrix is not a ranking or recommendation status. A future scenario evaluator must decide applicability.

## Reproduce

Run `.\.venv\Scripts\python.exe -m src.catalogue` from the project root. This rebuilds all tables without internet. It uses the reviewed seed and the two cached papers. Run pytest afterward. Regeneration must not modify the original TiO2 dataset or its audit.

## Next stage

Train and evaluate one TiO2 regression task on the original audited dataset. Keep study provenance and logarithm base limitations from Stage A. The 16 literature rows are not a new pooled training dataset. Numerical predictions remain disabled until that evaluation. Ranking rules will be implemented after training; no preference scores or winners have been assigned in Stage B.
