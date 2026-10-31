import {readFile,mkdir,writeFile,appendFile} from "node:fs/promises";
import {url,sitemap,htmlResources,jsImages,jsonImages,verdict,reconcile,coverage} from "./lib.mjs";
const cfg=JSON.parse(await readFile(new URL("./config.json",import.meta.url),"utf8"));
const root=new URL("./out/",import.meta.url);
const started=new Date().toISOString();
const limit={pages:1800,links:2200,images:1200,content:2400000};
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
async function fetchRetry(uri){
 for(let n=0;n<3;n++){
  const c=new AbortController();const t=setTimeout(()=>c.abort(),15000);
  try{
   const r=await fetch(uri,{signal:c.signal,redirect:"follow",headers:{"User-Agent":"AtlasGuardian/1.0 (readonly; monthly)"},cache:"no-store"});clearTimeout(t);
   if([429,502,503,504].includes(r.status)&&n<2){await r.body?.cancel();await sleep(450*(n+1));continue;}
   return r;
  }catch(e){clearTimeout(t);if(n===2)throw e;await sleep(400*(n+1));}
 }
}
async function getText(uri){
 const r=await fetchRetry(uri);
 if(!r.ok)throw Error("HTTP "+r.status+" "+uri);
 const size=Number(r.headers.get("content-length")||0);
 if(size>limit.content){await r.body?.cancel();throw Error("contenido excede tamaño seguro "+uri);}
 const txt=await r.text();if(txt.length>limit.content)throw Error("contenido demasiado extenso "+uri);return txt;
}
async function pool(xs,fn){
 let i=0;const out=Array(xs.length);
 await Promise.all(Array.from({length:Math.min(9,xs.length)},async()=>{while(i<xs.length){const j=i++;try{out[j]=await fn(xs[j]);}catch(e){out[j]={url:xs[j],state:"BLOQUEADO",detail:String(e.message||e)};}}}));
 return out;
}
async function check(uri,kind){
 const r=await fetchRetry(uri);
 let bytes=Buffer.alloc(0);
 if(kind==="image" && r.body){
  const reader=r.body.getReader();
  const first=await reader.read();
  bytes=first.value?Buffer.from(first.value).subarray(0,512):bytes;
  await reader.cancel();
 }else await r.body?.cancel();
 return {url:uri,state:verdict(r.status,kind,r.headers.get("content-type")||"",bytes),http:r.status};
}
function baseline(lines){return lines.split(/\r?\n/).map(x=>x.trim()).filter(x=>/^https?:\/\//.test(x));}
async function editorial(site,notes){
 const sources={},candidates=[];const since=Date.now()-40*86400000;
 if(site.musicbrainzArtistId){
  try{
   const xml=await getText("https://musicbrainz.org/ws/2/release-group/?artist="+encodeURIComponent(site.musicbrainzArtistId)+"&limit=100&fmt=json");
   const data=JSON.parse(xml);sources.musicbrainz={state:"REVISADA",count:data["release-group-count"]||0};
   for(const a of data["release-groups"]||[]){
    const when=a["first-release-date"],type=a["primary-type"];
    if(!/^\d{4}-\d\d-\d\d$/.test(when||"")||!["Album","EP","Single"].includes(type))continue;
    const ms=Date.parse(when+"T00:00:00Z");
    if(ms>=since&&ms<=Date.now())candidates.push({type:"lanzamiento-posible",title:a.title,date:when,url:"https://musicbrainz.org/release-group/"+a.id,source:"MusicBrainz"});
   }
   if(sources.musicbrainz.count>100){sources.musicbrainz.state="PARCIAL";notes.push("MusicBrainz paginación necesaria");}
  }catch(e){sources.musicbrainz={state:"BLOQUEADA",detail:String(e.message||e)};}
 }
 if(site.newsQuery){
  try{
   const feed=await getText("https://news.google.com/rss/search?q="+encodeURIComponent('"'+site.newsQuery+'" when:40d')+"&hl=es-419&gl=AR&ceid=AR:es-419");
   let count=0;for(const m of feed.matchAll(/<item>([\s\S]*?)<\/item>/gi)){
    count++;const body=m[1];
    const title=(body.match(/<title>([\s\S]*?)<\/title>/i)||[])[1]||"";
    const link=(body.match(/<link>([^<]+)<\/link>/i)||[])[1]||"";
    const pub=(body.match(/<pubDate>([^<]+)<\/pubDate>/i)||[])[1]||"";
    if(/disco|álbum|album|lanz|estren|entrevista|separ|disol|integrante|fallec|gira|libro|canci[oó]n|regres/i.test(title)&&Date.parse(pub)>=since){
     candidates.push({type:"titular-por-verificar",title:title.replace(/<!\[CDATA\[|\]\]>/g,"").replace(/&amp;/g,"&"),date:new Date(pub).toISOString().slice(0,10),url:link.replace(/&amp;/g,"&"),source:"Google News RSS"});
    }
   }
   sources.news={state:"REVISADA",count};
  }catch(e){sources.news={state:"BLOQUEADA",detail:String(e.message||e)};}
 }
 return {sources,candidates:candidates.slice(0,40),note:"Señales de fuentes declaradas; no equivale a leer toda la prensa ni prueba ausencia absoluta de novedades"};
}
async function audit(site,browser){
 const notes=[],origin=new URL(site.url).origin;
 const expected=baseline(await readFile(site.baseline,"utf8"));
 const expectedImages=baseline(await readFile(site.baseline.replace(".urls.txt",".images.txt"),"utf8"));
 if(!expected.length||!expectedImages.length)throw Error("baseline faltante");
 let actual=[];
 try{actual=sitemap(await getText(new URL("/sitemap.xml",origin).href),origin);}catch(e){notes.push("Sitemap inaccesible: "+String(e));}
 const delta=reconcile(expected,actual);
 if(delta.duplicates)notes.push("URL duplicadas en sitemap: "+delta.duplicates);
 if(delta.missing.length)notes.push("Desaparecieron "+delta.missing.length+" URL canónicas");
 if(delta.added.length)notes.push("Nuevas URL sin baseline aprobado: "+delta.added.length);
 if(actual.length>limit.pages)notes.push("Sitemap excede límite técnico de "+limit.pages);
 const pages=[...new Set([...expected,...actual])].slice(0,limit.pages);
 const imgs=new Set(),links=new Set(),scripts=new Set(),linkSources=new Map();
 const htmlChecks=await pool(pages,async uri=>{
  const r=await fetchRetry(uri),type=r.headers.get("content-type")||"";
  const state=verdict(r.status,"html",type);
  if(state!=="OK"){await r.body?.cancel();return {url:uri,state,http:r.status};}
  const body=await r.text();if(body.length>limit.content)return {url:uri,state:"BLOQUEADO",detail:"HTML demasiado grande"};
  const found=htmlResources(body,uri);
  found.images.forEach(x=>imgs.add(x));found.links.forEach(x=>{links.add(x);if(!linkSources.has(x))linkSources.set(x,[]);if(linkSources.get(x).length<4)linkSources.get(x).push(uri);});found.scripts.forEach(x=>scripts.add(x));
  return {url:uri,state:"OK",http:r.status};
 });
 for(const name of site.assetPaths||[]){
  const src=new URL(name,origin).href;
  try{jsImages(await getText(src),src).forEach(x=>imgs.add(x));}catch(e){notes.push("Asset no inspeccionable "+src+": "+String(e.message||e));}
 }
 for(const name of site.imageJsonPaths||[]){
  const src=new URL(name,origin).href;
  try{jsonImages(JSON.parse(await getText(src)),src,/covers\.json(?:$|\?)/.test(name)).forEach(x=>imgs.add(x));}
  catch(e){notes.push("JSON de medios no inspeccionable "+src+": "+String(e.message||e));}
 }
 const imageList=[...new Set([...expectedImages,...imgs])],linkList=[...links].filter(x=>!pages.includes(x));
 if(imageList.length>limit.images)notes.push("Recorte de imágenes, total "+imageList.length+" > "+limit.images);
 if(linkList.length>limit.links)notes.push("Recorte de enlaces, total "+linkList.length+" > "+limit.links);
 const imageChecks=await pool(imageList.slice(0,limit.images),u=>check(u,"image"));
 const linkChecks=await pool(linkList.slice(0,limit.links),u=>check(u,"link"));
 for(const item of linkChecks)item.foundAt=linkSources.get(item.url)||[];
 const imagesCoverage=coverage(imageList,imageChecks),linksCoverage=coverage(linkList,linkChecks),pagesCoverage=coverage(pages,htmlChecks);
 const foundBaselineImages=expectedImages.filter(u=>imgs.has(u)).length;
 if(foundBaselineImages!==expectedImages.length)notes.push('Imagen base no hallada en recursos de la versión actual: '+(expectedImages.length-foundBaselineImages));
 if(imageList.length<(site.expectedImagesAtLeast||1))notes.push("Menos imágenes de las esperadas");
 const editorialResult=await editorial(site,notes);
 const requiredBrowser=(site.browserRoutes||[]).length*2;
 const browserResult=browser?.sites?.[site.id];
 const browserChecks=browserResult?.checks||[];
 if(browserChecks.length!==requiredBrowser)notes.push("Chromium incompleto: "+browserChecks.length+"/"+requiredBrowser+" recorridos");
 let state="VERDE";
 if(notes.length||pagesCoverage.unverified.length||imagesCoverage.unverified.length||linksCoverage.unverified.length||imageChecks.some(x=>x.state==="BLOQUEADO")||linkChecks.some(x=>x.state==="BLOQUEADO")||htmlChecks.some(x=>x.state==="BLOQUEADO")||browserChecks.some(x=>x.status!=="PASS")||Object.values(editorialResult.sources).some(x=>x.state!=="REVISADA"))state="GRIS";
 if(htmlChecks.some(x=>x.state==="ROTO")||imageChecks.some(x=>x.state==="ROTO")||linkChecks.some(x=>x.state==="ROTO"&&new URL(x.url).origin===origin)||delta.missing.length)state="ROJO";
 else if(state==="VERDE"&&(delta.added.length||editorialResult.candidates.length||linkChecks.some(x=>x.state==="ROTO")))state="AMARILLO";
 return {id:site.id,url:origin,verdict:state,inventory:{urls:delta,imagesExpected:expectedImages.length,imagesDiscovered:imgs.size,imagesBaselinePresent:foundBaselineImages,linksDiscovered:links.size},coverage:{pages:pagesCoverage,images:imagesCoverage,links:linksCoverage},browser:browserResult||null,editorial:editorialResult,notes,checks:{pages:htmlChecks,images:imageChecks,links:linkChecks},incidents:{pages:htmlChecks.filter(x=>x.state!=="OK").slice(0,80),images:imageChecks.filter(x=>x.state!=="OK").slice(0,120),links:linkChecks.filter(x=>x.state!=="OK").slice(0,100)}};
}
await mkdir(root,{recursive:true});
let browser=null;try{browser=JSON.parse(await readFile(new URL("browser.json",root),"utf8"));}catch{}
const report={schema:2,date:started,runId:process.env.GITHUB_RUN_ID||null,automation:"READ_ONLY",sites:[]};
for(const site of cfg.sites.filter(x=>x.enabled)){
 try{report.sites.push(await audit(site,browser));}catch(e){report.sites.push({id:site.id,verdict:"GRIS",fatal:String(e.stack||e)});}
}
report.verdict=report.sites.some(s=>s.verdict==="ROJO")?"ROJO":report.sites.some(s=>s.verdict==="GRIS")?"GRIS":report.sites.some(s=>s.verdict==="AMARILLO")?"AMARILLO":"VERDE";
const lines=["# Atlas Guardian — "+started.slice(0,10),"","Resultado: **"+report.verdict+"**","Ejecución: "+(report.runId||"manual"),"Sin reparación ni publicación automática.",""];
for(const a of report.sites){
 lines.push("## "+a.id+" — "+a.verdict);
 if(a.fatal){lines.push("- No se pudo auditar: "+a.fatal);continue;}
 lines.push("- URLs base "+a.inventory.urls.expected+" / observadas "+a.inventory.urls.observed+"; faltan "+a.inventory.urls.missing.length+"; nuevas "+a.inventory.urls.added.length);
 for(const [k,v] of Object.entries(a.coverage))lines.push("- "+k+": "+v.expected+" esperados, "+v.checked+" revisados, "+v.ok+" OK, "+v.broken+" rotos, "+v.blocked+" bloqueados, "+v.unverified.length+" no vistos");
 lines.push("- Tapas base "+a.inventory.imagesExpected+" / presentes "+a.inventory.imagesBaselinePresent+"; imágenes totales "+a.inventory.imagesDiscovered);
 lines.push("- Chromium "+(a.browser?.checks||[]).filter(x=>x.status==="PASS").length+"/"+(a.browser?.checks||[]).length+" recorridos, esperados "+a.browser?.expected);
 for(const [source,v] of Object.entries(a.editorial.sources))lines.push("- Fuente editorial "+source+": "+v.state+" ("+(v.count??"sin datos")+")");
 lines.push("- Candidatos editoriales: "+a.editorial.candidates.length+" (NO verificados para publicación)");
 for(const c of a.editorial.candidates.slice(0,8))lines.push("  - "+c.date+" "+c.title+" "+c.url);
 for(const n of a.notes.slice(0,20))lines.push("- Atención: "+n);
 for(const [k,items] of Object.entries(a.incidents))for(const x of items.slice(0,12))lines.push("- "+k+" "+x.state+": "+x.url+(x.http?" HTTP "+x.http:"")+(x.foundAt?.length?" [origen: "+x.foundAt.slice(0,2).join(", ")+"]":""));
}
lines.push("","Evidencia completa: artifact guardian-report en la ejecución GitHub. Grises o bloques NO equivalen a OK.","Correcciones: ninguna aplicada. Altas de otros Atlas: sumar configuración y baselines nuevos; mismo motor.");
await writeFile(new URL("report.json",root),JSON.stringify(report,null,2)+"\n");
await writeFile(new URL("report.md",root),lines.join("\n")+"\n");
if(process.env.GITHUB_STEP_SUMMARY)await appendFile(process.env.GITHUB_STEP_SUMMARY,lines.join("\n")+"\n");
console.log("GUARDIAN_RESULT "+report.verdict+" "+report.sites.map(x=>x.id+":"+x.verdict).join(" "));
if(report.verdict==="GRIS"||report.verdict==="ROJO")process.exitCode=1;
