import test from "node:test";import assert from "node:assert/strict";import {sitemap,htmlResources,jsImages,jsonImages,verdict,reconcile,coverage} from "../lib.mjs";
test("sitemap exacto",()=>assert.deepEqual(sitemap("<loc>https://a.example/a</loc><loc>https://b.example/b</loc>","https://a.example"),["https://a.example/a"]));
test("imágenes HTML y enlace",()=>{const d=htmlResources('<img src="/x.jpg" srcset="/y.jpg 2x"><meta property="og:image" content="/z.png"><a href="/r">a</a>',"https://a.example");assert.equal(d.images.length,3);assert.equal(d.links.length,1);});
test("imágenes JSON sin extensión",()=>assert.deepEqual(jsonImages({"Pasto":"https://a.example/image123"},"https://a.example",true),["https://a.example/image123"]));
test("imágenes css y JS",()=>assert.equal(jsImages('url(/a.webp) "https://b.example/x.jpg"',"https://a.example").length,2));
test("imagen HTML falsa nunca pasa",()=>{assert.equal(verdict(200,"image","image/jpeg",Buffer.from("<html>")),"ROTO");assert.equal(verdict(200,"image","image/png",Buffer.from([137,80,78,71,13,10,26,10])),"OK");assert.equal(verdict(403,"image"),"BLOQUEADO");});
test("URL perdida detectada",()=>{assert.deepEqual(reconcile(["a","b"],["a"]).missing,["b"]);assert.equal(coverage(["a","b"],[{url:"a",state:"OK"}]).unverified.length,1);});

test("Wikimedia: página de archivo no es imagen, archivo upload sí",()=>{
 const page=jsonImages({cover:"https://commons.wikimedia.org/wiki/File:Babasonicosroger.jpg"},"https://atlas.example",true);
 const file=jsonImages({cover:"https://upload.wikimedia.org/wikipedia/commons/9/92/Babasonicosroger.jpg"},"https://atlas.example",true);
 assert.equal(page.length,0);assert.equal(file.length,1);
});
