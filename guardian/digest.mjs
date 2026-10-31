import {readFile,writeFile} from "node:fs/promises";
const folder=new URL("./out/",import.meta.url);
const report=JSON.parse(await readFile(new URL("report.json",folder),"utf8"));
if(!report.verdict||!Array.isArray(report.sites))throw new Error("Guardian report schema incomplete");
const runId=process.env.GITHUB_RUN_ID||report.runId||"";
const runUrl=runId?"https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/"+runId:"";
const lines=["### Atlas Guardian · "+report.date.slice(0,10)+" · "+report.verdict,""];
for(const site of report.sites){
 lines.push("**"+site.id+"** — "+site.verdict);
 if(site.fatal){lines.push("Auditoría incompleta: "+String(site.fatal).slice(0,140));continue;}
 const c=site.coverage||{},page=c.pages||{},images=c.images||{};
 const b=site.browser||{};
 lines.push("Comprobado: "+(page.ok||0)+"/"+(page.expected||0)+" páginas; "+(images.ok||0)+"/"+(images.expected||0)+" imágenes; "+(b.checks||[]).filter(x=>x.status==="PASS").length+"/"+(b.expected||0)+" recorridos Chromium.");
 const brokenExternal=(site.incidents?.links||[]).filter(x=>x.state==="ROTO"&&new URL(x.url).origin!==new URL(site.url).origin);
 const blockedExternal=site.externalLinks?.blocked||0;
 const changes=[];
 for(const item of brokenExternal.slice(0,2))changes.push("Corregir o reemplazar enlace externo que devuelve "+(item.http||"error")+": "+item.url);
 if(images.broken)changes.push("Revisar "+images.broken+" imágenes con fallos de carga.");
 if(images.blocked)changes.push("Revalidar "+images.blocked+" imágenes que no pudieron comprobarse.");
 const candidates=site.editorial?.candidates?.length||0;
 if(candidates)changes.push("Filtrar "+candidates+" titulares candidatos y decidir si justifican actualización editorial (sin incorporar automáticamente).");
 if(blockedExternal)changes.push("Reintentar "+blockedExternal+" enlaces externos inconclusos; no contarlos como rotos.");
 if(!changes.length)changes.push("Sin acciones correctivas detectadas.");
 lines.push("**Acciones:**");
 changes.slice(0,4).forEach((x,i)=>lines.push((i+1)+". "+x));
 lines.push("");
}
lines.push("Sin ediciones ni despliegues automáticos.");
if(runUrl)lines.push("[Ver informe completo y evidencia de la ejecución]("+runUrl+")");
await writeFile(new URL("digest.md",folder),lines.join("\n")+"\n");
console.log("GUARDIAN_DIGEST_CREATED "+report.verdict);
