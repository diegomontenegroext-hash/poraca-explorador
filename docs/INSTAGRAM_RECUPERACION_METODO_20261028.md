# Recuperación del método Instagram de Por Acá — 28/10/2026

## Antecedentes recuperados del repositorio privado

Documento original: `poraca-lp/docs/INSTAGRAM_FUENTES_Y_FLYERS_V1.md` (13/10/2026).

- 12/10: el Radar directo no accedió a 28 perfiles de 28 intentados.
- 13/10: una corrida con **TinyFish Fetch**, lector externo de páginas, accedió a 40 de 42 perfiles y reportó 120 publicaciones leídas. **No es prueba de que Python directo pueda leer los feeds:** TinyFish era un proveedor diferente y no equivale a GitHub Actions gratuito.
- El análisis histórico distinguía **descubrimiento de URLs desde el perfil** y **lectura de posts /p/ o /reel/ cuando se conoce la URL**.
- El post `/p/DeHOPiJRwNi/` y el reel `/reel/DeIP5x6RTRH/` permitieron recuperar texto y metadatos de un anuncio en aquella investigación, sin reproducción necesaria del video. No se documentó acceso a historias.

## Prueba directa nueva (sin TinyFish)

[GitHub Actions · ejecución 40625398760](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40625398760), 28/10/2026, SUCCESS, tests PASS.

| Unidad | Resultado |
|---|---|
| Perfil `instagram.com/cineselect/` | 429 en primera prueba de conectividad |
| Perfil `instagram.com/cineecoselect/` | 429 |
| Perfil `instagram.com/casa52casa/` | 429 |
| Post exacto `instagram.com/p/DeHOPiJRwNi/` | 200, canonical coincide, og:title / og:description / og:image y descripción presentes |
| Reel exacto `instagram.com/reel/DeIP5x6RTRH/` | 200, canonical coincide, metadata descriptiva y de imagen |
| Post exacto `instagram.com/malisialibros/p/DeW_6noxGOx/` | 200, canonical coincide, metadata descriptiva y de imagen |

**Alcance de la prueba:** se verificó que el servidor entregó metadatos específicos del permalink indicado. El script no guardó pies de foto completos, no comprobó datos de fecha/hora/sede y no descubrió publicaciones nuevas. Tampoco se utilizó una API oficial para extracción de contenidos, credenciales, proxies o accesos privados. Ante HTTP 429 el script detiene los intentos adicionales.

## Arquitectura de adquisición gratuita por probar

1. **Fuentes captadoras accesibles:** agendas y páginas culturales propias, artículos, canales de eventos y sitios de organizadores; en una muestra, extraer enlaces a publicaciones /p/ y /reel/ desde HTML y páginas de detalle.
2. **Post exacto:** intentar abrir la URL conocida una sola vez con límites; extraer sólo lo verificable y conservar URL, código HTTP, fecha de observación, campos disponibles y advertencias.
3. **Verificación de hechos:** probar que pie de post, fecha/hora/sede/organizador realmente estén presentes; un og:image no equivale a un flyer validado.
4. **Dedupe y continuidad:** contrastar contra registros históricos de Neon sólo en lectura hasta diseñar credenciales y función de inserción restringida; no usar 200 como evidencia de nueva publicación.
5. **Límite principal:** **descubrir URLs nuevas de Instagram** sigue sin resolverse con sólo abrir los posts ya conocidos. El objetivo de la próxima prueba es extraer links exactos desde páginas públicas accesibles, no depender de feeds bloqueados.
6. **Fuentes alternativas:** cuando un perfil bloquea el acceso o no hay permalink descubierto, buscar información publicada por el organizador en su web, cartelera, agenda o canales enlazados. No equiparar perfil bloqueado con inactividad.

**No debe automatizarse masivamente ni usarse un método que eluda bloqueos de acceso.** Este documento no cambia el Radar programado ni escribe Neon.
