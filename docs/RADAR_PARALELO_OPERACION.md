# Radar paralelo Por Acá — piloto 0.1

**Estado al 28/10/2026:** primera escritura REAL completada y corroborada en Neon, con secret GitHub `NEON_EXPLORADOR_DATABASE_URL` configurado. Tres corridas automáticas programadas en paralelo con Radar ChatGPT. Primera ejecución en modo `write`: [GitHub Actions #40627651136](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/40627651136), 6 fuentes consultadas, 5 accesibles, 6 candidatos nuevos, 6 controles registrados, corrida `partial` por fallo de acceso Centro de Arte UNLP. Los candidatos no están verificados.

## Aislamiento exacto

- Proyecto Neon existente: `frosty-union-52906378` (cuenta Free, compartido con otros proyectos).
- **Rama obligatoria:** `poraca-production`, ID `br-mute-recipe-b4odj2bl`.
- **Base nueva:** `poraca_explorador`.
- **Rol nuevo:** `poraca_explorador_writer`.
- Nunca usar `neondb` ni rama `production` (corresponde a Bitácora).
- La misma rama Neon implica uso de su cómputo y cuotas; la independencia es **lógica por base de datos**, no un servidor aislado.
- Tablas propias: `sources`, `source_checks`, `radar_runs`, `candidates`.

## Consultar y ejecutar el sistema ya activado

El secreto `NEON_EXPLORADOR_DATABASE_URL` ya se instaló. **No copiarlo ni volverlo a crear** salvo rotación de credenciales. Para un diagnóstico manual, abrir [Radar paralelo GitHub Actions](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-paralelo.yml), elegir `Run workflow` → `dry-run` o `write` (éste guarda en la base aislada). El ejecutor temporal de la primera escritura se retiró.

**Automatización desde 28/10:** `20 1,13,19 * * *` UTC = **22:20, 10:20, 16:20 ART**, con posibles retrasos del scheduler de GitHub. Los horarios repiten los de Radar ChatGPT pero sus responsabilidades y bases están separadas; no se ha retirado ninguna tarea existente.

**Cómo verificar en Neon:** abrir proyecto `bitacora`, rama `poraca-production`, base `poraca_explorador`. Ejecutar las consultas de abajo. Las credenciales sólo están en el secreto cifrado de Actions.

7. Leer Neon en esta base, por ejemplo:

```sql
SELECT run_id,started_at,finished_at,status,sources_attempted,
       sources_success,candidates_seen,candidates_new
FROM radar_runs ORDER BY started_at DESC LIMIT 10;

SELECT kind,review_state,count(*) FROM candidates GROUP BY 1,2 ORDER BY 1;

SELECT source_id,http_status,status,pages_opened,discovered_links
FROM source_checks ORDER BY checked_at DESC LIMIT 30;
```

## Qué recolecta de verdad
- Índices públicos de 13 fuentes iniciales (hasta 6 vencidas por ejecución).
- Hasta tres páginas de detalle por fuente y permalinks exactos a Instagram que encuentre en el HTML público; nunca feed restringido o Stories.
- Si detecta JSON-LD `Event`, puede recoger fecha/hora/sede/organizador **que estén explícitos**. Si no, esos campos quedan NULL.
- Registra estado HTTP, acceso, cantidad de enlaces, pistas y URLs; deduplica por URL original, y distingue candidato nuevo de revisita.
- Una URL con 200, la presencia de `og:description` o un artículo de un medio **no** confirman por sí solos un evento.
- No publica nada en Por Acá, no modifica Radar ChatGPT, no usa Work, no cambia SQL del `neondb` operativa.

## Siguiente gate

- **Ya ejecutado:** primer run `write` con readback y `schedule` tres veces al día.
- **Pendiente:** controlar varios ciclos de fuente, ritmo de descubrimiento, calidad y actualidad de los candidatos, fallas HTTP, accesibilidad Instagram y cuotas.
- **Pendiente:** extraer fechas/horarios/sedes con evidencia suficiente. La primera corrida produjo seis `unverified` sin fecha de evento válida; no afirmar que se confirmaron seis actividades culturales.
- **Prohibido por ahora:** fusionar bases, aceptar o publicar eventos automáticamente, retirar el Radar ChatGPT o alterar API/Vercel sin reconciliación de evidencia.

**Seguridad:** el workflow sólo tiene permiso `contents:read`, el `DATABASE_URL` se inyecta desde el secreto y se comprueba `current_database()` y `current_user` antes de escribir. Nunca usar credenciales de administrador.
