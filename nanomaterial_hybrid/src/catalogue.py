"""Build Stage B reference tables from reviewed literature observations.

This module does not train a model or assign recommendation scores.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
POLLUTANTS = [
    {"pollutant_id":"sulfamethoxazole", "display_name":"Sulfamethoxazole", "pollutant_class":"antibiotic", "species":"sulfamethoxazole", "aliases":"SMX;sulfamethoxazole", "ml_dataset_present":True},
    {"pollutant_id":"amaranth", "display_name":"Amaranth dye", "pollutant_class":"azo_dye", "species":"amaranth dye", "aliases":"amaranth;amaranth dye;Acid Red 27", "ml_dataset_present":True},
    {"pollutant_id":"lead_ii", "display_name":"Dissolved lead II", "pollutant_class":"metal_ion", "species":"Pb(II)", "aliases":"Pb(II);Pb2+;lead(II)", "ml_dataset_present":False},
]
MATERIALS = [
    ("M01","Iron oxide magnetite","Fe3O4",10,100,"particle_size",30,150,"adsorption;magnetic_recovery"),
    ("M02","Titanium dioxide","TiO2",10,50,"particle_size",30,200,"photocatalysis"),
    ("M03","Zinc oxide","ZnO",10,100,"particle_size",10,100,"photocatalysis;adsorption"),
    ("M04","Silver nanoparticles","Ag",10,100,"particle_size",5,50,"antimicrobial_action"),
    ("M05","Nanoscale zero valent iron","Fe0",10,100,"particle_size",20,40,"reduction;adsorption"),
    ("M06","Graphene oxide","GO",1,10,"sheet_thickness",100,700,"adsorption"),
    ("M07","Reduced graphene oxide","rGO",1,10,"sheet_thickness",100,600,"adsorption;filtration"),
    ("M08","Carbon nanotubes","CNT",1,100,"tube_diameter",100,500,"adsorption"),
    ("M09","Nano alumina","Al2O3",10,100,"particle_size",50,200,"adsorption"),
    ("M10","Magnesium oxide","MgO",10,100,"particle_size",50,200,"adsorption;precipitation"),
    ("M11","Manganese dioxide","MnO2",10,100,"particle_size",50,300,"adsorption;oxidation"),
    ("M12","Cerium oxide","CeO2",5,50,"particle_size",20,150,"adsorption;catalytic_oxidation"),
    ("M13","Nano hydroxyapatite","Ca10(PO4)6(OH)2",20,100,"particle_size",20,100,"adsorption;ion_exchange"),
    ("M14","Nano clay montmorillonite","montmorillonite",1,100,"layer_thickness",50,200,"adsorption;ion_exchange"),
    ("M15","Chitosan nanoparticles","chitosan",20,200,"particle_size",20,100,"adsorption;complexation"),
]


def material_table():
    columns = ["material_id","material_name","formula_or_family","seed_size_min_nm",
               "seed_size_max_nm","seed_dimension_type","seed_surface_area_min_m2_g",
               "seed_surface_area_max_m2_g","seed_processes"]
    frame = pd.DataFrame(MATERIALS, columns=columns)
    frame["seed_source_id"] = "USER_LIST"
    frame["seed_properties_verified"] = False
    frame["seed_properties_use"] = "Display only; do not impute experimental values or train on these ranges"
    return frame


def build_tables(seed):
    materials = material_table()
    sources = pd.DataFrame(seed["sources"])
    profiles = pd.DataFrame(seed["profiles"])
    evidence = pd.DataFrame(seed["evidence"])
    assert len(materials) == 15 and materials.material_id.is_unique
    for frame, key in [(sources,"source_id"),(profiles,"profile_id"),(evidence,"evidence_id")]:
        if not frame[key].is_unique:
            raise ValueError(f"Duplicate identifiers: {key}")
    if not set(profiles.material_id) <= set(materials.material_id):
        raise ValueError("Unknown material family")
    if not set(profiles.source_id) <= set(sources.source_id):
        raise ValueError("Profile source missing")
    if not set(evidence.profile_id) <= set(profiles.profile_id):
        raise ValueError("Evidence profile missing")
    if not set(evidence.pollutant_id) <= {r["pollutant_id"] for r in POLLUTANTS}:
        raise ValueError("Unknown pollutant")
    evidence = evidence.merge(profiles[["profile_id","material_id","source_id","light_requirement"]],
                              on="profile_id", validate="many_to_one")
    evidence["study_id"] = evidence.source_id.map(sources.set_index("source_id").doi)
    evidence["source_url"] = evidence.source_id.map(sources.set_index("source_id").url)
    evidence["reviewed_scope"] = evidence.source_id.map(sources.set_index("source_id").reviewed_scope)
    evidence["verified"] = True
    evidence["verification_meaning"] = "Claim checked against inspected source scope; not independent experimental replication"
    evidence["review_date"] = seed["review_date"]
    evidence["requires_profile_match"] = True
    evidence["ml_training_eligible"] = False
    evidence["applicability_status"] = "Evidence for profile and pollutant; scenario match not yet evaluated"
    evidence["claim_type"] = "literature_observation_not_prediction"
    for col in ["pH","dose_g_L","concentration_mg_L","time_min","temperature_C",
                "temperature_K","result_value","result_unit","result_uncertainty",
                "result_qualifier","dose_reported","concentration_reported","derivation"]:
        if col not in evidence:
            evidence[col] = None
    # Keep collection fields machine-readable, never as Python repr strings in CSV.
    if "studied_pH_values" in evidence:
        evidence["studied_pH_values"] = evidence.studied_pH_values.map(
            lambda v: json.dumps(v) if isinstance(v,list) else None)
    numeric = pd.to_numeric(evidence.result_value, errors="coerce")
    percent = evidence.result_unit.eq("percent")
    if not numeric[percent].between(0,100).all():
        raise ValueError("Invalid percentage observation")
    if evidence.loc[numeric.notna(),"result_unit"].isna().any():
        raise ValueError("Numeric outcome missing its unit")
    return materials, sources, profiles, evidence


def coverage_table(materials, evidence):
    records=[]
    for material_id in materials.material_id:
        for pollutant in POLLUTANTS:
            selected=evidence.loc[(evidence.material_id==material_id)&
                                  (evidence.pollutant_id==pollutant["pollutant_id"])]
            records.append({"material_id":material_id,"pollutant_id":pollutant["pollutant_id"],
                            "literature_records":len(selected),"independent_studies":selected.study_id.nunique(),
                            "evidence_ids":";".join(sorted(selected.evidence_id)),
                            "status":"verified_profile_evidence" if len(selected) else "insufficient_evidence",
                            "meaning":"No scenario score assigned; absence is a database gap, not evidence of failure"})
    return pd.DataFrame(records)


def main():
    path=ROOT / "data/curation/evidence_seed.json"
    seed=json.loads(path.read_text(encoding="utf-8"))
    materials,sources,profiles,evidence=build_tables(seed)
    sources["access_date"]=seed["review_date"]
    sources["verification_limit"]="Full text only where reviewed_scope says so; indexed abstracts do not establish complete conditions"
    sources["cache_sha256"]=None
    for idx,row in sources.iterrows():
        if isinstance(row.get("cache_path"),str):
            file=ROOT / row.cache_path
            if not file.exists():
                raise FileNotFoundError(file)
            sources.at[idx,"cache_sha256"]=hashlib.sha256(file.read_bytes()).hexdigest()
    seed_source={"source_id":"USER_LIST","title":"Material list supplied in project conversation",
                 "url":"user_supplied_project_context","reviewed_scope":"unverified_catalogue_seed",
                 "access_date":seed["review_date"],"verification_limit":"No experimental support or universal property values implied"}
    stage_a_sources=[
        {"source_id":"A01","title":"TiO2 photodegradation experimental data repository", "url":"https://github.com/mahyavs/GNN_photodegradation", "reviewed_scope":"cached_data_and_code", "access_date":seed["review_date"], "verification_limit":"See data/source_manifest.json for immutable commit and file hashes; repository reuse terms unverified"},
        {"source_id":"A02","title":"Predicting photodegradation rate constants of water pollutants on TiO2 using graph neural network and combined experimental graph features", "doi":"10.1038/s41598-025-04220-z", "url":"https://pmc.ncbi.nlm.nih.gov/articles/PMC12126497/", "reviewed_scope":"cached_full_text", "cache_path":"data/raw/tio2/paper.xml", "access_date":seed["review_date"], "verification_limit":"Dataset methodology source, not a new independent treatment experiment"},
    ]
    sources=pd.concat([sources,pd.DataFrame([seed_source]+stage_a_sources)],ignore_index=True)
    coverage=coverage_table(materials,evidence)
    for name,frame in [("materials",materials),("sources",sources),("material_profiles",profiles),
                       ("evidence",evidence),("pollutants",pd.DataFrame(POLLUTANTS)),
                       ("excluded_transfers",pd.DataFrame(seed["excluded_transfers"]))]:
        frame.to_csv(ROOT / f"data/{name}.csv",index=False)
    coverage.to_csv(ROOT / "outputs/evidence_coverage.csv",index=False)
    pivot=coverage.pivot(index="material_id",columns="pollutant_id",values="independent_studies").reindex(materials.material_id)
    rows="\n".join(f"| {r.material_id} | {r.material_name} | "+" | ".join(str(int(pivot.loc[r.material_id,k])) for k in ["sulfamethoxazole","amaranth","lead_ii"])+" |" for r in materials.itertuples())
    covered=int((coverage.literature_records>0).sum())
    report=f"""# Stage B catalogue and evidence audit

