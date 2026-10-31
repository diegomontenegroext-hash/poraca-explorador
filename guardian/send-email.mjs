import {readFile} from "node:fs/promises";
const key=process.env.GUARDIAN_RESEND_API_KEY;
const from=process.env.GUARDIAN_MAIL_FROM;
const to=process.env.GUARDIAN_MAIL_TO;
if (!key || !from || !to) {
  console.error("MAIL_NOT_CONFIGURED: requiere GUARDIAN_RESEND_API_KEY, GUARDIAN_MAIL_FROM y GUARDIAN_MAIL_TO. No se envió correo.");
  process.exit(2);
}
const report=JSON.parse(await readFile(new URL("./out/report.json",import.meta.url),"utf8"));
const md=await readFile(new URL("./out/report.md",import.meta.url),"utf8");
const run=process.env.GITHUB_RUN_ID;
const runUrl=run?"https://github.com/"+process.env.GITHUB_REPOSITORY+"/actions/runs/"+run:"";
const subject="[Atlas Guardian] "+report.status+" · "+report.generatedAt.slice(0,7);
const response=await fetch("https://api.resend.com/emails",{
  method:"POST",
  headers:{"Authorization":"Bearer "+key,"Content-Type":"application/json",...(run?{"Idempotency-Key":"atlas-guardian-"+run}:{})},
  body:JSON.stringify({from,to:[to],subject,text:md+(runUrl?"\nEjecución: "+runUrl+"\n":"")})
});
if(!response.ok) {console.error("MAIL_FAILED HTTP "+response.status+": "+(await response.text()).slice(0,400));process.exit(1);}
const result=await response.json();
console.log("MAIL_ACCEPTED: "+result.id+" (no confirma entrega final).");
