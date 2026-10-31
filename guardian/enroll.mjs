import {readFile,writeFile,mkdir} from "node:fs/promises";
import {sitemap,jsonImages} from "./lib.mjs";
const args=Object.fromEntries(process.argv.slice(2).filter(x=>x.startsWith("--")&&x.includes("=")).map(x=>{const i=x.indexOf("=");return [x.slice(2,i),x.slice(i+1)];}));
const id=args.id,url=args.url,images=args.images||"/covers.json",write=process.argv.includes("--write");
if(!/^[a-z][a-z0-9-]{2,30}$/.test(id||""))throw Error("Requerido --id=atlas-unico (min. 3 caracteres)");
let base;
try{base=new URL(url)}catch{throw Error("Requerido --url=https://dominio-de-produccion/")}
if(base.protocol!=="https:"||base.username||base.password||base.hostname==="localhost"||/^(?:127\.|10\.|192\.168\.|169\.254\.)/.test(base.hostname))throw Error("Solo se admite dominio público HTTPS");
base.pathname="/";base.hash="";base.search="";
const configPath=new URL("./config.json",import.meta.url);
const config=JSON.parse(await readFile(configPath,"utf8"));
if(config.sites.some(s=>s.id===id||new URL(s.url).origin===base.origin))throw Error("Atlas ya registrado por ID u origen");
async function text(uri){
 const c=new AbortController(),t=setTimeout(()=>c.abort(),18000);
 try{const r=await fetch(uri,{signal:c.signal,headers:{"User-Agent":"AtlasGuardian/1.0 (onboarding)"}});if(!r.ok)throw Error("HTTP "+r.status+" "+uri);return await r.text();}
 finally{clearTimeout(t);}
}
const urls=sitemap(await text(new URL("/sitemap.xml",base).href),base.href);
if(!urls.length||new Set(urls).size!==urls.length)throw Error("Sitemap vacío o duplicado: no se admite alta");
const imagesUrl=new URL(images,base).href, data=JSON.parse(await text(imagesUrl));
const found=jsonImages(data,imagesUrl,true).filter(x=>/^https:/.test(x));
if(!found.length)throw Error("No se detectó inventario de imágenes; proporcionar --images=/ruta-al-json con recursos reales");
const inventory=[...new Set(found)];
const routes=["/"];
if(urls.length>1)routes.push(new URL(urls.find(x=>new URL(x).pathname!=="/")||urls[0]).pathname);
if(urls.some(x=>new URL(x).pathname.startsWith("/en/")))routes.push("/en/");
const record={id,enabled:true,url:base.origin,baseline:"guardian/baselines/"+id+".urls.txt",expectedImagesAtLeast:inventory.length,assetPaths:[],imageJsonPaths:[new URL(imagesUrl).pathname],browserRoutes:[...new Set(routes)],newsQuery:""};
console.log(JSON.stringify({mode:write?"WRITE":"DRY_RUN",site:id,origin:base.origin,pages:urls.length,images:inventory.length,browserRoutes:record.browserRoutes},null,2));
if(!write){console.log("No se modificaron archivos. Agregar --write para incorporar el Atlas en la rama actual y revisar el diff.");process.exit(0);}
await mkdir(new URL("./baselines/",import.meta.url),{recursive:true});
await writeFile(new URL("./baselines/"+id+".urls.txt",import.meta.url),"# Alta verificada: "+new Date().toISOString()+"\n"+urls.join("\n")+"\n");
await writeFile(new URL("./baselines/"+id+".images.txt",import.meta.url),"# Alta verificada: "+new Date().toISOString()+"\n"+inventory.join("\n")+"\n");
config.sites.push(record);await writeFile(configPath,JSON.stringify(config,null,2)+"\n");
console.log("Registrado en archivos locales. Crear PR; revisar protección/acceso y QA antes de activar.");
