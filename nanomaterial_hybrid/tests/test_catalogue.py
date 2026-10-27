import json
import hashlib

import pandas as pd
import pytest

from src.catalogue import ROOT, build_tables, coverage_table


def load_tables():
    return build_tables(json.loads((ROOT / "data/curation/evidence_seed.json").read_text()))


def test_all_fifteen_families_and_unknowns_remain_visible():
    materials,_,_,evidence=load_tables()
    coverage=coverage_table(materials,evidence)
    assert set(materials.material_id)=={f"M{i:02d}" for i in range(1,16)}
    assert len(coverage)==45
    assert coverage.loc[coverage.material_id=="M04","status"].eq("insufficient_evidence").all()
    assert not materials.seed_properties_verified.any()


def test_multiple_observations_are_not_independent_studies():
    materials,_,_,evidence=load_tables()
    coverage=coverage_table(materials,evidence)
    go=coverage.loc[(coverage.material_id=="M06")&(coverage.pollutant_id=="lead_ii")].iloc[0]
    assert go.literature_records==3
    assert go.independent_studies==1


def test_no_numeric_unit_or_profile_transfer():
    _,_,profiles,evidence=load_tables()
    data=evidence.set_index("evidence_id")
    assert data.loc["E009","result_unit"]=="mmol/g"
    assert data.loc["E013","endpoint"]=="experimental_maximum_capacity"
    assert data.loc["E013","result_value"]==265
    assert data.loc["E016","result_value"]==55
    assert data.loc["E016","material_id"]=="M10"
    assert data.loc["E017","material_id"]=="M05"
    assert data.loc["E017","result_value"]==29.91
    assert data.loc["E017","result_unit"]=="mg/g"
    assert "shell" in profiles.set_index("profile_id").loc["P12","formulation"].lower()
    assert pd.isna(data.loc["E017","dose_g_L"])
    assert data.loc["E018","result_qualifier"]=="up_to"
    assert data.loc["E019","result_min"]==83 and data.loc["E019","result_max"]==91
    assert pd.isna(data.loc["E019","result_value"])
    assert profiles.set_index("profile_id").loc["P14","light_requirement"]=="not_specified_in_source"
    assert not (evidence.material_id=="M14").any()
    assert not evidence.ml_training_eligible.any()
    assert evidence.requires_profile_match.all()
    assert pd.isna(data.loc["E008","time_min"])
    assert pd.isna(data.loc["E008","dose_g_L"])
    assert profiles.set_index("profile_id").loc["P03","length_nm"]==755


def test_corrupt_source_reference_is_rejected():
    seed=json.loads((ROOT / "data/curation/evidence_seed.json").read_text())
    seed["profiles"][0]["source_id"]="missing_source"
    with pytest.raises(ValueError,match="Profile source missing"):
        build_tables(seed)


def test_invalid_percentage_is_rejected():
    seed=json.loads((ROOT / "data/curation/evidence_seed.json").read_text())
    seed["evidence"][1]["result_value"]=150
    with pytest.raises(ValueError,match="Invalid percentage"):
        build_tables(seed)


def test_invalid_percentage_range_is_rejected():
    seed=json.loads((ROOT / "data/curation/evidence_seed.json").read_text())
    seed["evidence"][-1]["result_min"]=95
    with pytest.raises(ValueError,match="Invalid percentage range"):
        build_tables(seed)


def test_cached_full_text_sources_match_recorded_hashes():
    sources=pd.read_csv(ROOT / "data/sources.csv")
    cached=sources.dropna(subset=["cache_path","cache_sha256"])
    assert len(cached)>=2
    for source in cached.itertuples():
        assert hashlib.sha256((ROOT / source.cache_path).read_bytes()).hexdigest()==source.cache_sha256
