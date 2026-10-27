"""Regenerate reviewed profile and evidence tables while preserving source cache metadata."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import pandas as pd
from src.catalogue import build_tables, coverage_table

seed = json.loads((ROOT / 'data/curation/evidence_seed.json').read_text(encoding='utf-8'))
materials, sources, profiles, evidence = build_tables(seed)
old_sources = pd.read_csv(ROOT / 'data/sources.csv')
new_sources = sources.loc[~sources.source_id.isin(old_sources.source_id)].copy()
new_sources['access_date'] = '2026-10-27'
new_sources['verification_limit'] = 'Only the stated abstract and methods were reviewed; no generalization to unsupported materials or full-scale recovery.'
pd.concat([old_sources, new_sources], ignore_index=True).to_csv(ROOT / 'data/sources.csv', index=False)
profiles.to_csv(ROOT / 'data/material_profiles.csv', index=False)
evidence.to_csv(ROOT / 'data/evidence.csv', index=False)
coverage_table(materials, evidence).to_csv(ROOT / 'outputs/evidence_coverage.csv', index=False)
print(f'{len(evidence)} evidence records across {len(profiles)} profiles')
