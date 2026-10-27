"""Reproducible Stage A audit; no fitted models and no invented descriptors."""
from __future__ import annotations

import hashlib
import json
import platform
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NUMERIC = ["I", "T", "D", "C0", "pH", "mlogk"]
INPUTS = ["SMILES", "I", "T", "D", "C0", "pH"]
UNITS = {"I": "mW/cm^2 (UV intensity)", "T": "degrees C", "D": "g/L (TiO2 dose)",
         "C0": "mg/L (initial pollutant concentration)", "pH": "dimensionless",
         "mlogk": "reported -log(k); k in min^-1; logarithm base not yet independently confirmed"}


def clean_frame(raw):
    frame = raw.copy()
    frame.insert(0, "source_row", range(2, len(frame) + 2))
    for col in ["Molecule_Name", "SMILES"]:
        frame[col] = frame[col].astype("string").str.strip()
    for col in NUMERIC:
        frame[col] = pd.to_numeric(frame[col], errors="coerce")
    return frame


def summarise(raw):
    frame = clean_frame(raw)
    core = INPUTS + ["mlogk"]
    conflicts = frame.groupby(INPUTS, dropna=False)["mlogk"].nunique()
    return {
        "rows": len(frame), "columns": list(raw.columns),
        "missing": {c: int(v) for c, v in frame.drop(columns="source_row").isna().sum().items()},
        "raw_exact_duplicates": int(raw.duplicated().sum()),
        "normalised_exact_duplicates": int(frame.duplicated(subset=core).sum()),
        "unique_names_after_strip": int(frame.Molecule_Name.nunique()),
        "unique_smiles_strings": int(frame.SMILES.nunique()),
        "name_to_smiles_conflicts": int((frame.groupby("Molecule_Name").SMILES.nunique() > 1).sum()),
        "smiles_to_name_conflicts": int((frame.groupby("SMILES").Molecule_Name.nunique() > 1).sum()),
        "same_input_groups_with_different_targets": int((conflicts > 1).sum()),
        "numeric_ranges": {c: {"min": float(frame[c].min()), "max": float(frame[c].max())} for c in NUMERIC},
        "pollutant_counts": {k: int(v) for k,v in frame.Molecule_Name.value_counts().items()},
        "zero_or_negative_dose_rows": int((frame.D <= 0).sum()),
    }