## Completed scope

- All 15 material families are registered with stable IDs M01 to M15.
- {len(profiles)} study specific material profiles and {len(evidence)} reviewed observations from {evidence.study_id.nunique()} independent papers.
- Three named pollutants: sulfamethoxazole, amaranth dye and dissolved lead II. The first two are present in the audited ML dataset; lead is evidence only.
- {covered} of 45 material and pollutant pairs have profile specific evidence. {45-covered} remain insufficient evidence.
- Four rejected evidence transfers are recorded to prevent composite, measurement and configuration mixups.

## Coverage by independent study count

| ID | Material | Sulfamethoxazole | Amaranth dye | Lead II |
|---|---|---:|---:|---:|
{rows}

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

Run `.\\.venv\\Scripts\\python.exe -m src.catalogue` from the project root. This rebuilds all tables without internet. It uses the reviewed seed and the two cached papers. Run pytest afterward. Regeneration must not modify the original TiO2 dataset or its audit.

## Next stage

Train and evaluate one TiO2 regression task on the original audited dataset. Keep study provenance and logarithm base limitations from Stage A. The 16 literature rows are not a new pooled training dataset. Numerical predictions remain disabled until that evaluation. Ranking rules will be implemented after training; no preference scores or winners have been assigned in Stage B.
"""
    (ROOT / "outputs/evidence_audit.md").write_text(report,encoding="utf-8")
    summary={"materials":len(materials),"pollutants":len(POLLUTANTS),"profiles":len(profiles),
             "evidence_records":len(evidence),"independent_studies":evidence.study_id.nunique(),
             "covered_pairs":covered,"total_pairs":len(coverage),
             "uncovered_materials":sorted(set(materials.material_id)-set(evidence.material_id)),
             "seed_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"review_date":seed["review_date"]}
    (ROOT / "outputs/evidence_audit.json").write_text(json.dumps(summary,indent=2),encoding="utf-8")
    notebook={"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"}},"cells":[
        {"cell_type":"markdown","id":"scope","metadata":{},"source":["# Material catalogue and research evidence\n","Stage B: all 15 families are assessed for evidence coverage. These are published observations, not trained predictions or preference rankings."]},
        {"cell_type":"code","id":"load","metadata":{},"execution_count":None,"outputs":[],"source":["from pathlib import Path\n","import json\n","import pandas as pd\n","ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\n","summary = json.loads((ROOT / 'outputs/evidence_audit.json').read_text())\n","print(summary)\n","materials = pd.read_csv(ROOT / 'data/materials.csv')\n","evidence = pd.read_csv(ROOT / 'data/evidence.csv')\n","coverage = pd.read_csv(ROOT / 'outputs/evidence_coverage.csv')\n","profiles = pd.read_csv(ROOT / 'data/material_profiles.csv')\n","sources = pd.read_csv(ROOT / 'data/sources.csv')"]},
        {"cell_type":"markdown","id":"coverage-note","metadata":{},"source":["## Independent study counts\n","Zero means an evidence gap in this bounded database. It does not mean the material fails. Multiple rows from one paper count once."]},
        {"cell_type":"code","id":"coverage","metadata":{},"execution_count":None,"outputs":[],"source":["coverage.merge(materials[['material_id', 'material_name']], on='material_id').pivot(index=['material_id', 'material_name'], columns='pollutant_id', values='independent_studies')"]},
        {"cell_type":"markdown","id":"units-note","metadata":{},"source":["## Observations for a chosen pollutant\n","Change pollutant_id below. Capacity, rate constants and percentages remain separate endpoints. Unknown operating conditions stay blank."]},
        {"cell_type":"code","id":"evidence","metadata":{},"execution_count":None,"outputs":[],"source":["pollutant_id = 'sulfamethoxazole'\n","evidence.loc[evidence.pollutant_id == pollutant_id, ['evidence_id', 'material_id', 'profile_id', 'endpoint', 'result_value', 'result_unit', 'pH', 'time_min', 'reviewed_scope', 'source_id', 'limitations']]"]},
        {"cell_type":"code","id":"formulations","metadata":{},"execution_count":None,"outputs":[],"source":["profiles[['profile_id', 'material_id', 'formulation', 'light_requirement', 'recovery_method']]"]},
        {"cell_type":"code","id":"sources","metadata":{},"execution_count":None,"outputs":[],"source":["sources[['source_id', 'title', 'url', 'reviewed_scope']]"]},
        {"cell_type":"markdown","id":"next","metadata":{},"source":["## Next stage\n","Train one evaluated TiO2 task using the Stage A dataset. Do not pool these 16 literature rows into it. No material preference score or winner exists yet."]}
    ]}
    (ROOT / "notebooks/02_catalogue_evidence.ipynb").write_text(json.dumps(notebook,indent=2),encoding="utf-8")
    print(json.dumps(summary,indent=2))


if __name__=="__main__":
    main()
