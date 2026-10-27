'use strict';
const $=id=>document.getElementById(id);
const state={meta:null,result:null,filter:'all',preset:'demo_ml',selected:[]};
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels={conditional:'Conditional',supported:'Source matched',incompatible_with_setup:'Setup mismatch',insufficient_evidence:'Evidence gap'};
const fieldMap={concentration:'concentration_mg_L',ph:'pH',dose:'dose_g_L',temperature:'temperature_C',time:'time_min',intensity:'light_intensity_mW_cm2'};
function number(id){const value=$(id).value;return value===''?null:Number(value);}
function updateVisibility(){ $('other-wrap').hidden=$('pollutant').value!=='other';$('target-wrap').hidden=!$('use-target').checked;$('intensity-wrap').hidden=!['UV','UVA'].includes($('light').value); }
function fill(scenario){
  const raw=String(scenario.pollutant_id??'').toLowerCase();const known=['sulfamethoxazole','amaranth','lead_ii'].includes(raw);
  $('pollutant').value=known?raw:'other';$('other-pollutant').value=known?'':scenario.pollutant_id??'';
  Object.entries(fieldMap).forEach(([id,key])=>$(id).value=scenario[key]??'');
  $('light').value=scenario.light_type??'unspecified';$('matrix').value=scenario.water_matrix??'unspecified';
  ['mixer','centrifuge','filtration'].forEach(id=>$(id).checked=(scenario.available_equipment??[]).includes(id));
  $('profile').value=scenario.profile_choices?.M02??'automatic';$('include-ml').checked=!!scenario.include_ml;
  $('study-profiles').checked=!!scenario.consider_study_profiles;$('conditional').checked=!!scenario.allow_conditional_ranking;
  $('use-target').checked=scenario.requested_endpoint==='removal_percent';$('target').value=scenario.required_removal_percent??90;updateVisibility();
}
function readScenario(){
  const s={pollutant_id:$('pollutant').value==='other'?$('other-pollutant').value.trim():$('pollutant').value,
    light_type:$('light').value,water_matrix:$('matrix').value,available_equipment:['mixer','centrifuge','filtration'].filter(id=>$(id).checked),
    consider_study_profiles:$('study-profiles').checked,allow_conditional_ranking:$('conditional').checked,
    include_ml:$('include-ml').checked,prediction_endpoint:'mlogk',requested_endpoint:$('use-target').checked?'removal_percent':'qualitative_remediation',profile_choices:{}};
  Object.entries(fieldMap).forEach(([id,key])=>{s[key]=number(id);});
  if($('profile').value!=='automatic')s.profile_choices.M02=$('profile').value;
  if($('use-target').checked)s.required_removal_percent=number('target');
  return s;
}
function setPreset(name){state.preset=name;document.querySelectorAll('.preset').forEach(b=>b.classList.toggle('active',b.dataset.preset===name));fill(state.meta.presets[name]);run();}
const weightIds=['suitability','setup','recovery'];
function updateWeights(){const total=weightIds.reduce((sum,key)=>sum+(number('weight-'+key)??0),0);$('weight-total').textContent=`${total}%`;$('weight-total').parentElement.classList.toggle('invalid',total!==100);}
function readWeights(){const values=weightIds.map(key=>number('weight-'+key));if(values.some(v=>v===null||!Number.isFinite(v)||v<0||v>100)||Math.abs(values.reduce((a,b)=>a+b,0)-100)>0.000001)throw new Error('Decision priorities must be between 0 and 100 and total 100%.');return Object.fromEntries(weightIds.map((key,i)=>[key,values[i]/100]));}
async function run(){
  const button=$('run-button');button.disabled=true;button.querySelector('span').textContent='Analysing…';$('form-error').hidden=true;
  try{
    const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario:readScenario(),weights:readWeights()})});
    const data=await response.json();if(!response.ok)throw new Error(data.error??'Analysis could not complete.');state.result=data;state.filter='all';state.selected=data.summary.top_candidates.slice(0,3);$('result-stale').hidden=true;render();
  }catch(error){$('form-error').textContent=error.message;$('form-error').hidden=false;}
  finally{button.disabled=false;button.querySelector('span').textContent='Rank materials';$('loading').hidden=true;}
}
function render(){
  const {rows,summary}=state.result;const tops=rows.filter(r=>summary.top_candidates.includes(r.material_id));const winner=summary.unique_policy_winner;
  $('result-content').hidden=false;
  $('recommendation-title').textContent=tops.length>1?`${tops.length} candidates worth comparing`:tops.length===1?tops[0].material_name:'No supported recommendation';
  $('result-badge').textContent=tops.length>1?'Uncertain shortlist':tops.length===1?(tops[0].status==='supported'?'Source matched':'Conditional candidate'):'More evidence needed';
  $('recommendation-description').textContent=tops.length>1?'The score ranges overlap, so the current evidence does not justify a unique winner. Compare the selected formulations below.':winner?(tops[0].status==='supported'?'This formulation best matches the published experiment and your declared setup under the decision policy. Its performance is not independently validated.':'This is the remaining candidate among scored profiles. It needs further condition matching and recovery verification.'):summary.request_supported?'The current setup or missing inputs do not justify ranking a candidate. Review the details below.':'This pollutant is outside the current evidence catalogue. No material performance has been guessed.';
  $('shortlist-chips').innerHTML=tops.map(r=>`<span class="shortlist-chip"><b>${esc(r.material_id)}</b>${esc(r.material_name)}</span>`).join('');
  const gaps=rows.filter(r=>r.status==='insufficient_evidence').length;
  $('coverage-note').textContent=`15 materials assessed · ${summary.ranked_candidates} ranked · ${gaps} evidence gaps`;
  $('stability-note').textContent=summary.weight_sensitive?'Shortlist changes with alternate weights':'Shortlist unchanged in two weight checks';
  const ml=rows.find(r=>r.prediction!=null);const tio2=rows.find(r=>r.material_id==='M02');
  $('prediction-value').innerHTML=ml?`${Number(ml.prediction).toFixed(3)}<small>mlogk</small>`:'<small>No eligible ML estimate</small>';
  $('prediction-note').textContent=ml?'Experimental TiO₂ estimate in the dataset’s reported negative log rate target. Not removal percentage.':'Literature screening still works. Numerical prediction is limited to supported TiO₂ conditions.';
  $('ml-reasons').hidden=!!ml;$('ml-reason-text').textContent=tio2?.ml_fallback_reason||'Use the dataset TiO₂ profile, enable ML, and provide supported pollutant, UV, dose, pH, temperature, concentration and intensity inputs.';
  $('shortlist-count').textContent=tops.length;$('gap-count').textContent=gaps;renderRows();renderComparison();
}
function renderComparison(){
  const rows=state.result.rows;$('compare-count').textContent=`${state.selected.length} / 3 selected`;
  $('compare-choices').innerHTML=rows.map(r=>`<button type="button" class="compare-choice" data-compare="${esc(r.material_id)}" aria-pressed="${state.selected.includes(r.material_id)}" ${state.selected.length>=3&&!state.selected.includes(r.material_id)?'disabled':''}>${esc(r.material_name)}</button>`).join('');
  const selected=state.selected.map(id=>rows.find(r=>r.material_id===id)).filter(Boolean);
  $('compare-cards').innerHTML=selected.length?selected.map(r=>{const evidence=(state.result.evidence||[]).filter(e=>String(r.evidence_ids||'').split(';').includes(e.evidence_id));const rating=value=>value==null?'Unknown':`${value}/2`;return `<article class="compare-card"><span class="eyebrow">${esc(r.material_id)}</span><h3>${esc(r.material_name)}</h3><span class="status ${esc(r.status)}">${esc(labels[r.status])}</span><p><strong>Formulation:</strong> ${esc(r.formulation||'No applicable profile')}</p><p><strong>Mechanism:</strong> ${esc(evidence.map(e=>e.mechanism.replaceAll('_',' ')).filter((v,i,a)=>a.indexOf(v)===i).join(', ')||'Not established for this profile')}</p><p><strong>Score:</strong> ${r.score_min==null?'Not ranked':`${esc(r.score_min)}–${esc(r.score_max)}`}</p><p><strong>Setup / recovery:</strong> ${rating(r.setup)} / ${rating(r.recovery)} in the project rubric</p><p><strong>Evidence:</strong> ${esc(evidence.map(e=>e.claim).join(' ')||(r.prediction!=null?'TiO₂ model estimate is eligible for these inputs.':r.reason))}</p><p><strong>Limitations:</strong> ${esc(evidence.map(e=>e.limitations).join(' ')||r.reason)}</p><p><strong>ML estimate:</strong> ${r.prediction==null?'Not available':`${Number(r.prediction).toFixed(3)} mlogk`}</p><div class="detail-links">${sourceLinks(r)}</div></article>`;}).join(''):'<p class="compare-empty">Select materials above to compare their evidence and suitability.</p>';
}
function renderCatalogue(){
  const dimensions={particle_size:'particle size',sheet_thickness:'thickness',tube_diameter:'diameter',layer_thickness:'thickness'};
  $('catalogue-rows').innerHTML=state.meta.materials.map(m=>`<tr><td><span class="material-name">${esc(m.material_name)}</span><div class="profile-label">${esc(m.formula_or_family)}</div></td><td>${esc(m.seed_size_min_nm)}–${esc(m.seed_size_max_nm)} nm <span class="profile-label">${esc(dimensions[m.seed_dimension_type]||'size')}</span></td><td>${esc(m.seed_surface_area_min_m2_g)}–${esc(m.seed_surface_area_max_m2_g)} m²/g</td><td>${esc(m.seed_processes.replaceAll('_',' ').replaceAll(';','; '))}</td><td>${esc(state.meta.provided_impacts[m.material_id]||'Not provided')}</td></tr>`).join('');
}
function renderCoverage(){
  const coverage=state.meta.coverage;const materialCount=state.meta.material_count;
  $('coverage-total').textContent=`${coverage.covered_pairs} / ${coverage.total_pairs} pairs`;
  $('coverage-bars').innerHTML=state.meta.pollutants.map(p=>{const count=coverage.by_pollutant[p.pollutant_id]||0;return `<div><div class="coverage-label"><span>${esc(p.display_name)}</span><span>${count} / ${materialCount} materials</span></div><div class="coverage-track" role="img" aria-label="${esc(p.display_name)}: ${count} of ${materialCount} material families have literature records"><div class="coverage-fill" style="width:${100*count/materialCount}%"></div></div></div>`;}).join('');
  $('coverage-sources').textContent=`${coverage.observations} literature observations from ${coverage.studies} studies. These counts describe the catalogue, not independent validation or predicted performance.`;
}
function renderRows(){
  const {rows,summary}=state.result;document.querySelectorAll('[data-filter]').forEach(b=>b.classList.toggle('active',b.dataset.filter===state.filter));
  const visible=rows.filter(r=>state.filter==='all'||(state.filter==='shortlist'&&summary.top_candidates.includes(r.material_id))||(state.filter==='unknown'&&r.status==='insufficient_evidence'));
  $('material-rows').innerHTML=visible.length?visible.map(r=>{
    const score=r.score_min==null?'<span class="no-tier">—</span>':`<span class="score-number">${r.score_min===r.score_max?r.score_min:`${r.score_min}–${r.score_max}`}</span><div class="score-track"><i class="score-range" style="left:${r.score_min}%;width:${Math.max(1,r.score_max-r.score_min)}%"></i><i class="score-point" style="width:${r.score_min}%"></i></div>`;
    return `<tr><td>${r.preference_tier==null?'<span class="no-tier">—</span>':`<span class="tier-pill">${r.preference_tier}</span>`}</td><td><div class="material-name">${esc(r.material_name)}</div><div class="profile-label">${esc(r.profile_id??r.material_id)}</div></td><td><span class="status ${esc(r.status)}">${esc(labels[r.status])}</span></td><td>${score}</td><td class="prediction-cell">${r.prediction==null?'<span class="no-tier">—</span>':Number(r.prediction).toFixed(3)}</td><td><button class="view-button" data-detail="${esc(r.material_id)}" aria-expanded="false">View</button></td></tr><tr class="row-details" id="details-${esc(r.material_id)}" hidden><td colspan="6"><p class="detail-title">${esc(r.formulation??'No applicable formulation in the current database')}</p><p class="detail-reason">${esc(r.reason)}</p>${r.ml_fallback_reason?`<p class="detail-reason"><strong>ML:</strong> ${esc(r.ml_fallback_reason)}</p>`:''}<div class="detail-links">${sourceLinks(r)}</div></td></tr>`;
  }).join(''):'<tr><td colspan="6" class="empty-row">No materials in this view.</td></tr>';
}
function sourceLinks(row){return String(row.source_urls??'').split('; ').filter(Boolean).map((url,i)=>{try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))return '';return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">Research source ${i+1} ↗</a>`;}catch{return '';}}).join('');}
function exportCsv(){const cols=['material_id','material_name','profile_id','status','preference_tier','score_min','score_max','prediction','prediction_target','reason','source_urls'];const quote=v=>'"'+String(v??'').replaceAll('"','""')+'"';const content=[cols.join(','),...state.result.rows.map(r=>cols.map(k=>quote(r[k])).join(','))].join('\r\n');const url=URL.createObjectURL(new Blob(['\ufeff'+content],{type:'text/csv;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='nanoselect-results.csv';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
function exportReport(){
  const {rows,summary,evidence}=state.result;const scenario=summary.scenario;const weights=summary.weights;const coverage=state.meta.coverage;
  const inputs=[['Pollutant',scenario.pollutant_id||'Not specified'],['Concentration',scenario.concentration_mg_L==null?'Unknown':`${scenario.concentration_mg_L} mg/L`],['pH',scenario.pH??'Unknown'],['Material dose',scenario.dose_g_L==null?'Unknown':`${scenario.dose_g_L} g/L`],['Temperature',scenario.temperature_C==null?'Unknown':`${scenario.temperature_C} °C`],['Contact time',scenario.time_min==null?'Unknown':`${scenario.time_min} min`],['Light',scenario.light_type??'Unknown'],['UV intensity',scenario.light_intensity_mW_cm2==null?'Unknown':`${scenario.light_intensity_mW_cm2} mW/cm²`],['Water source',scenario.water_matrix??'Unknown'],['Equipment',(scenario.available_equipment||[]).join(', ')||'None selected'],['Requested endpoint',scenario.requested_endpoint??'Unknown'],['Removal target',scenario.required_removal_percent==null?'Not specified':`${scenario.required_removal_percent}%`],['Use TiO₂ prediction',scenario.include_ml?'Yes, when eligible':'No'],['Study formulations considered',scenario.consider_study_profiles?'Yes':'No'],['Conditional research candidates included',scenario.allow_conditional_ranking?'Yes':'No'],['Explicit profile choices',Object.entries(scenario.profile_choices||{}).map(([material,profile])=>`${material}: ${profile}`).join(', ')||'None']];
  const shortlist=summary.top_candidates.length?summary.top_candidates.map(id=>rows.find(r=>r.material_id===id)?.material_name||id).join(', '):'No justified ranking';
  const evidenceFor=row=>(evidence||[]).filter(item=>String(row.evidence_ids||'').split(';').includes(item.evidence_id));
  const evidenceHtml=row=>evidenceFor(row).map(item=>`<div class="observation"><strong>${esc(item.evidence_id)}:</strong> ${esc(item.claim)}<br><strong>Limitations:</strong> ${esc(item.limitations)}</div>`).join('');
  const doc=`<!doctype html><html lang="en"><head><meta charset="utf-8"><title>NanoSelect research report</title><style>body{font:14px/1.55 Arial,sans-serif;color:#17303d;max-width:950px;margin:40px auto;padding:0 25px}h1,h2{color:#126e76}h2{margin-top:32px}table{border-collapse:collapse;width:100%}th,td{border:1px solid #cbdcde;padding:9px;text-align:left;vertical-align:top}th{background:#edf6f4}a{color:#126e76}.note{background:#edf6f4;border-left:4px solid #126e76;padding:16px}.observation{border-top:1px solid #dce8e9;margin-top:8px;padding-top:8px}small{color:#58747b}p{margin:9px 0}@media print{body{margin:0}.no-print{display:none}tr,.note{break-inside:avoid}}</style></head><body><small>NANOSELECT · IDP RESEARCH PROTOTYPE</small><h1>Water treatment material screening</h1><p>Generated ${esc(new Date().toLocaleString())} from the last completed analysis. ${!$('result-stale').hidden?'The form has changed since that analysis; rerun it to report the new inputs.':''}</p><div class="note"><strong>Shortlist:</strong> ${esc(shortlist)}<br><strong>Result type:</strong> ${esc(summary.recommendation_type)}<br>${esc(summary.ranking_scope)}</div><h2>Water conditions and settings</h2><table>${inputs.map(([k,v])=>`<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join('')}</table><p><strong>Decision priorities:</strong> ${weightIds.map(k=>`${esc(k)} ${esc(Number((weights[k]*100).toFixed(4)))}%`).join(' · ')}. These are user preferences.</p><h2>Evidence coverage</h2><p>The catalogue has ${esc(coverage.observations)} observations from ${esc(coverage.studies)} studies, covering ${esc(coverage.covered_pairs)} of ${esc(coverage.total_pairs)} material–pollutant pairs for its three supported pollutants. Coverage is not a measure of treatment effectiveness or independent validation.</p><h2>Material assessments</h2><table><thead><tr><th>Material</th><th>Tier, status & score</th><th>Formulation, evidence and sources</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.material_name)} (${esc(r.material_id)})</td><td>${r.preference_tier==null?'Not ranked':`Tier ${esc(r.preference_tier)}`}<br>${esc(labels[r.status])}<br>${r.score_min==null?'No score':`Score ${esc(r.score_min)}–${esc(r.score_max)}`}<br>${r.prediction==null?'':`TiO₂ estimate: ${esc(Number(r.prediction).toFixed(3))} mlogk`}</td><td><strong>${esc(r.formulation||'No applicable formulation')}</strong><br>${esc(r.reason)}${evidenceHtml(r)}<div>${sourceLinks(r)}</div></td></tr>`).join('')}</tbody></table><h2>Assumptions and limits</h2><ul>${summary.assumptions.map(v=>`<li>${esc(v)}</li>`).join('')}<li>Decision scores are not removal percentages or probabilities. Overlapping ranges do not justify a unique winner.</li><li>The ML estimate is the dataset’s mlogk target; its logarithm base is unverified and the output is not a removal percentage.</li><li>Model evaluation is preliminary; study identifiers are missing. This is not independently validated treatment advice.</li></ul><p class="no-print">Use your browser’s Print command to save this report as a PDF.</p></body></html>`;
  const url=URL.createObjectURL(new Blob([doc],{type:'text/html;charset=utf-8'}));const link=document.createElement('a');link.href=url;link.download='nanoselect-report.html';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.querySelectorAll('.preset').forEach(b=>b.addEventListener('click',()=>{if(!$('run-button').disabled)setPreset(b.dataset.preset);}));
$('sample-form').addEventListener('submit',event=>{event.preventDefault();state.preset=null;document.querySelectorAll('.preset').forEach(b=>b.classList.remove('active'));run();});
$('sample-form').addEventListener('input',()=>{if(state.result)$('result-stale').hidden=false;});
$('sample-form').addEventListener('change',()=>{if(state.result)$('result-stale').hidden=false;});
['pollutant','light','use-target'].forEach(id=>$(id).addEventListener('change',updateVisibility));
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{if(state.result){state.filter=b.dataset.filter;renderRows();}}));
$('material-rows').addEventListener('click',event=>{const button=event.target.closest('[data-detail]');if(!button)return;const row=$('details-'+button.dataset.detail);row.hidden=!row.hidden;button.setAttribute('aria-expanded',String(!row.hidden));button.textContent=row.hidden?'View':'Close';});
weightIds.forEach(key=>$('weight-'+key).addEventListener('input',updateWeights));$('reset-weights').addEventListener('click',()=>{[60,25,15].forEach((value,i)=>$('weight-'+weightIds[i]).value=value);updateWeights();});
$('compare-choices').addEventListener('click',event=>{const button=event.target.closest('[data-compare]');if(!button)return;const id=button.dataset.compare;state.selected=state.selected.includes(id)?state.selected.filter(v=>v!==id):[...state.selected,id].slice(0,3);renderComparison();});
$('download-report').addEventListener('click',exportReport);
$('download').addEventListener('click',exportCsv);$('method-toggle').addEventListener('click',()=>$('method-dialog').showModal());$('close-method').addEventListener('click',()=>$('method-dialog').close());$('method-dialog').addEventListener('click',event=>{if(event.target===$('method-dialog'))$('method-dialog').close();});
(async()=>{try{const response=await fetch('/api/meta');if(!response.ok)throw new Error('Cannot load the local project.');state.meta=await response.json();renderCatalogue();renderCoverage();$('model-metrics').textContent=`${state.meta.model.name} was selected from three model types. Held-out MAE: ${state.meta.model.mae.toFixed(3)} in mlogk units; R²: ${state.meta.model.r2.toFixed(3)}. R² is not percentage accuracy. The split used 350 training and 90 test records.`;setPreset('demo_ml');}catch(error){$('loading').textContent=error.message;}})();

// Coalesce pointer updates so the highlight stays smooth without intercepting clicks.
(()=>{
  const enabled=matchMedia('(hover: hover) and (pointer: fine) and (prefers-reduced-motion: no-preference)');
  const ambient=document.createElement('div');ambient.className='cursor-ambient';ambient.setAttribute('aria-hidden','true');document.body.appendChild(ambient);
  const cursor=document.createElement('div');cursor.className='light-cursor';cursor.setAttribute('aria-hidden','true');cursor.appendChild(document.createElement('span'));document.body.appendChild(cursor);
  let frame=0,last=null;
  const clear=()=>{if(frame)cancelAnimationFrame(frame);frame=0;last=null;document.body.classList.remove('cursor-active','cursor-custom');ambient.classList.remove('visible');cursor.classList.remove('visible','over-control','pressed');};
  document.addEventListener('pointermove',event=>{
    if(!enabled.matches||event.pointerType==='touch')return;
    const target=event.target;
    last={x:event.clientX,y:event.clientY,native:!!target.closest('input,textarea,[contenteditable],dialog'),control:!!target.closest('button,a,summary,select,[role="button"]')};
    if(frame)return;
    frame=requestAnimationFrame(()=>{
      frame=0;if(!last||!enabled.matches)return;
      ambient.style.transform=`translate3d(${last.x}px,${last.y}px,0)`;ambient.classList.add('visible');
      document.body.classList.add('cursor-active');
      document.body.classList.toggle('cursor-custom',!last.native);cursor.classList.toggle('visible',!last.native);cursor.classList.toggle('over-control',last.control);cursor.style.transform=`translate3d(${last.x}px,${last.y}px,0)`;
    });
  },{passive:true});
  document.addEventListener('pointerdown',()=>cursor.classList.add('pressed'),{passive:true});document.addEventListener('pointerup',()=>cursor.classList.remove('pressed'),{passive:true});
  document.addEventListener('pointerleave',clear);window.addEventListener('blur',clear);enabled.addEventListener('change',()=>{if(!enabled.matches)clear();});
})();
