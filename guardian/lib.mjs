export function url(s,base){if(typeof s!=="string"||!s.trim()||/^(#|mailto:|tel:|data:|javascript:|blob:)/i.test(s.trim()))return null;try{const u=new URL(s.trim().replace(/&amp;/g,"&"),base);if(!/^https?:$/.test(u.protocol)||u.username||u.password)return null;u.hash="";return u.href;}catch{return null;}}
export function sitemap(xml,base){return [...xml.matchAll(/<loc>\s*([^<]+)<\/loc>/g)].map(m=>url(m[1],base)).filter(u=>u&&new URL(u).origin===new URL(base).origin);}
export function htmlResources(html,base){
 const images=new Set(),links=new Set(),scripts=new Set();const add=(s,v)=>{const u=url(v,base);if(u)s.add(u)};
 for(const m of html.matchAll(/<(img|source|a|video|script|link|meta)\b[^>]*>/gi)){
 const tag=m[0],kind=m[1].toLowerCase();const a=Object.fromEntries([...tag.matchAll(/([\w:-]+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/g)].map(x=>[x[1].toLowerCase(),x[2]??x[3]??x[4]]));
 if(kind==="a")add(links,a.href);
 if(kind==="script")add(scripts,a.src);
 if(kind==="link"){if(/stylesheet/i.test(a.rel||""))add(scripts,a.href);if(/icon|image/i.test(a.rel||""))add(images,a.href);}
 if(kind==="meta"&&/^(og:image|twitter:image)$/i.test(a.property||a.name||""))add(images,a.content);
 if(kind==="img"||kind==="source"){add(images,a.src);add(images,a["data-src"]);for(const z of (a.srcset||"").split(","))add(images,z.trim().split(/\s+/)[0]);}
 if(kind==="video")add(images,a.poster);
 for(const z of cssUrls(a.style||"",base))images.add(z);
 }
 for(const z of cssUrls(html,base))images.add(z);
 return {images:[...images],links:[...links],scripts:[...scripts]};
}
export function cssUrls(s,base){return [...new Set([...s.matchAll(/url\(\s*["']?([^)'" ]+)["']?\s*\)/gi)].map(m=>url(m[1],base)).filter(Boolean))];}
export function jsImages(s,base){const a=new Set(cssUrls(s,base));for(const m of s.matchAll(/https?:\/\/[^\s"'<>\\)]+/gi)){const x=m[0].replace(/[;,]+$/,"");if(/\.(png|jpe?g|webp|gif|svg|avif)(\?|#|$)/i.test(x)){const u=url(x,base);if(u)a.add(u);}}return [...a];}
export function jsonImages(x,base,all=false){const a=new Set();function walk(v,key="",n=0){if(n>25)return;if(typeof v==="string"){if(all||/image|cover|photo|picture|poster|thumbnail|asset|tapa|visual/i.test(key)||/\.(png|jpe?g|webp|gif|svg|avif)(\?|$)/i.test(v)){const u=url(v,base);if(u)a.add(u)}}else if(Array.isArray(v))v.forEach(y=>walk(y,key,n+1));else if(v&&typeof v==="object")Object.entries(v).forEach(([k,y])=>walk(y,k,n+1))}walk(x);return [...a];}
export function verdict(status,kind,type="",bytes=Buffer.alloc(0)){if([401,403,429].includes(status)||status>=500||!status)return "BLOQUEADO";if([404,410].includes(status))return "ROTO";if(status<200||status>=400)return "BLOQUEADO";if(kind==="image"){if(!type.toLowerCase().startsWith("image/"))return "ROTO";const b=Buffer.isBuffer(bytes)?bytes:Buffer.from(bytes);if(!b.length)return "BLOQUEADO";const h=b.toString("hex",0,16),s=b.toString("utf8",0,350).trimStart();if(h.startsWith("ffd8ff")||h.startsWith("89504e470d0a1a0a")||h.startsWith("47494638")||(b.toString("ascii",0,4)==="RIFF"&&b.toString("ascii",8,12)==="WEBP")||/<svg\b/i.test(s)||h.startsWith("000000"))return "OK";return "ROTO";}if(kind==="html"&&!type.toLowerCase().includes("text/html"))return "BLOQUEADO";return "OK";}
export function reconcile(expected,actual){const e=new Set(expected),a=new Set(actual);return {expected:e.size,observed:a.size,missing:[...e].filter(x=>!a.has(x)),added:[...a].filter(x=>!e.has(x)),duplicates:actual.length-a.size};}
export function coverage(expected,checks){const seen=new Set(checks.map(x=>x.url));return {expected:new Set(expected).size,checked:seen.size,ok:checks.filter(x=>x.state==="OK").length,broken:checks.filter(x=>x.state==="ROTO").length,blocked:checks.filter(x=>x.state==="BLOQUEADO").length,unverified:[...new Set(expected)].filter(x=>!seen.has(x))};}
