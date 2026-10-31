# Atlas Guardian — mantenimiento público de Atlases

Guardian revisa **solo la web publicada**, sin acceder a repositorios Atlas privados y sin publicar ni desplegar nada.

## Piloto Babasónicos

- Baseline de 570 URL y 15 portadas de producción. HTTP a todas las URL registradas; imágenes descubiertas por HTML/JS/CSS/JSON y portadas; enlaces externos comprobados por estado. Inventarios limitados a los recursos **descubiertos**, no equivalen a todas las imágenes posibles si existen cargas dinámicas que no registran estas fuentes.
- Chromium abre cuatro rutas de muestra en móvil/escritorio (8 recorridos). No afirmar inspección visual de todas las 570 páginas.
- Consulta MusicBrainz y titulares de Google News dentro de una ventana de 40 días. **No es un seguimiento exhaustivo de fuentes oficiales ni noticias de todo Internet.** Los titulares se clasifican en posibles cambios de banda, lanzamientos, acústicos y otros; se **verifican editorialmente** antes de afirmar hechos.
- Rojo para páginas/imágenes realmente rotas; gris ante comprobación parcial; amarillo para señales editoriales, enlaces terceros rotos o bloqueos externos. La ejecución Actions puede marcar SUCCESS mientras el Atlas está AMARILLO/GRIS: hay un informe generado, no significa que todo esté bien.

## ¿Quién ejecuta Guardian?

**GitHub Actions del repositorio público** `poraca-explorador`, en `.github/workflows/atlas-guardian-pilot.yml`.
Primera programación: día 3 a las **09:17 ART** (`17 12 3 * *` UTC).
Respaldo: día 4 a las **09:47 ART** (`47 12 4 * *` UTC); consulta el marcador del informe del mes en [issue #4](https://github.com/diegomontenegroext-hash/poraca-explorador/issues/4) y omite reejecución si ya hubo informe.
El backup protege contra algunos fallos de programación, **no garantiza** entrega: GitHub puede demorar o perder ejecuciones, y un repositorio público inactivo durante 60 días puede tener sus horarios deshabilitados. Hace falta un watchdog externo independiente para garantizar una alerta de ausencia.
Los cambios en el código de Guardian lanzan QA de prueba por push, pero **no** emiten el informe mensual a issue ni email. El informe programado conserva un marcador mensual para evitar duplicados.

## ¿Cómo avisa?

- Informe resumido en issue público #4, con evidencia completa en artifact Actions; archivo retención 30 días.
- Email de prueba fue enviado desde `sobreflora@gmail.com` a `diegomontenegroext@gmail.com` mediante el conector Gmail de ChatGPT. **Esa conexión NO es accesible desde GitHub Actions.** Email directo automatizado todavía sin activar: el workflow solo admite proveedor Resend opcional con secretos; no garantiza remitente `sobreflora@gmail.com`. Configurar OAuth específico para Gmail si el remitente exacto es obligatorio; no compartir tokens en chat ni colocar direcciones o credenciales en este repositorio público.
- La funcionalidad de watchdog externo existe como webhook **optativo**: proveedor/secret de vigilancia no configurados.

## Casos adversos incluidos en tests

- Tres fotografías rotas → ROJO, resumen de cada recurso.
- HTTP 429 de imagen → GRIS, nunca falso VERDE.
- Posible disolución, nuevo disco, concierto acústico → señales con distinta prioridad, **sin afirmar que el titular sea cierto**.
- Titular de desmentida no se trata como disolución confirmada.
- Falta de verificación o fuente editorial caída → GRIS.
- Simulación de día 4 con comentario previo del mismo mes → omite duplicado; otro mes sí ejecuta.

## Nuevo Atlas

Simular `node guardian/enroll.mjs --id=mi-atlas --url=https://mi-atlas.vercel.app --images=/covers.json`; usar `--write` únicamente tras revisar el sitemap real y el registro de imágenes del proyecto. Agregar fuentes, imágenes y recorridos apropiados para cada Atlas. No desproteger SSO o Deployment Protection para hacer el control.

**Limitación aceptada:** una salida verde certifica el alcance explícito, no toda posible ruta editorial o visual. Este monitor no modifica el sitio, fotos, enlaces ni catálogo; propone acciones para revisión.
