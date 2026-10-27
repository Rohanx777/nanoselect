"""Recheck the saved TiO2 holdout and summarize evidence for other models.

This is a read-only evaluation of project inputs; only the Step 6 JSON report is
written. It does not retrain, refit, or alter the model, split or catalogue.
"""
import hashlib
import json
from pathlib import Path
import sys

import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

ROOT=Path(__file__).resolve().parents[1] / 'nanomaterial_hybrid'
sys.path.insert(0,str(ROOT))
from src.predict import FEATURES, assess_inputs, scenario_from_row

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def metrics(y,p):
    return {'n':len(y),'mae':float(mean_absolute_error(y,p)),
            'rmse':float(np.sqrt(mean_squared_error(y,p))),'r2':float(r2_score(y,p))}

card=json.loads((ROOT/'models/model_card.json').read_text(encoding='utf-8'))
domain=json.loads((ROOT/'models/domain.json').read_text(encoding='utf-8'))
model=ROOT/'models'/card['artifact_filename']
data=ROOT/'data/processed/tio2_audited.csv'
config=ROOT/'config/training.json'
checks={'model_hash_matches_card':sha(model)==card['artifact_sha256'],
        'training_data_hash_matches_card':sha(data)==card['data_sha256'],
        'training_config_hash_matches_card':sha(config)==card['training_config_sha256']}
data_bytes=data.read_bytes()
crlf_bytes=data_bytes.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
checks['training_data_crlf_hash_matches_card']=hashlib.sha256(crlf_bytes).hexdigest()==card['data_sha256']
checks['training_data_matches_raw_or_crlf']=checks['training_data_hash_matches_card'] or checks['training_data_crlf_hash_matches_card']
if not (checks['model_hash_matches_card'] and checks['training_config_hash_matches_card']):
    raise RuntimeError(f'Recorded integrity check failed: {checks}')

frame=pd.read_csv(data)
split=pd.read_csv(ROOT/'outputs/train_test_split.csv')
saved=pd.read_csv(ROOT/'outputs/test_predictions.csv')
if not frame.source_row.is_unique or not split.source_row.is_unique or not saved.source_row.is_unique:
    raise ValueError('Source rows must be unique.')
checks['all_source_rows_match_split']=set(frame.source_row)==set(split.source_row)
checks['no_exact_input_group_overlap']=not bool(set(split.loc[split.split.eq('train'),'input_group_id']) & set(split.loc[split.split.eq('test'),'input_group_id']))
test=frame.merge(split[['source_row','split']],on='source_row',validate='one_to_one')
test=test.loc[test.split.eq('test')].merge(saved[['source_row','predicted_mlogk','baseline_mlogk','eligible_under_domain_policy']],on='source_row',validate='one_to_one')
if set(test.source_row)!=set(saved.source_row):
    raise ValueError('Saved test predictions do not match the recorded test split.')

pipeline=joblib.load(model)
forest=pipeline.named_steps['model']
forest.n_jobs=1
prediction=pipeline.predict(test[FEATURES])
eligible=np.array([assess_inputs(scenario_from_row(row),domain)['eligible'] for _,row in test.iterrows()],dtype=bool)
checks['saved_predictions_match']=bool(np.allclose(prediction,test.predicted_mlogk.to_numpy(),atol=1e-11,rtol=0))
checks['saved_eligibility_matches']=bool(np.array_equal(eligible,test.eligible_under_domain_policy.to_numpy(dtype=bool)))
current=metrics(test.mlogk,prediction)
baseline=metrics(test.mlogk,test.baseline_mlogk)
eligible_metrics=metrics(test.mlogk.to_numpy()[eligible],prediction[eligible]) if eligible.sum()>1 else None
checks['reported_metrics_match']=all(np.isclose(current[k],card['test_metrics'][k],atol=1e-11,rtol=0) for k in ['mae','rmse','r2'])
checks['eligible_metrics_match']=eligible_metrics is not None and eligible_metrics['n']==card['eligible_test_rows'] and all(np.isclose(eligible_metrics[k],card['eligible_test_metrics'][k],atol=1e-11,rtol=0) for k in ['mae','rmse','r2'])

test=test.assign(recomputed_prediction=prediction,eligible=eligible)
breakdown=[]
for name in ['Sulfamethoxazole','Amaranth']:
    rows=test.loc[test.Molecule_Name.str.casefold().eq(name.casefold())]
    accepted=rows.loc[rows.eligible]
    breakdown.append({'pollutant':name,'n':len(rows),'eligible_n':len(accepted),
                      'mae_all_holdout':float(mean_absolute_error(rows.mlogk,rows.recomputed_prediction)) if len(rows) else None,
                      'mae_eligible_holdout':float(mean_absolute_error(accepted.mlogk,accepted.recomputed_prediction)) if len(accepted) else None})

evidence=pd.read_csv(ROOT/'data/evidence.csv')
review=pd.read_csv(ROOT.parent/'research/step4-reviewed-evidence.csv')
material_summary=[]
for material in pd.read_csv(ROOT/'data/materials.csv').itertuples():
    rows=evidence.loc[evidence.material_id.eq(material.material_id)]
    material_summary.append({'material_id':material.material_id,'material_name':material.material_name,
                             'literature_rows':len(rows),'studies':int(rows.study_id.nunique()),
                             'ml_training_eligible_rows':int(rows.ml_training_eligible.fillna(False).astype(bool).sum())})

result={'checks':checks,'holdout_metrics_recomputed':current,'baseline_saved_predictions_metrics':baseline,
        'eligible_holdout_metrics_recomputed':eligible_metrics,'pollutant_holdout_breakdown':breakdown,
        'test_rows_outside_domain':int((~eligible).sum()),
        'training_pollutant_categories_supported':sum(x['eligible_category'] for x in domain['pollutants'].values()),
        'study_independent_validation':False,'material_evidence_summary':material_summary,
        'staged_review_rows':len(review),'staged_independent_studies':int(review.study_id.nunique()),
        'staged_experimental_rows_not_yet_training_data':True,
        'caution':'Replaying a saved test set is a reproducibility check, not new independent validation.'}
output=ROOT.parent/'research/step6-model-audit.json'
output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
if not all(value for key,value in checks.items() if key not in ('training_data_hash_matches_card','training_data_crlf_hash_matches_card')):
    raise SystemExit('One or more model audit checks failed.')