def main():
    for folder in ["outputs", "data/processed", "models", "notebooks", "tests", "config"]:
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    summaries = {}
    for name in ["original_data.xlsx", "curated_data.xlsx"]:
        file = ROOT / "data/raw/tio2/data" / name
        sheets = pd.read_excel(file, sheet_name=None)
        summaries[name] = {sheet: summarise(raw) for sheet, raw in sheets.items()}
    raw = pd.read_excel(ROOT / "data/raw/tio2/data/original_data.xlsx")
    frame = clean_frame(raw)
    duplicates = frame.duplicated(subset=INPUTS + ["mlogk"])
    invalid = (frame[NUMERIC].isna().any(axis=1) | (frame.I <= 0) | (frame.D <= 0)
               | (frame.C0 <= 0) | ~frame.pH.between(0,14)
               | frame.SMILES.isna() | frame.Molecule_Name.isna())
    excluded = frame.loc[duplicates | invalid].copy()
    excluded["exclusion_reason"] = ["exact_duplicate" if duplicates.loc[i] else "invalid_or_nonpositive_operating_input" for i in excluded.index]
    excluded.to_csv(ROOT / "outputs/excluded_rows.csv", index=False)
    cleaned = frame.loc[~(duplicates | invalid)].copy()
    # Group identical inputs together later; this is not a recovered study identifier.
    cleaned["input_group_id"] = cleaned.apply(
        lambda row: hashlib.sha256(json.dumps([str(row[c]) for c in INPUTS]).encode()).hexdigest()[:16], axis=1)
    cleaned["material_id"] = "M02"
    cleaned["material_profile_status"] = "TiO2 family only; grade and batch unavailable"
    cleaned.to_csv(ROOT / "data/processed/tio2_audited.csv", index=False)
    pd.DataFrame([{ "field": k, "unit_or_definition": v} for k,v in UNITS.items()]).to_csv(ROOT / "outputs/data_dictionary.csv", index=False)
    coverage = cleaned.groupby(["Molecule_Name", "SMILES"], as_index=False).agg(
        records=("mlogk", "size"), distinct_input_groups=("input_group_id", "nunique"))
    coverage.sort_values("records", ascending=False).to_csv(ROOT / "outputs/pollutant_coverage.csv", index=False)
    result = {"workbooks": summaries, "selected_source": "original_data.xlsx",
              "cleaned_rows": len(cleaned), "excluded_rows": len(excluded),
              "features": INPUTS, "target": "mlogk", "units": UNITS,
              "study_ids_available": False, "log_base_verified": False,
              "python_version_used_for_audit": platform.python_version()}
    (ROOT / "outputs/data_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    rows = "\n".join(f"| {r.Molecule_Name} | {r.records} | {r.distinct_input_groups} |" for r in coverage.sort_values("records", ascending=False).head(10).itertuples())
    original = summaries["original_data.xlsx"]["Sheet1"]
    report = f"""# Stage A data audit

## Decision

Proceed with a preliminary TiO2 operating condition regression task predicting the reported `mlogk` target. Use the original workbook, not the outcome curated workbook, as the source for our own evaluation. No model has been trained yet. This dataset cannot train a 15 material comparison.

## Actual downloaded files

Repository commit: `c59e1a748b36b87eb051d9ce0acf6962bab1d118`.
Original: {original['rows']} rows. Curated: {summaries['curated_data.xlsx']['Sheet1']['rows']} rows. Both have one sheet and eight columns. The paper describes an earlier 446 record collection; use the actual downloaded counts in our report.

The original workbook has {original['raw_exact_duplicates']} exact duplicate and {original['unique_names_after_strip']} pollutant names after whitespace normalisation, matching {original['unique_smiles_strings']} distinct SMILES strings. All eight raw columns are populated. Exact SMILES strings are not chemically canonicalised or independently validated in this audit.

After deterministic exclusions: **{len(cleaned)} rows**. Excluded {len(excluded)} rows; see `excluded_rows.csv`. This removes exact duplicates and nonpositive catalyst doses, which cannot support a TiO2 treatment prediction. Other identical inputs with different measured targets remain; they may reflect repeats or missing context. Keep those inputs together in later splits.

## Features and outcome

Five operating inputs: I (UV intensity in mW/cm^2), T (degrees C), D (TiO2 dose in g/L), C0 (mg/L), and pH. Pollutant identity is supplied by SMILES or its verified name mapping. The human readable name is not an additional independent chemical descriptor.

The paper defines the target as -log(k), with k in min^-1. The inspected text and upstream code do not explicitly establish the logarithm base. **Train and label only `mlogk` for now; do not convert to k or removal percentage until the base is verified.** The supplied data does not include particle size, BET surface area, time, catalyst grade, batch, reactor geometry, wavelength or source study identifiers.

## Pollutant coverage

Methylene blue is absent. Switch the proposed ML demonstration to sulfamethoxazole or amaranth, subject to later validation and evidence matching. Do not claim predictions for methylene blue from this dataset.

| Pollutant | Cleaned records | Distinct input groups |
|---|---:|---:|
{rows}

The complete table is `pollutant_coverage.csv`. All numeric ranges and missing values are in `data_audit.json`; units are in `data_dictionary.csv`.

## Provenance and evaluation limitations

No row level study identifiers exist in either workbook. Identical input grouping can prevent direct duplicate leakage but cannot establish independent study performance. Prefer recovering original study provenance if possible within the time budget; otherwise label evaluation preliminary and explicitly state that study overlap may inflate results. A pollutant holdout can be an additional diagnostic for unseen molecules, not a substitute for study provenance.

The associated paper reports removing four points based on model residuals to create the curated dataset. To avoid inheriting this outcome informed filtering, our default is the original workbook with only documented input validity and duplicate exclusions. Do not remove rows merely because a model predicts them poorly.

There are {original['same_input_groups_with_different_targets']} original identical input groups with different targets. Missing experimental context limits identifiability. No material grade should be invented, and no claim of validation for a commercial grade is justified by these files alone.

## Sources and reuse

Data and upstream code: https://github.com/mahyavs/GNN_photodegradation

Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC12126497/

Cached full text XML: https://www.ebi.ac.uk/europepmc/webservices/rest/PMC12126497/fullTextXML

Original dataset paper DOI given by the associated paper: https://doi.org/10.1016/j.envres.2020.109697

Raw files are cached unchanged. `data/source_manifest.json` records URLs, commit and SHA256 values. No repository licence was located in the audited tree. Do not assume permission to redistribute the raw dataset; retain attribution and review reuse terms before publishing.

## Next stage

Build the 15 family catalogue and verified evidence records for a small pollutant set. Prefer one actual dataset pollutant for the first numerical demo. Then compare a baseline, Ridge and Random Forest using leakage aware evaluation. Training, evidence ranking and the full demo are not part of this completed setup stage.
"""
    (ROOT / "outputs/data_audit.md").write_text(report, encoding="utf-8")
    notebook = {"nbformat":4,"nbformat_minor":5,"metadata":{"kernelspec":{"display_name":"Python 3", "language":"python","name":"python3"}}, "cells":[
        {"cell_type":"markdown","metadata":{},"id":"scope","source":["# Nanomaterial project data audit\n", "Stage A only. No trained model or rankings yet. Run from this project environment."]},
        {"cell_type":"code","metadata":{},"id":"paths","execution_count":None,"outputs":[],"source":["from pathlib import Path\n", "import json\n", "import pandas as pd\n", "ROOT = Path.cwd() if (Path.cwd() / 'data').exists() else Path.cwd().parent\n", "audit = json.loads((ROOT / 'outputs/data_audit.json').read_text())\n", "print('Cleaned rows:', audit['cleaned_rows'])\n", "print('Target:', audit['target'])"]},
        {"cell_type":"code","metadata":{},"id":"coverage","execution_count":None,"outputs":[],"source":["pd.read_csv(ROOT / 'outputs/pollutant_coverage.csv').head(15)"]},
        {"cell_type":"markdown","metadata":{},"id":"limits","source":["## Limits\n", "No study identifiers or material descriptors. Methylene blue is absent. Logarithm base remains unverified. See outputs/data_audit.md before training."]}
    ]}
    (ROOT / "notebooks/01_data_audit.ipynb").write_text(json.dumps(notebook, indent=2), encoding="utf-8")
    print(f"Audit complete: {len(cleaned)} retained rows, {len(excluded)} exclusions; no models trained.")


if __name__ == "__main__":
    main()
