"""Build a review-only evidence table from source-scoped observations.

This does not write the application's ranking catalogue or training data.
"""
import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIELDS = ["review_id", "study_id", "source_url", "source_scope", "material_candidates",
          "formulation", "formulation_type", "pollutant_species", "water_matrix", "ph",
          "initial_concentration_mg_l", "dose_g_l", "contact_time_min", "temperature_c",
          "light", "equipment", "endpoint", "value", "value_min", "value_max", "unit",
          "qualifier", "condition_notes", "conversion", "limitations", "review_status"]
records=[]

def add(review_id, study_id, source_url, source_scope, material_candidates, formulation,
        formulation_type, pollutant_species, endpoint, unit, limitations, review_status, **values):
    row=dict(review_id=review_id, study_id=study_id, source_url=source_url,
             source_scope=source_scope, material_candidates=material_candidates,
             formulation=formulation, formulation_type=formulation_type,
             pollutant_species=pollutant_species, endpoint=endpoint, unit=unit,
             limitations=limitations, review_status=review_status, **values)
    unknown=set(row)-set(FIELDS)
    if unknown:
        raise ValueError(f'Unexpected fields in {review_id}: {unknown}')
    records.append(row)

add('R001','10.1016/j.chemosphere.2015.03.061','https://www.sciencedirect.com/science/article/abs/pii/S0045653515002842',
    'Publisher abstract','M06','Graphene oxide','GO','sulfamethoxazole','reported_removal','percent',
    'Up to value over unspecified conditions; dose and pH for the stated value not resolved. Sonication gives a separate outcome.',
    'conditionally_curated',value=12,qualifier='up to; within 6 h',condition_notes='Within 6 hours; exact time at maximum not identified.')

add('R002','10.1016/j.scitotenv.2020.143307','https://pubmed.ncbi.nlm.nih.gov/33189375/',
    'Indexed PubMed abstract','M05','Nanoscale zero-valent iron particles','nZVI','sulfamethoxazole','reported_removal_range','percent',
    'Acidic range covers more than one pH; exact time and conditions per endpoint are not identified in abstract.',
    'conditionally_curated',value_min=83,value_max=91,qualifier='range',
    condition_notes='Acidic conditions; nZVI to SMX mass ratio 10:1. Study included pH 3 and 5; values not individually attributed.')

for i, result in enumerate([95.98,97.24,98.01],start=1):
    add(f'R00{2+i}','10.1038/s41598-023-41823-w','https://pmc.ncbi.nlm.nih.gov/articles/PMC10475053/',
        'Indexed full text: methods and Table 5','M01;M15','Magnetite–chitosan nanoparticles','magnetite_chitosan_composite',
        'sulfamethoxazole','experimental_removal','percent',
        'One composite and one study; three runs are replicates, not independent studies. Sonication and magnetic separation are required; no inference for either standalone constituent.',
        'hold_composite_and_sonication',value=result,ph=6,initial_concentration_mg_l=22,dose_g_l=1.3,
        contact_time_min=15,water_matrix='aqueous experimental solution',equipment='ultrasonic bath; centrifuge; external magnet',
        qualifier=f'experimental replicate {i} of 3',conversion='0.13 g in 100 mL = 1.3 g/L; table gives experimental and predicted values separately')

add('R006','PMID:31104171','https://pubmed.ncbi.nlm.nih.gov/31104171/',
    'Indexed PubMed abstract','M04;M07','Silver@reduced graphene oxide','silver_rgo_composite',
    'sulfamethoxazole','experimental_removal','percent',
    'Only composite performance is reported. Temperature, water chemistry, grade and recovery were not extracted from abstract.',
    'hold_composite',value=88,ph=5,initial_concentration_mg_l=30,dose_g_l=0.14,contact_time_min=60,
    water_matrix='aqueous solution',conversion='0.007 g / 0.05 L = 0.14 g/L; 3600 s = 60 min; 30 mg/dm3 = 30 mg/L')

for i,(loading,result) in enumerate([(10,9),(12,25),(15,29),(20,40)],start=7):
    add(f'R{i:03d}','10.1038/s41598-023-42680-3','https://pmc.ncbi.nlm.nih.gov/articles/PMC10511407/',
        'Indexed full text: amaranth results and Figure 11','M07',f'{loading}% CuS–rGO composite',
        'copper_sulfide_rgo_composite','amaranth','reported_dark_adsorption','percent',
        'Four formulations from one study are not independent studies. Conditions for each dark value are incomplete; do not infer full mineralization or standalone rGO performance.',
        'hold_composite',value=result,contact_time_min=60,light='dark',water_matrix='aqueous dye solution',
        qualifier='dark adsorption after 1 h',conversion='1 h = 60 min')

add('R011','CeO2-lead-2026','https://www.mdpi.com/2297-8739/13/2/61',
    'Indexed publisher abstract and Table 4','M12','Cerium oxide nanoparticles','ceria_nanoparticles',
    'lead_ii','experimental_adsorption_capacity','mg/g',
    'Experimental capacity differs from the reported fitted Langmuir capacity of 714.2 mg/g. Exact conditions for this value need confirmation.',
    'hold_condition_verification',value=192,ph=6,qualifier='maximum experimental capacity')
