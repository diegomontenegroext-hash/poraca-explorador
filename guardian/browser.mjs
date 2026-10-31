import {chromium} from "playwright";
import {readFile,mkdir,writeFile} from "node:fs/promises";
const cfg=JSON.parse(await readFile(new URL("./config.json",import.meta.url),"utf8"));
const out=new URL("./out/",import.meta.url);await mkdir(out,{recursive:true});
const report={date:new Date().toISOString(),sites:{}};
let browser;
try{
 browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
 for(const site of cfg.sites.filter(s=>s.enabled)){
  const checks=[];
  for(const vp of [{label:"mobile",width:390,height:844},{label:"desktop",width:1440,height:900}]){
   const context=await browser.newContext({viewport:{width:vp.width,height:vp.height}});
   for(const path of site.browserRoutes||[]){
    const uri=new URL(path,site.url).href,problems=[];
    const page=await context.newPage();
    page.on("pageerror",e=>problems.push("JavaScript: "+String(e.message).slice(0,200)));
    page.on("response",r=>{if(r.url().startsWith(new URL(site.url).origin)&&r.status()>=400)problems.push("HTTP "+r.status()+" "+r.url());});
    try{
     const response=await page.goto(uri,{waitUntil:"domcontentloaded",timeout:28000});
     await page.waitForTimeout(550);
     await page.evaluate(async()=>{for(let n=0;n<4;n++){window.scrollTo(0,document.body.scrollHeight*n/3);await new Promise(r=>setTimeout(r,120));}});
     const view=await page.evaluate(()=>({title:document.title,language:document.documentElement.lang,bodyLength:(document.body?.innerText||"").trim().length,brokenImages:[...document.images].filter(x=>(x.offsetWidth||x.offsetHeight)&&x.complete&&x.naturalWidth===0).map(x=>x.currentSrc||x.src).slice(0,30)}));
     if(!response||response.status()>=400)problems.push("Navegación "+(response?.status()||0));
     if(!view.title||view.bodyLength<80)problems.push("Documento vacío o no legible");
     if(path.startsWith("/en")&&view.language!=="en")problems.push("Idioma no inglés");
     if(view.brokenImages.length)problems.push("Imágenes sin decodificar: "+view.brokenImages.join(","));
     checks.push({url:uri,viewport:vp.label,status:problems.length?"FAIL":"PASS",...view,problems});
    }catch(e){checks.push({url:uri,viewport:vp.label,status:"BLOQUEADO",problems:[String(e.message)]});}
    finally{await page.close();}
   }
   await context.close();
  }
  report.sites[site.id]={expected:(site.browserRoutes||[]).length*2,checks};
 }
}catch(e){report.fatal=String(e.stack||e);}
finally{await browser?.close();await writeFile(new URL("browser.json",out),JSON.stringify(report,null,2)+"\n");}
console.log("Browser QA: "+JSON.stringify(Object.fromEntries(Object.entries(report.sites).map(([k,v])=>[k,v.checks.filter(x=>x.status==="PASS").length+"/"+v.expected]))));
if(report.fatal||Object.values(report.sites).some(s=>s.checks.some(x=>x.status!=="PASS")))process.exitCode=1;
