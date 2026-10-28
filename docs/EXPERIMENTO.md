# Por Acá · Explorador cultural / experimento 0.1

Proyecto independiente y público: prueba gratuita de adquisición, sin secretos ni modificaciones al Radar de ChatGPT, Neon o la web.

**Alcance real:** nueve URLs públicas (seis webs culturales/medios y tres perfiles de Instagram). Se intenta abrir cada página una vez, se registra HTTP, título, encabezados y hasta cinco enlaces que parecen actividades. **No valida eventos ni identifica publicaciones de Instagram**; un HTTP 200 de Instagram sólo indica que respondió HTML, no que pudieron recuperarse sus posts.

## Cómo ejecutar
1. GitHub → Actions → «Por Acá · prueba de fuentes» → «Run workflow».
2. Abrir la ejecución, leer su «Summary» y «Probar nueve fuentes» en los logs.
3. Contrastar accesibles/inaccesibles con Radar y Neon antes de automatizar.
4. Ejecutar de nuevo otro día para evaluar repetibilidad; **ninguna fuente se considera cubierta por una sola prueba**.

## Garantías de la prueba
- Sólo se activa manualmente por workflow_dispatch. No hay cron.
- Sin variables ni credenciales, sin acceso a la base Neon y sin publicación web.
- Python estándar, sin instalar dependencias; ejecución limitada a 5 min.
- Descarga de hasta 400 KiB HTML por URL y timeout de 10 segundos.
- Sin artefactos persistentes ni cache de GitHub Actions.
- No bypass de login, antirrobots, CAPTCHA ni rate limit.
- Titulares y enlaces hallados son **pistas**; nunca hechos culturales admitidos.

## Ejecutar localmente
```bash
python3 -m unittest discover -s tests -v
python3 src/explore.py
```

El archivo `resultado-exploracion.json` se genera en el entorno de ejecución, **no se sube**. El Summary del job permite revisar el resultado sin almacenamiento adicional.

## Siguiente fase (no implementada)
Si varias fuentes devuelven datos útiles, añadir detección diferencial, almacenamiento de candidatos y cursor en Neon con permisos restringidos y deduplicación. Definir explícitamente fuentes originales aceptables y conservación de procedencia antes de cualquier escritura.