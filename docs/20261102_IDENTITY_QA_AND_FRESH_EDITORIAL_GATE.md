# Por Acá — Control editorial puntual y dos identidades, 02/11/2026

## Fuentes externas contrastadas

**Malena Muyala**: [ficha original Casa Metro](https://casametro.com.ar/evento/malena-muyala/) y [cartelera del organizador](https://casametro.com.ar/categoria-producto/casa-metro/) coinciden: **21/11/2026, 22:00, Sala A – Casa Metro**. En el corte anterior Neon contiene 5 observaciones brutas de la función (3 con URL directa del original) y **0 eventos canónicos correspondientes**. No es una prueba de celebración del recital, es un anuncio público verificable. Los duplicados de la bandeja ya fueron corregidos como presentación en la web, conservando el historial. La siguiente puerta de aceptación requiere **recibo editorial independiente con observación exacta**, acto autorizado de admisión, y readback canon/API/web. [Consulta segura del expediente](../sql/20261102_malena_fresh_editorial_gate_READ_ONLY.sql). Estado: **pendiente de recibo y de publicación**, sin insertar un canon para obtener un PASS artificial.

**Pasaje Dardo Rocha**: [Bafilma, plataforma oficial bonaerense](https://bafilma.gba.gob.ar/locaciones/la-plata/centro-cultural-pasaje-dardo-rocha) acredita centro cultural y su ubicación en calle 50 entre 6 y 7. No acredita que hoy esté abierto ni el horario de una función.

**En Eso Estamos**: [sitio del propio espacio](https://enesoestamosfc.wordpress.com/) describe su identidad como fábrica cultural autogestiva y dirección en calle 62 Nº 274. La página es útil para identidad, pero no certifica su apertura o programación de noviembre.

## Migración de identidad, QA validada (no producción)

Se versionó [SQL aditivo y acotado](../sql/20261102_two_venue_identity_receipts_additive.sql). Solo agrega **dos afirmaciones `descripcion` revisadas** con su URL de prueba y atributos explícitos `does_not_prove_current_opening=true`, `does_not_prove_current_events=true`, `not_full_dossier=true`. No actualiza actividad real ni toca `radar_agenda_events`.

**QA Neon**: proyecto `frosty-union-52906378`, rama `br-icy-night-b4larkc3`, base `neondb`, una transacción con `INSERT` + guardas, resultado **2 insertadas**: ID **673** `pasaje-dardo-rocha` (`institutional`) y **674** `en-eso-estamos` (`first_party`). Verificación QA de `poraca_verified_public_entity_handoff_v1`: **ambas en `manual_diff_and_publication_gate_required`** para dossier completo, por lo que no se concede aprobación L4 ni actividad actual. `assertion_id` usa `GENERATED ALWAYS`; la primera tentativa con nextval fue rechazada y su transacción se revirtió, la migración se corrigió y pasó el control.

**No instalado en producción**: el control adicional de elegibilidad de mini identidades devolvió un bloqueo de seguridad de herramienta. Respetar el bloqueo, **no reemplazarlo por otra ruta de ejecución**. Requiere validación operativa del control antes de llevar estas dos pruebas a la rama productiva y comprobar si minidirectorio pasa de 51 a 53. No anunciar que aparecen ya en la web ni alterar SSO para probarlo.

## Regla general

Una fuente **institucional** prueba lo que informa expresamente; una **autodescripción** acredita la identidad declarada. Ninguna prueba por sí sola actividad vigente, funciones futuras ni la revisión/aceptación final de un evento. QA y staging son ambientes independientes de publicación. No certificar 3/7 días ni Chromium SSO por una prueba unitaria.