add('R012','CeO2-lead-2026','https://www.mdpi.com/2297-8739/13/2/61',
    'Indexed publisher abstract','M12','Cerium oxide nanoparticles','ceria_nanoparticles','lead_ii','reported_removal','percent',
    'Abstract gives 80% at pH 6 while a comparison table lists 90%; resolve conditions and discrepancy before use.',
    'hold_source_inconsistency',value=80,ph=6)

add('R013','10.1039/C5RA09483F','https://pubs.rsc.org/en/content/articlelanding/2015/ra/c5ra09483f',
    'Indexed publisher abstract','M14','Ionic-liquid-modified montmorillonite','modified_montmorillonite',
    'amaranth','calculated_adsorption_capacity','mg/g',
    'Modified material; nanoclay dimension not confirmed. Capacity is not percent removal. Full experiment conditions remain unextracted.',
    'hold_nanodimensions',value=263.2,qualifier='calculated maximum',condition_notes='Abstract reports optimum pH 2; not assumed to be the precise condition of this capacity.')

for review_id,formulation,kind,result in [('R014','Fe(0) nanoparticles','nzvi',55),('R015','Starch-stabilized Fe(0) nanoparticles','starch_stabilized_nzvi',98)]:
    add(review_id,'PMID:16187417','https://pmc.ncbi.nlm.nih.gov/articles/PMC1390446/',
        'Full text: batch methods and Figure 6 description','M05',formulation,kind,'chromium_vi',
        'reported_cr_vi_removal','percent',
        'Both records are same study and same comparison, not independent studies. Cr(VI) reduction is not proof of total chromium removal; nitrogen atmosphere and stirring are specified.',
        'hold_new_pollutant_and_setup',value=result,ph=7,initial_concentration_mg_l=20,dose_g_l=0.2,
        contact_time_min=60,temperature_c=25,water_matrix='aqueous dichromate',equipment='stirring at 600 rpm; nitrogen flow; 0.22 μm analytical filter',qualifier='approximately')

add('R016','10.1039/D4RA03697B','https://pubs.rsc.org/en/content/articlelanding/2024/ra/d4ra03697b',
    'Publisher abstract; indexed full-text methods','M06','Graphene oxide reported as GO-200 nm','graphene_oxide',
    'chromium_vi','langmuir_maximum_capacity','mg/g',
    'Model-fitted capacity, not percentage removal. Dimension definition and exact operating inputs associated with the fitted value require verification; adsorption of total chromium differs from Cr(VI) removal.',
    'hold_new_pollutant_and_conditions',value=41.27,temperature_c=25,qualifier='fitted Langmuir maximum')

add('R017','PMC7465564','https://pmc.ncbi.nlm.nih.gov/articles/PMC7465564/',
    'Indexed full-text methods','M01','CTAB-coated iron oxide','CTAB_coated_iron_oxide','arsenic_iii',
    'qualitative_batch_adsorption','',
    'Source methods describe a concentration series; no outcome is assigned to the whole series. Coated iron oxide is a distinct profile; analytical separation is not proof of total material recovery.',
    'hold_new_pollutant_and_quantitative_result',ph=5,dose_g_l=10,contact_time_min=1440,
    water_matrix='aqueous As(III) solution',equipment='roller mixer; centrifuge; filter',
    condition_notes='Initial As(III) concentration series reported as 0–100 mg/L; room temperature not assigned as exact value.',
    conversion='0.2 g in 20 mL = 10 g/L; 24 h = 1440 min')

add('R018','10.1016/j.inoche.2024.112033','https://www.sciencedirect.com/science/article/abs/pii/S1387700324000169',
    'Indexed publisher highlights','M10','Cu3(PO4)2/MgO composite','copper_phosphate_mgo_composite',
    'amaranth','reported_photocatalytic_degradation','percent',
    'Composite only. Indexed sources differ in dose reporting; 0.1 g/L versus 0.1 g per 300 mL. Outcome must not be imported until the original conditions are resolved.',
    'hold_conflicting_dose_and_composite',value=99,contact_time_min=150,light='natural sunlight',
    condition_notes='Initial dye concentration stated as 10 μM; no conversion to mg/L made without verifying species and molecular weight.')

for row in records:
    for key in ('value','value_min','value_max'):
        value=row.get(key)
        if value is not None and row.get('unit')=='percent' and not 0<=value<=100:
            raise ValueError(f'Invalid percentage in {row["review_id"]}')
    if row.get('value') is not None and not row.get('unit'):
        raise ValueError(f'Missing result unit in {row["review_id"]}')
    if not row['source_url'].startswith('https://'):
        raise ValueError(f'Invalid source in {row["review_id"]}')

with (HERE/'step4-reviewed-evidence.csv').open('w',encoding='utf-8-sig',newline='') as output:
    writer=csv.DictWriter(output,fieldnames=FIELDS)
    writer.writeheader()
    writer.writerows(records)
print(json.dumps({'records':len(records),'studies':len({r['study_id'] for r in records}),
                  'held':sum(r['review_status'].startswith('hold') for r in records)},indent=2))
