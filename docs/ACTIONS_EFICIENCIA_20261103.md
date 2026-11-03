# Por Acá — política de uso eficiente de GitHub Actions

Corte: 2026-11-03. Aplica a `poraca-explorador` y al QA visual de `poraca-lp`. No altera programación de Radar, permisos ni publicación.

## Evidencia del problema

- De las últimas 100 ejecuciones visibles de Radar: 62 QA definitivo, 23 QA antiguo, 12 Radar operativo y 3 Atlas Guardian; 13 SHAs dispararon ambos QA de código.
- Del último conjunto de 100 ejecuciones de la web: 99 QA visuales (33 success, 19 failure y 47 cancelled). Las cancelaciones ya estaban habilitadas, pero no recuperan necesariamente el tiempo de runner consumido.
- No confundir cantidad de runs ni segundos de pared con minutos facturados: verificar la métrica nativa de GitHub antes de cuantificar ahorro real.

## Contrato operativo

1. **Radar operativo** (`radar-definitivo.yml`): conservar la programación existente del orquestador GPT y su grupo de concurrencia con `cancel-in-progress: false`. Nunca cancelar una FULL/ingesta en proceso para ahorrar minutos. Sin introducir otro cron, una FULL extra o escrituras por QA.
2. **Radar QA de código** (`radar-definitivo-ci.yml`): único `push` automatizado en `main` para `src/**`, `tests/**`, `sql/**`, `data/**`, semillas Instagram exactas y workflows Radar. Compila y prueba toda la suite **sin Neon**. La concurrencia cancela solo QA anterior de tipo `push` en la misma rama; los QA manuales tienen otra clave. No saltear tests por archivo individual.
3. **QA antiguo** (`radar-ci.yml`): `workflow_dispatch` únicamente para investigación manual. No duplicar tests automáticos sobre el mismo SHA.
4. **Atlas Guardian**: conservar vigilancia mensual y reintento de calendario existentes; no agregar tareas periódicas. El guard de mes evita repetir auditoría completa después de un mes ya reportado.
5. **Por Acá web**: `poraca-visual-qa.yml` ya cancela QA obsoletos, pero la batería Chromium sigue siendo costosa. **No suprimir sin sustituto la navegación visual previa a aceptación**. Agrupar cambios de UI/editorial por lote y publicar/QA el SHA consolidado. Para trabajos pequeños, ejecutar Node local/QA focal antes de comprometer `main`; QA visual integral en un lote terminado, no por cada microajuste. Despliegue Vercel `READY` no equivale a QA Chromium.

## Criterios de aceptación y controles

- Un commit con código Radar debe generar **un solo QA automático**, no dos workflows de suites equivalentes.
- Cambios de documentación, issues y `ops/radar-fallback-trigger.txt` no deben lanzar QA de código por sí solos.
- Un disparo de Radar por `ops/radar-fallback-trigger.txt` debe conservar su adquisición y recibos existentes; una segunda ejecución no es sustituto de una corrida fallida.
- QA `SUCCESS` no acredita O3/F5, adquisición de Biblioteca UNLP, publicación editorial, disponibilidad de la web ni avance IICS. Usar readbacks de Neon y evidencia por gate.
- La próxima revisión: comparar **últimos 100 runs** antes/después, duplicaciones por SHA, segundos de job, cancelaciones y cambios de cobertura. No anunciar ahorro monetario sin datos de facturación.

## Norma de edición

Hacer cambios coherentes en un **solo commit por lote** sobre `main` (sin ramas paralelas) y esperar una suite consolidada. Los microcommits correctivos son excepción ante un QA real fallido. No empujar cambios vacíos, no hacer `workflow_dispatch` redundantes ni duplicar FULLs solo para elevar la nota.
