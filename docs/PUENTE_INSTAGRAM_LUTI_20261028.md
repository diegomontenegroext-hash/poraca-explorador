# Puente controlado Instagram — Luti, 28/10/2026

## Brecha real observada
`rd-ig-lutitravelguide` existe en Neon como `discover_only` (prioridad 50,
cadencia nominal 72 h, sin `last_checked_at`). No se consulta el feed y el
reel `DfDGyw_SkDA` no figuraba en `radar_definitivo.candidates` al corte.
La corrida FULL GitHub #40775098418 (65 fuentes / 10 IG exactos) tampoco
seleccionó esa cuenta. La tarea ChatGPT sólo orquesta GitHub.

## Intervención acotada
`ops/instagram-exact-seeds.json` admite links exactos compartidos y
atribuye cada uno a una cuenta del inventario `discover_only`. El runner
revisa sólo esos permalinks con límites originales, guarda candidato
`observed_unverified`, evidencia (caption de HTML público cuando existe,
metadatos e imagen referencial) y vínculo `seeded_exact_permalink`.

- Una URL canónica `/p/SHORTCODE/` o `/reel/SHORTCODE/` por entrada.
- Máximo 3 cuentas y 2 posts/cuenta por ejecución, relectura cada 36 h.
- Vencimiento explícito por entrada; sin persistencia de feeds ni Stories.
- `source_checks` marca `EXACT_PERMALINK_ONLY_PROFILE_NOT_SCANNED` y
  **no altera** `sources.last_checked_at` ni `next_due_at` del perfil.
- Ante 429/HTML inaccesible, reportar fallo sin atribuirle publicaciones.
- No se aceptan horarios implícitos, ni eventos, ni entidades automáticamente.

## Caso Luti
Reel del 28/10/2026
`https://www.instagram.com/reel/DfDGyw_SkDA/`
con múltiples propuestas de La Plata. Su descripción menciona el Piano Bar
de Casa Tomada, entre otras actividades del 28/10 al 1/11. Este paso sólo
asegura un **lead revisable** y preserva la descripción cuando el servidor
ofrece metadatos. La separación por actividad y la comprobación de horario
y sede requieren contrastar cada original; el feed automático de Luti
**sigue sin cobertura demostrada**.

## QA de aceptación
1. CI unitario verde, sin conexión a Neon.
2. Próxima corrida: verificar `candidates.url`, evidencia y
   `candidate_sources.source_id`, y que `sources.last_checked_at`
   del perfil Luti permanezca sin cambio.
3. Si se recupera el reel, contrastar cada actividad con cuenta oficial:
   Casa Tomada y otras; Motor/puente/web no se tocan en este cambio.
4. Para monitoreo regular real evaluar canal permitido (API autorizada,
   fuente pública con links a permalinks o agregador público accesible);
   `discover_only` no debe confundirse con feed monitorizado.
