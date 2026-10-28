# Prueba completa de recuperación de Instagram (28/10/2026)

## Evidencia de los ejecutores GitHub Actions

1. [Lectura de 3 publicaciones exactas históricas](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625398760): 3/3 HTTP 200, canonical del shortcode coincidente, metadatos `description`, `og:title`, `og:description`, `og:image`. No se extrajeron pies de foto completos ni hechos de calendario verificados.
2. [Descubrimiento de enlaces](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625611123): 4 webs leídas, 7 páginas HTML inspeccionadas, 6 permalinks Instagram encontrados en una agenda pública de Vive La Plata. Los otros sitios no produjeron enlaces en esta muestra. Enlaces históricos: no son novedades.
3. [Cadena combinada: agenda → Instagram](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625709193): SUCCESS + tests PASS. Detectó 6 permalinks desde páginas externas y abrió **automáticamente** el primero, `https://www.instagram.com/p/Dd9NDd-IH5U/`, con **HTTP 200**, canonical coincidente y los cuatro campos de metadatos citados. No se leyó ni validó fecha/hora/sede.

## Lección

En la primera prueba de perfiles generales (Select, EcoSelect, Casa52) **3/3 respondieron HTTP 429**. Los cuatro permalinks probados, tres históricos conocidos y uno descubierto automáticamente desde agenda, respondieron HTTP 200. El éxito de un permalink en esta muestra NO garantiza que otros posts funcionen, que los perfiles sean navegables, ni permite afirmar acceso a Stories.

La prueba de 13/10 original en Por Acá con TinyFish Fetch (40/42 perfiles y 120 posts según su propio reporte) usaba un servicio distinto. No se trasplantó ese backend a Python. Este experimento demuestra una **vía gratuita parcial**: reconocer permalinks desde agendas accesibles y leer metadatos que el post muestra públicamente.

## Hito pendiente para operar

- Descubrir enlaces recientes de forma sostenida, con muestra representativa de disciplinas y territorios y origen comprobado.
- Extraer campos de eventos del texto público disponible, distinguiendo la fecha del post de la fecha del acontecimiento; corroborar autor/organizador, sede, horario y posibles cambios.
- Deduplicar anuncios y comparar con Neon en lectura; sólo después habilitar alta de candidatos con rol mínimo mediante contrato transaccional existente. La **lectura no equivale a evento aceptado**.
- Registrar la tasa de URLs encontradas, posts legibles, campos probados, errores 429 y comparación con Radar en varios días. Mantener sin cron hasta terminar el gate.
- No usar oEmbed de Meta para alimentar extracción de datos: su finalidad documentada es la inserción en frontend, no adquirir su contenido para otros fines.

**No se cambiaron Radar ChatGPT, Neon, API, web ni despliegues. No se programó ninguna tarea recurrente.**
