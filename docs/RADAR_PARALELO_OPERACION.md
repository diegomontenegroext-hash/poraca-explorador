# Radar paralelo Por Acá — piloto 0.1

**Estado:** base y permisos de lectura/escritura creados en Neon. Código de adquisición y workflow integrados. El primer modo `dry-run` consulta sitios sin escribir; el modo `write` se habilita al instalar **UN secreto**, sin publicarlo en GitHub ni en ChatGPT.

## Aislamiento exacto

- Proyecto Neon existente: `frosty-union-52906378` (cuenta Free, compartido con otros proyectos).
- **Rama obligatoria:** `poraca-production`, ID `br-mute-recipe-b4odj2bl`.
- **Base nueva:** `poraca_explorador`.
- **Rol nuevo:** `poraca_explorador_writer`.
- Nunca usar `neondb` ni rama `production` (corresponde a Bitácora).
- La misma rama Neon implica uso de su cómputo y cuotas; la independencia es **lógica por base de datos**, no un servidor aislado.
- Tablas propias: `sources`, `source_checks`, `radar_runs`, `candidates`.

## Activar la primera escritura real (paso humano imprescindible)

1. En [Neon Console](https://console.neon.tech/), abrir el proyecto `bitacora` (ID arriba).
2. Elegir branch `poraca-production` (no `production`), base `poraca_explorador`, role `poraca_explorador_writer`.
3. Copiar la **connection string PostgreSQL** completa de esos tres selectores (con SSL). No compartirla en el chat ni confirmarla con una captura.
4. Abrir [GitHub Actions secrets](https://github.com/diegomontenegroext-hash/poraca-explorador/settings/secrets/actions), usar **New repository secret** con nombre exacto `NEON_EXPLORADOR_DATABASE_URL`, pegar la conexión y guardar.
5. En [Radar paralelo](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/workflows/radar-paralelo.yml) elegir **Run workflow** en `main`, parámetro `mode=write`.
6. Verificar en Summary: `database_written=true`, `sources_attempted`, `sources_success`, `candidates_seen`, `candidates_new`. Si no hay fuentes debidas, el run puede completarse sin candidatos: no fingir ingestión.
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

## Siguiente gate, NO autorizado todavía
Tras el primer run `write` con readback:
- habilitar `schedule` a las 10:20/16:20/22:20 ART, inicialmente en paralelo;
- controlar varios ciclos de fuente, ritmo de descubrimiento, calidad y fecha de los candidatos, fallas HTTP y cuotas;
- decidir si la integración con la aceptación canónica de Por Acá tiene mérito. No unir bases ni insertar eventos públicos sin revisión y contrato.

**Seguridad:** el workflow sólo tiene permiso `contents:read`, el `DATABASE_URL` se inyecta desde el secreto y se comprueba `current_database()` y `current_user` antes de escribir. Nunca usar credenciales de administrador.
