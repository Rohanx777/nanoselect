"""Representative behavior checks; not laboratory or study-independent validation."""
import math
import pandas as pd
import pytest

from src.predict import PROFILE, scenario_from_row
from src.recommend import RecommendationEngine, load_demo


@pytest.fixture(scope='module')
def engine():
    return RecommendationEngine()


def assess(engine,scenario,weights=None):
    frame=engine.recommend(scenario,weights=weights)
    assert len(frame)==15 and frame.material_id.is_unique
    return frame.set_index('material_id')


def test_missing_light_intensity_disables_only_the_ml_estimate(engine):
    scenario=dict(load_demo('demo_ml'),light_intensity_mW_cm2=None)
    result=assess(engine,scenario)
    assert pd.isna(result.loc['M02','prediction'])
    assert 'light_intensity_mW_cm2' in result.loc['M02','ml_fallback_reason']
    assert 'M03' in result.attrs['summary']['top_candidates']


@pytest.mark.parametrize('field,value',[
    ('pH',6),('dose_g_L',2),('temperature_C',30),('time_min',20),
    ('concentration_mg_L',100),('water_matrix','groundwater')])
def test_changing_any_source_match_condition_removes_exact_support(engine,field,value):
    scenario=dict(load_demo('demo_lead'),**{field:value})
    result=assess(engine,scenario)
    assert result.loc['M13','status']!='supported'
    assert not (result.loc['M13','score_min']==100 and result.loc['M13','score_max']==100)


def test_extreme_priority_changes_ranking_but_does_not_leak(engine):
    scenario=load_demo('demo_lead')
    before=assess(engine,scenario)
    changed=assess(engine,scenario,{'suitability':0,'setup':0,'recovery':1})
    after=assess(engine,scenario)
    assert before.attrs['summary']['top_candidates']==['M13']
    assert changed.attrs['summary']['top_candidates']!=before.attrs['summary']['top_candidates']
    assert after.attrs['summary']['top_candidates']==before.attrs['summary']['top_candidates']


def test_amaranth_holdout_eligible_prediction_uses_tio2_only(engine):
    data=pd.read_csv('data/processed/tio2_audited.csv')
    held=pd.read_csv('outputs/test_predictions.csv')
    eligible=held.loc[held.Molecule_Name.eq('Amaranth') & held.eligible_under_domain_policy]
    assert len(eligible)>0
    row=data.set_index('source_row').loc[eligible.iloc[0].source_row]
    scenario=scenario_from_row(row)
    scenario.pop('material_id')
    scenario.pop('profile_id')
    scenario.update(requested_endpoint='qualitative_remediation',prediction_endpoint='mlogk',
                    include_ml=True,profile_choices={'M02':PROFILE},consider_study_profiles=True,
                    allow_conditional_ranking=True,available_equipment=['mixer','filtration'])
    result=assess(engine,scenario)
    assert result.attrs['summary']['pollutant_id']=='amaranth'
    assert math.isfinite(result.loc['M02','prediction'])
    assert result.prediction.notna().sum()==1


@pytest.mark.parametrize('pollutant',['arsenic','chromium','methylene blue',''])
def test_unsupported_pollutants_never_receive_a_rank(engine,pollutant):
    scenario=dict(load_demo('demo_ml'),pollutant_id=pollutant)
    result=assess(engine,scenario)
    assert result.attrs['summary']['request_supported'] is False
    assert result.attrs['summary']['top_candidates']==[]
    assert result.preference_tier.isna().all() and result.prediction.isna().all()


@pytest.mark.parametrize('field,value',[
    ('pH',-1),('pH',14.1),('dose_g_L',0),('concentration_mg_L',-1),
    ('time_min',0),('light_intensity_mW_cm2',float('nan')),
    ('required_removal_percent',101)])
def test_out_of_range_values_are_rejected(engine,field,value):
    scenario=dict(load_demo('demo_ml'),**{field:value})
    with pytest.raises(ValueError):
        engine.recommend(scenario)
