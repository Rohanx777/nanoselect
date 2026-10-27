# Five minute presentation walkthrough

Before presenting, double-click run.bat in IDP 2026 to open the NanoSelect webpage. Keep the terminal open. Use the example buttons and Rank materials to run each case; View opens a material's explanation, and View method and model results explains the evaluation. The earlier notebook and saved HTML remain optional supporting artifacts. Do not retrain during the presentation.

## First minute explain the problem and approach

“Different pollutants need different treatment mechanisms. Our project assesses a fixed catalogue of 15 nanomaterial families and recommends the best supported candidates for specified water conditions. We use a hybrid method: a trained TiO2 model where the data supports prediction, and published experimental evidence plus deterministic rules elsewhere.”

Show the 15 material rows. Explain that adsorption captures a contaminant on a surface, while photocatalysis uses light to help transform it. The system therefore needs the pollutant identity and treatment conditions rather than surface area alone.

## Second minute show the machine learning evidence

“We downloaded existing experimental data and retained 440 records after documented exclusions. We compared a median baseline, Ridge regression and Random Forest. Selection used training cross validation, followed by a separate 90 record test set. Identical input groups were kept together.”

Show the model evaluation notebook or outputs/model_evaluation.md if asked. Random Forest test MAE is approximately 0.146 in the reported mlogk target, compared with 0.440 for the baseline. R squared is about 0.873; it is not 87.3 percent accuracy. Missing study IDs make this preliminary evaluation, since related studies may occur across splits.

“We did not invent missing size or surface area measurements. Those properties are absent from the ML dataset. The model's output is the original reported negative log rate target, and the logarithm base remains unverified, so we do not convert it to physical rates or removal percentages.”

## Third minute run the hybrid example

Show the UV sulfamethoxazole case. Introduce sulfamethoxazole as SMX, an antibiotic.

“The model produces an eligible TiO2 estimate under its dataset profile. The evidence engine also considers ZnO, CNT, nZVI and graphene oxide study profiles. It returns an uncertain shortlist because the evidence and unknown setup and recovery criteria do not justify a unique material winner.”

Point to the material profile and prediction target columns. The numeric ML value does not boost the decision score or transfer to a named literature grade. The preference score uses declared 60/25/15 weights for suitability, setup and recovery. Unknown criteria retain a range rather than an invented midpoint.

## Fourth minute change the conditions

Run the dark case.

“Removing light makes the documented photocatalytic routes incompatible with the declared setup. CNT, graphene oxide and nZVI remain conditional research candidates; the nZVI and graphene oxide abstracts do not establish illumination requirements. This is not a guaranteed removal percentage.”

Show the lead case.

“This example deliberately matches the published hydroxyapatite batch experiment. It ranks first under our policy because an observed removal result and the available separation setup match the requested case. The 100 point score means complete checked policy support, not 100 percent removal.”

If time permits, run config/my_scenario.json. The changed lead concentration loses the exact source matched support. This demonstrates that the recommendation is conditional on the inputs.

## Fifth minute show boundaries and conclude

Run the unknown pollutant case.

“The system returns all 15 candidates but refuses to fabricate a ranking for unsupported pollutants. We currently have 19 literature observations from 14 papers covering 13 of 45 material and pollutant pairs. The other pairs are explicit evidence gaps.”

“Our contribution is a reproducible local decision support prototype with explanations, source links, domain checks and a working hybrid pipeline. We used existing published data and performed computational checks. We have not performed independent laboratory validation or established drinking water safety.”

## Likely questions

**Why use a hybrid method?** Comparable numerical data does not cover all 15 materials. The hybrid design preserves the fixed candidate catalogue while making different evidence levels visible.

**Are all 15 predictions made by ML?** No. The evaluated numerical module is for TiO2. Other materials are assessed using verified, profile specific literature evidence; missing pairs remain unknown.

**Why Random Forest?** It had the lowest training cross validation error among the compared model families and then passed the predeclared prototype usefulness checks on the held out set.

**Is the ranking learned?** No. It is a transparent deterministic decision policy. The weights are project choices, not experimentally discovered constants. Two alternative weight sets are checked with selected profiles held fixed.

**How is it reproducible?** Data and source hashes, the split, configuration, package versions and model card are saved. Training uses seed 42. Saved model inference uses one thread to keep reduction order stable on this PC.

**Why are candidates tied?** Their score intervals overlap. A unique winner would imply evidence the database does not contain. Display order within a tier does not claim superiority.

**Why is surface area not an ML input?** The actual dataset does not contain it. Some literature profiles record measured surface area, but catalogue ranges are not substitutes for experimental measurements.

**What does the ML output mean?** It is the dataset's reported mlogk, a negative log rate target. The prototype keeps that target instead of assuming the log base or converting to percentage removal.

**Does it work offline?** The cached demonstration, model and source tables work without external connections. Internet is needed to acquire new research or open external citation links.

**What would improve it?** More comparable experiments across materials, recovered study provenance, better material descriptors, validated uncertainty estimates and later laboratory checks.
