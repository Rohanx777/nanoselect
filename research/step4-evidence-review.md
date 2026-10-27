# Step 4: Curated evidence review

Review date: 27 October 2026. The [review table](step4-reviewed-evidence.csv) is a staging artifact, not the application's evidence database and not model training data. It contains 18 source-scoped observations from 11 studies: six on sulfamethoxazole, six on amaranth, two on dissolved lead, three on chromium(VI), and one on arsenic(III).

The table records the exact formulation, pollutant species, source and review scope, known experimental fields, outcome and unit, conversions, limitations, and a review decision. A blank cell means **not established in the reviewed source scope**; it is not zero. The `material_candidates` field identifies related families for human review and is not permission to transfer a composite result to all of its constituents.

## Decisions

| Decision | Rows | Meaning |
| --- | ---: | --- |
| `conditionally_curated` | 2 | Primary source scope provides a relevant observation, but some conditions are missing. Eligible for a cautious profile-specific evidence review, not a fully matched operating point. |
| `hold_*` | 16 | Source identifies a relevant observation, but the recorded reason requires an implementation or review decision before import. |

The 16 held rows include four records for new chromium/arsenic species or associated setup conditions, eight composite/sonication records, one unverified nanoclay dimension, two records needing condition or source-consistency checks, and one composite record with conflicting dose reports. These categories describe the reason for holding a record, not its scientific quality.

Three magnetite–chitosan SMX rows are experimental replicates from a **single study**, not three independent studies. Four amaranth CuS–rGO rows describe different loadings within another single study. Their outcomes must not be assigned to either component on its own. The current app does not explicitly model sonication or a nitrogen atmosphere; a future import must first handle these requirements conservatively.

## Examples checked

- [Graphene oxide and SMX](https://www.sciencedirect.com/science/article/abs/pii/S0045653515002842): the publisher abstract reports up to 12% SMX removal within six hours. The full set of conditions for that upper-bound result has not been established, so this is not an exact operating point.
- [nZVI and SMX](https://pubmed.ncbi.nlm.nih.gov/33189375/): the indexed abstract reports an 83–91% range in acidic conditions at a 10:1 nZVI-to-SMX mass ratio. The endpoints are not attributed to specific individual pH values and times in the reviewed abstract.
- [Magnetite–chitosan composite and SMX](https://pmc.ncbi.nlm.nih.gov/articles/PMC10475053/): the indexed Table 5 reports three experimental values at pH 6, concentration 22 mg/L, 0.13 g per 100 mL, and 15 minutes of sonication. The separate predicted value is not imported as experimental evidence.
- [Iron nanoparticles and chromium(VI)](https://pmc.ncbi.nlm.nih.gov/articles/PMC1390446/): the full-text comparison distinguishes bare from starch-stabilized particles under a stirred nitrogen atmosphere. Reduction of Cr(VI) must not be presented as total chromium removal.
- [CeO₂ and lead](https://www.mdpi.com/2297-8739/13/2/61): the indexed abstract reports 80% removal at pH 6, while a comparison table lists 90%. The removal row is held until the conditions and discrepancy are resolved. The reported experimental adsorption capacity is separate from the fitted Langmuir capacity.

The source access is mixed: some records are based on accessible full text or indexed full-text sections, while others are based on publisher or PubMed abstracts because direct access returned a CAPTCHA, denial, or rate limit. Review status is limited to that scope; it is not an independent experimental validation or a redistribution licence.

## Checks and next-step boundaries

- Checked for unique review IDs, valid percentage ranges, a unit for numerical outcomes, and HTTPS source references. Verified that the review table can be parsed as CSV.
- Normalized only explicit conversions: g per known solution volume to g/L, seconds or hours to minutes, and mg/dm³ to mg/L. Original quantities are noted in the conversion field.
- No entries were added to `data/evidence.csv`, no model was retrained, and application rankings were not changed. In particular, arsenic and chromium are **not yet selectable as supported evidence pollutants**.
- Before Step 5 can use these records, decide how to represent composites and required equipment, resolve the held inconsistencies, verify which formulations satisfy the 15-candidate scope, and add tests. Missing data remains missing; no complete ordering is inferred from the 18 rows.

Regenerate the CSV from the documented records with the project Python:

```powershell
nanomaterial_hybrid/.venv/Scripts/python.exe research/step4_build_review.py
```
