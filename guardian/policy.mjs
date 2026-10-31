// Atlas Guardian: contratos deterministas (no confundir titular con confirmación).
export function eventSignal(headline) {
 const s=String(headline??"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase();
 if(/\b(no se (?:separa|disuelve)|desmiente(?:n)? (?:su )?(?:separacion|disolucion)|falso rumor)\b/.test(s))
  return {kind:"rumor/desmentida",level:"REVISAR",action:"Confirmar con fuente oficial; no afirmar disolución"};
 if(/(?:se (?:disolv|separ)|disolucion|separacion|ruptura (?:de |del )?(?:grupo|banda)|pausa indefinida|fin de la banda|anuncia (?:su )?despedida|fallecimient|fallecio|murio un integrante|murio el cantante)/.test(s))
  return {kind:"cambio mayor de la banda",level:"URGENTE_VERIFICAR",action:"Contrastar con fuente oficial e independiente; no afirmar el hecho a partir del titular"};
 if(/(?:nuevo (?:disco|album|ep)|lanza (?:un |su )?(?:disco|album|ep)|publica (?:un |su )?(?:disco|album|ep)|estrena (?:un |su )?(?:disco|album|ep)|sale (?:un |su )?(?:disco|album)|nuevo single|nuevo sencillo)/.test(s))
  return {kind:"lanzamiento discográfico",level:"ALTA",action:"Corroborar anuncio, fecha y obra antes de actualizar"};
 if(/(?:acustic|unplugged|sesion en vivo|live session|concierto intim|show sorpresa|nuevo documental|pelicula documental|nuevo videoclip)/.test(s))
  return {kind:"actuación o audiovisual",level:"REVISAR",action:"Determinar si es una nueva obra o una actuación relevante"};
 if(/(?:libro|entrevista|documental|estrena|gira|cancion|novedad|inedit|regreso|regresa)/.test(s))
  return {kind:"novedad editorial",level:"REVISAR",action:"Evaluar relevancia y si ya fue incorporada"};
 return null;
}
export function assessSite({missingUrls=0,brokenPages=0,brokenImages=0,brokenInternalLinks=0,blockedImages=0,blockedPages=0,missingChecks=0,brokenExternalLinks=0,blockedExternalLinks=0,candidates=[],sourceMissing=false,browserFails=0}={}){
 if(missingUrls||brokenPages||brokenImages||brokenInternalLinks||browserFails)return "ROJO";
 if(blockedImages||blockedPages||missingChecks||sourceMissing)return "GRIS";
 if(brokenExternalLinks||blockedExternalLinks||candidates.length)return "AMARILLO";
 return "VERDE";
}
export function uniqueNewsCandidates(items){
 const seen=new Set(),out=[];
 for(const item of items){
  const key=String(item.title||"").normalize("NFD").replace(/[\u0300-\u036f]/g,"").toLowerCase().replace(/\W+/g," ").trim();
  if(!key||seen.has(key))continue;
  seen.add(key);
  const signal=item.signal||eventSignal(item.title)||(item.type==="lanzamiento-posible"?{kind:"lanzamiento discográfico",level:"ALTA",action:"Confirmar con fuente oficial"}:null);
  if(signal)out.push({...item,signal});
 }
 return out.sort((a,b)=>Number(b.signal.level==="URGENTE_VERIFICAR")-Number(a.signal.level==="URGENTE_VERIFICAR"));
}
