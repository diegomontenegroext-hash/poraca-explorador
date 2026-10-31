import {readFile} from "node:fs/promises";
const key=process.env.GUARDIAN_RESEND_API_KEY;
const from=process.env.GUARDIAN_MAIL_FROM;
const to=process.env.GUARDIAN_MAIL_TO;
if(!key||!from||!to){console.error("MAIL_NOT_CONFIGURED: secrets y dominio autorizado pendientes");process.exit(2);}
const report=JSON.parse(await readFile(new URL("./out/report.json",import.meta.url),"utf8"));
if(!report.verdict||!report.date||!Array.isArray(report.sites))throw Error("INVALID_REPORT");
const run=process.env.GITHUB_RUN_ID||"";
const issue="https://github.com/diegomontenegroext-hash/poraca-explorador/issues/4";
const lines=["ATLAS GUARDIAN | Informe mensual","Estado general: "+report.verdict,""];
for(const s of report.sites){
 lines.push(s.id.toUpperCase()+": "+s.verdict);
 if(s.fatal){lines.push("Revision incompleta: "+String(s.fatal).slice(0,130));continue;}
 const a=s.coverage||{};
 lines.push("Paginas "+(a.pages?.ok??0)+"/"+(a.pages?.expected??0)+", imagenes "+(a.images?.ok??0)+"/"+(a.images?.expected??0)+", Chromium "+(s.browser?.checks||[]).filter(x=>x.status==="PASS").length+"/"+(s.browser?.expected??0)+".");
 lines.push("Enlaces externos: "+(s.externalLinks?.broken??0)+" rotos y "+(s.externalLinks?.blocked??0)+" sin confirmar.");
 lines.push("Noticias candidatas: "+(s.editorial?.candidates?.length??0)+" (sin revision editorial).");
 if((s.externalLinks?.broken??0)>0)lines.push("ACCION: revisar enlaces de terceros que devuelven 404.");
 if((s.editorial?.candidates?.length??0)>0)lines.push("ACCION: filtrar novedades y decidir si corresponde una actualizacion editorial.");
 if((a.images?.broken??0)>0)lines.push("ACCION: revisar recursos de imagen rotos.");
 if((a.images?.blocked??0)>0)lines.push("PENDIENTE: repetir prueba de imagenes bloqueadas.");
 lines.push("");
}
lines.push("No se publico ni modifico ningun Atlas.","Informe y evidencia: "+issue);
if(run)lines.push("Ejecucion: https://github.com/"+process.env.GITHUB_REPOSITORY+"/actions/runs/"+run);
const response=await fetch("https://api.resend.com/emails",{method:"POST",headers:{"Authorization":"Bearer "+key,"Content-Type":"application/json",...(run?{"Idempotency-Key":"atlas-guardian-"+run}:{})},body:JSON.stringify({from,to:[to],subject:"[Atlas Guardian] "+report.verdict+" · "+report.date.slice(0,7),text:lines.join("\n")+"\n"})});
if(!response.ok){console.error("MAIL_FAILED HTTP "+response.status);process.exit(1);}
const result=await response.json();
console.log("MAIL_ACCEPTED "+result.id+"; entrega final pendiente de confirmacion");
