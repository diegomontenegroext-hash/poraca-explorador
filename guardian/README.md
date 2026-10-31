# Atlas Guardian — ejecutor público separado de Por Acá

Este directorio está alojado aquí **solo como ejecutor gratuito y aislado de GitHub Actions**; no importa ni ejecuta el Radar cultural de Por Acá, no usa Neon, no accede a repositorios privados y no ejecuta Vercel. Una futura migración a un repo público dedicado conservará este directorio de forma autónoma.

- Primer Atlas: Babasónicos, por URL de producción y sitemap público.
- Baseline: 570 rutas y 15 portadas públicas recopiladas el 30/10/2026.
- Configuración: `guardian/config.json`.
- Prueba offline: `node --test guardian/tests/*.test.mjs`.
- Auditoría: `node guardian/runner.mjs`; navegador: `node guardian/browser.mjs` con Playwright en el runner.
- Agregar Atlas: `node guardian/enroll.mjs --id=identificador --url=https://dominio.vercel.app --images=/covers.json` (simulación); `--write` crea inventarios cuando el sitio tiene un JSON de imágenes aplicable.
- Nunca importar tokens de otros proyectos ni acceder a un Atlas privado sin credenciales específicas.
- No realizar reparaciones, merges, deploys ni cambios de contenido automáticamente.
- Cron mensual habilitar solo después de una corrida real validada, recepción de email y watchdog independiente de fallos/omisiones.

Estado: **piloto**, no certificado. El fallo previo del ejecutor privado era por agotamiento conocido de cuota de minutos, no por un error atribuido al Atlas.
