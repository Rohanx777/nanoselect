'use strict';
const $=id=>document.getElementById(id);
const state={meta:null,result:null,filter:'all',preset:'demo_ml'};
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
async function run(){
  const button=$('run-button');button.disabled=true;button.querySelector('span').textContent='Analysing…';$('form-error').hidden=true;
  try{
    const response=await fetch('/api/recommend',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({scenario:readScenario()})});
    const data=await response.json();if(!response.ok)throw new Error(data.error??'Analysis could not complete.');state.result=data;state.filter='all';render();
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
  $('shortlist-count').textContent=tops.length;$('gap-count').textContent=gaps;renderRows();
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
document.querySelectorAll('.preset').forEach(b=>b.addEventListener('click',()=>{if(!$('run-button').disabled)setPreset(b.dataset.preset);}));
$('sample-form').addEventListener('submit',event=>{event.preventDefault();state.preset=null;document.querySelectorAll('.preset').forEach(b=>b.classList.remove('active'));run();});
['pollutant','light','use-target'].forEach(id=>$(id).addEventListener('change',updateVisibility));
document.querySelectorAll('[data-filter]').forEach(b=>b.addEventListener('click',()=>{if(state.result){state.filter=b.dataset.filter;renderRows();}}));
$('material-rows').addEventListener('click',event=>{const button=event.target.closest('[data-detail]');if(!button)return;const row=$('details-'+button.dataset.detail);row.hidden=!row.hidden;button.setAttribute('aria-expanded',String(!row.hidden));button.textContent=row.hidden?'View':'Close';});
$('download').addEventListener('click',exportCsv);$('method-toggle').addEventListener('click',()=>$('method-dialog').showModal());$('close-method').addEventListener('click',()=>$('method-dialog').close());$('method-dialog').addEventListener('click',event=>{if(event.target===$('method-dialog'))$('method-dialog').close();});
(async()=>{try{const response=await fetch('/api/meta');if(!response.ok)throw new Error('Cannot load the local project.');state.meta=await response.json();$('model-metrics').textContent=`${state.meta.model.name} was selected from three model types. Held-out MAE: ${state.meta.model.mae.toFixed(3)} in mlogk units; R²: ${state.meta.model.r2.toFixed(3)}. R² is not percentage accuracy. The split used 350 training and 90 test records.`;setPreset('demo_ml');}catch(error){$('loading').textContent=error.message;}})();
