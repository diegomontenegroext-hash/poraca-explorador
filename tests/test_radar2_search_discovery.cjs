const assert=require('node:assert/strict');
const {discoverCulturalWeb}=require('../radar2/search_discovery.js');
(async()=>{
 const queries=[{id:'synthetic-ig',q:'synthetic',domains:['instagram.com']},{id:'synthetic-error',q:'fail'},{id:'synthetic-web',q:'web'}];
 const tool={mcp__codex_apps__search_service_web_run:async args=>{
   const q=(args.system2_search_query||args.system1_search_query)[0].q;
   if(q==='fail')throw new Error('synthetic failure');
   return {content:[{type:'text',text:q==='synthetic'?'Synthetic art (https://www.instagram.com/p/SYNTHETIC/)\n【synthetic-ref】 Excerpt for test only.':'Synthetic web (https://example.org/event)\n【synthetic-web】 Test only.'}]};
 }};
 const out=await discoverCulturalWeb(tool,{queries});
 assert.equal(out.searches.length,3);assert.equal(out.searches.filter(x=>x.error).length,1);
 assert.equal(out.documents.find(x=>x.url.includes('instagram')).acquisition_method,'public_search_index');
 assert.equal(out.documents.length,2);assert.equal(queries.length,3);
 console.log('PASS: indexed result retained; individual error isolated; web result retained; input unchanged');
})().catch(e=>{console.error(e);process.exit(1)});
