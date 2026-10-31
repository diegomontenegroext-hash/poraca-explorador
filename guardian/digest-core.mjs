import {cycleMarker} from "./monthly.mjs";
export function buildDigest(report,{runId="",eventName=""}={}){
 if(!report||!Array.isArray(report.sites)||!report.date||!report.verdict)throw Error("invalid report schema");
 const lines=["### Atlas Guardian · "+report.date.slice(0,10)+" · "+report.verdict,""];
 for(const site of report.sites){
  lines.push("**"+site.id+"** — "+site.verdict);
  if(site.fatal){lines.push("Auditoría incompleta: "+String(site.fatal).slice(0,140));continue;}
  const c=site.coverage||{},pages=c.pages||{},images=c.images||{},b=site.browser||{};
  lines.push("Comprobado: "+(pages.ok||0)+"/"+(pages.expected||0)+" páginas; "+(images.ok||0)+"/"+(images.expected||0)+" imágenes; "+(b.checks||[]).filter(x=>x.status==="PASS").length+"/"+(b.expected||0)+" recorridos Chromium.");
  const changes=[],news=site.editorial?.candidates||[];
  const urgent=news.filter(x=>x.signal?.level==="URGENTE_VERIFICAR");
  if(urgent.length)changes.push("SEÑAL URGENTE A VERIFICAR: "+urgent.slice(0,2).map(x=>x.title).join("; ")+". Confirmar oficialmente; el titular no prueba el hecho.");
  if(images.broken){const urls=(site.incidents?.images||[]).filter(x=>x.state==="ROTO").slice(0,3).map(x=>x.url);changes.push("Revisar "+images.broken+" fotografías rotas"+(urls.length?": "+urls.join(", "):"")+".");}
  if(images.blocked)changes.push("Reintentar "+images.blocked+" imágenes no verificables (sin afirmar que estén rotas).");
  const links=(site.incidents?.links||[]).filter(x=>x.state==="ROTO"&&new URL(x.url).origin!==new URL(site.url).origin);
  for(const l of links.slice(0,2))changes.push("Corregir enlace externo "+(l.http||"error")+": "+l.url);
  if(news.length)changes.push("Evaluar "+news.length+" novedades candidatas para el Atlas; no están confirmadas ni incorporadas.");
  if(site.externalLinks?.blocked)changes.push("Revisar "+site.externalLinks.blocked+" enlaces externos bloqueados; no clasificarlos como rotos.");
  if(!changes.length)changes.push("Sin acciones correctivas identificadas en el alcance comprobado.");
  lines.push("**Acciones:**");
  changes.slice(0,4).forEach((x,i)=>lines.push((i+1)+". "+x));
  lines.push("");
 }
 lines.push("Sin ediciones ni despliegues automáticos.");
 if(runId)lines.push("[Evidencia detallada](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/"+runId+")");
 if(eventName==="schedule")lines.unshift(cycleMarker(report.date.slice(0,7)));
 return lines.join("\n")+"\n";
}
