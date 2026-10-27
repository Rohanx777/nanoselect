// Exercise the actual report generator without a browser download or network.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../web/app.js'), 'utf8');
const cutoff = source.indexOf("\ndocument.querySelectorAll('.preset')");
assert.ok(cutoff > 0, 'Could not locate report generator');
let createdBlob, downloadName;
class ReportURL extends URL {
  static createObjectURL(blob) { createdBlob = blob; return 'blob:report'; }
  static revokeObjectURL() {}
}
const context = vm.createContext({
  URL: ReportURL, Blob, Date, Number, String, Object, Math,
  setTimeout() {},
  document: {
    getElementById(id) { assert.equal(id, 'result-stale'); return {hidden: false}; },
    createElement(tag) { assert.equal(tag, 'a'); return {click(){downloadName=this.download;}}; }
  }
});
vm.runInContext(source.slice(0, cutoff), context);
context.fixture={
  rows:[{material_id:'M05',material_name:'Iron <script>alert(1)</script>',status:'conditional',
         preference_tier:1,score_min:30,score_max:70,formulation:'Profile A',reason:'Conditions unknown',
         evidence_ids:'E019',source_urls:'https://example.org/source',prediction:null}],
  evidence:[{evidence_id:'E019',claim:'Reported range, not a guarantee.',limitations:'Operating time unknown.'}],
  summary:{scenario:{pollutant_id:'sulfamethoxazole',pH:5,concentration_mg_L:30,dose_g_L:0.14,
             water_matrix:'laboratory_solution',available_equipment:['mixer'],requested_endpoint:'removal_percent',
             required_removal_percent:90,include_ml:false,consider_study_profiles:true,
             allow_conditional_ranking:true,profile_choices:{M05:'P14'}},
           weights:{suitability:.3333,setup:.3333,recovery:.3334},top_candidates:['M05'],
           recommendation_type:'unique conditional policy candidate',ranking_scope:'Scope of analysis.',
           assumptions:['No guaranteed performance.']}
};
context.catalogue={coverage:{observations:19,studies:14,covered_pairs:13,total_pairs:45}};
vm.runInContext('state.result=fixture; state.meta=catalogue; exportReport();',context);
(async()=>{
  const html=await createdBlob.text();
  assert.equal(downloadName,'nanoselect-report.html');
  for(const text of ['13 of 45','19 observations from 14 studies','33.33%','33.34%',
      '90%','M05: P14','Reported range, not a guarantee.','Operating time unknown.',
      'The form has changed since that analysis','https://example.org/source']) assert.ok(html.includes(text),text);
  assert.ok(html.includes('&lt;script&gt;alert(1)&lt;/script&gt;'));
  assert.ok(!html.includes('<script>alert(1)</script>'));
  console.log('Report export content and escaping passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
