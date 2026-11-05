/* Run in the existing ChatGPT Radar executor, which supplies authenticated tools.
 * No search account, paid API or automation is created. This function is the
 * repeatable acquisition step; its output feeds collector.py --discovery.
 */
async function discoverCulturalWeb(tools, options = {}) {
  const stamp = new Intl.DateTimeFormat('es-AR', {timeZone:'America/Argentina/Buenos_Aires', month:'long', year:'numeric'}).format(new Date());
  const exclusions = '-site:instagram.com -site:imginn.com -site:pikory.com -site:pixnoy.com -site:pixwox.com -site:facebook.com';
  const queries = options.queries || [
    {id:'open-art', q:`"La Plata" ${stamp} inauguración exposición galería residencia ${exclusions}`},
    {id:'open-wine', q:`"La Plata" ${stamp} cata vinos degustación feria ${exclusions}`},
    {id:'open-theatre', q:`"La Plata" ${stamp} teatro independiente programación funciones ${exclusions}`},
    {id:'open-music', q:`"La Plata" ${stamp} recital festival ciclo talleres especiales ${exclusions}`},
    {id:'network-circus', accounts:['circus_ofc'], q:`"Circus" "La Plata" ${stamp} entradas ${exclusions}`},
    {id:'network-intra', accounts:['intra.prod'], q:`"INTRA" "La Plata" ${stamp} entradas ${exclusions}`},
    {id:'network-999', accounts:['999ciclo'], q:`"999ciclo" ${stamp} "La Plata" ${exclusions}`},
    {id:'network-guajira',accounts:['guajira.bar'],q:`"Guajira" "La Plata" ${stamp} entradas ${exclusions}`},
    {id:'network-sunset',accounts:['sunsetwine.mixology'],q:`"Sunset Wine Mixology" ${stamp} La Plata ${exclusions}`},
    {id:'network-dionisio',accounts:['dionisio_vinoteca'],q:`"Casa Dionisio" ${stamp} cata vinos La Plata ${exclusions}`},
    {id:'network-escenario',accounts:['escenario40'],q:`"Escenario 40" "La Plata" ${stamp} teatro ${exclusions}`},
    {id:'network-corazon',accounts:['residenciacorazon'],q:`"Residencia Corazón" ${stamp} ${exclusions}`},
    {id:'network-centroarte',accounts:['centrodearteunlp'],q:`"Centro de Arte UNLP" ${stamp} exposición talleres ${exclusions}`},
    {id:'network-luti', accounts:['lutitravelguide'], q:`"lutitravelguide" ${stamp} planes eventos ${exclusions}`}
  ];
  const blocked = /(^|\.)(instagram\.com|facebook\.com|imginn\.com|pikory\.com|pixnoy\.com|pixwox\.com)$/;
  const searches=[]; const documents=new Map();
  // Small batches; preserve every response, including failures and exclusions.
  for(let i=0;i<queries.length;i+=3){
    const batch=await Promise.all(queries.slice(i,i+3).map(async query=>{
      const at=new Date().toISOString();
      const cached=options.captured_searches?.find(x=>x.query.id===query.id);
      if(cached)return cached;
      const result=await tools.mcp__codex_apps__search_service_web_run({system2_search_query:[{q:query.q}],response_length:'long'});
      const raw=(result.content||[]).filter(x=>x.type==='text').map(x=>x.text).join('\n');
      return {query,at,raw,error:Boolean(result.isError)};
    }));
    for(const search of batch){
      searches.push(search);
      const pattern=/^([^\n]+?) \((https:\/\/[^\s)]+)\)\s*\n(?:【([^】]+)】)?/gm;
      let match;
      while((match=pattern.exec(search.raw))!==null){
        const host=match[2].match(/^https:\/\/([^/?#]+)/)?.[1]?.toLowerCase();
        if(!host||host.includes('@')||blocked.test(host)||/\.(pdf|jpg|png|zip)(\?|$)/i.test(match[2]))continue;
        const key=match[2];
        const origin={query_id:search.query.id,query:search.query.q,searched_at:search.at,ref:match[3]||null,accounts:search.query.accounts||[]};
        if(documents.has(key)){documents.get(key).searches.push(origin);continue}
        documents.set(key,{url:key,title:match[1],searches:[origin]});
      }
    }
  }
  return {schema:'radar2-public-search-v1',acquired_at:new Date().toISOString(),searches,documents:[...documents.values()]};
}
