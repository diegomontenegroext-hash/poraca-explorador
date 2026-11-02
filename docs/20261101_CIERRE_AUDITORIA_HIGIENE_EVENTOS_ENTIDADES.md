# Por Acá — Limpieza inteligente del catálogo, corte 01/11/2026

**Evidencia reproducible:** `sql/20261101_catalog_editorial_audit_READ_ONLY.sql`, consultas SQL SELECT en Neon PROD `frosty-union-52906378/br-mute-recipe-b4odj2bl/neondb` y prueba HTTP externa SSO de `/api/agenda`, `/api/approved-directory`. Ninguna escritura productiva de eventos, entidades o relaciones se realizó para esta auditoría.

## Diagnóstico en limpio

- **144 eventos canónicos**; 126 anteriores al día local; 18 para hoy o fechas futuras (16 `confirmed`, 2 `to_verify`).
- 123 eventos históricos conservan `status=scheduled` en el registro original. No afirmar que ocurrieron ni borrarlos. La web ya tiene `historyStatus` que combina día actual y fecha del evento para indicar «Fecha pasada · realización no corroborada»; no mutar 123 filas para reetiquetar el pasado.
- 9 eventos sin hora; 25 `to_verify` incluyendo fechas históricas; **4 expedientes futuros con `release_quality_gate` distinto de revisión estructural simple**.
- **Un único par de canónicos estrictamente duplicado (Iván Noble, 17/10, 21:00, Teatro Metro)**, y **cero pares sin decisión editorial**: `poraca_event_identity_resolutions_v1` ya marca `duplicate_alias`, preserva historia y la API proyecta sólo el canónico cuando coincide hora/sede/original. No eliminar ni reabrir.
- Las otras 3 coincidencias título+fecha+teatro eran **Play, de Samuel Beckett**, funciones 19:30 y 20:30 de 29, 30 y 31/10: **seis sesiones legítimas**. Jamás fusionar por texto/fecha sin comparar la hora.
- **478 observaciones staging sin verificación**; no equivalen a 478 eventos. Un grupo de tres anuncios aparentemente coincidentes de clases de tango requiere revisar la programación original, no aprobar/fusionar sin detalle.
- **135 entidades**: 80 aprobadas para identidad, 32 internas y 23 candidatas; 65 de las 80 aprobadas no tienen `last_verified_activity_at`. Esta fecha acredita *actividad real* y no debe rellenarse a partir de futuros anuncios. Tampoco interpretar `lifecycle_state='unknown'` como cierre.
- **51 entidades en minidirectorio protegido** porque cumplen un filtro de afirmación identitaria aceptada con fuente primaria/institucional y URL. Las otras 29 no prueban una pérdida de datos; permanecen en catálogo.
- **888 Casa** tiene identidad corroborada y descripción aceptada del 16/10, pero ninguna agenda actual corroborada; **Espacio Molière** todavía no tiene campos de ficha ampliada aceptados. `poraca_verified_public_entity_handoff_v1.web_handoff_state='visibility_conflict_hold'` es un **hold de entrega de dossier completo** con revisión manual, no prueba de que deba suprimirse una **mini ficha de identidad**. `api/approved-directory.js` y el cliente ya fuerzan `dossierLevel='mini_identity_only'` y `confirmedCurrentActivity=false`. No añadir una exclusión por ID, no afirmar que el lugar esté cerrado ni confundir estado de dossier con estado de identidad.
- Cero entidades con nombres normalizados exactamente repetidos. Tres URLs consideradas «oficiales» compartidas entre dos o tres entidades (en dos casos, anuncios de eventos de una ticketera): revisar clasificación `event_proof_url` frente a `official_entity_url`; jamás fusionar artista, organizador y lugar porque aparezcan en el mismo anuncio.

## Tanda de evidencia: cuatro próximos eventos retenidos

**No promover, ni editar certificación histórica mediante pruebas externas sin recibo editorial y readback.** Todos tienen registro canónico independiente.

1. `opera-carmen-sanchez-viamonte-2026-11-07`: 07/11, Teatro Ópera, **puertas 20:00, show 21:00** según [ticketera Livepass](https://livepass.com.ar/events/carmen-sanchez-viamonte-en-el-teatro-opera-lp-2026-11-07-20-00-00-0300). Neon: `confirmed`, `event_time=21:00`, evidencia propia `sourceRole=first_party_ticketing` con `supports=[title,date,time,venue]`, pero gate diagnóstico `hold_missing_primary_correlated_source`. **Posible desacople genérico de vocabulario de procedencia**; investigar contrato SQL y recibo, NO cambiar `sourceRole` para obtener verde.
2. `noches-capitales-babasonicos-2026-11-14`: 14/11, Hipódromo, **puertas 19:00, show 21:00** según [Livepass](https://livepass.com.ar/events/babasonicos-en-el-hipodromo-de-la-plata). Neon: `confirmed`, 21:00, misma categoría `first_party_ticketing` con campos corroborados y gate `hold_missing_primary_correlated_source`. Misma revisión de contrato de evidencia, no un parche para Babasónicos.
3. `cultural-98eea4dade88fd2fbfdc4b1a360ad2cf`: **Escrito en la piel**, sábados 21:30 en Centro Cultural Viejo Almacén El Obrero hasta 21/11 según [Alternativa Teatral](https://teatros.alternativateatral.com/obra103320-escrito-en-la-piel). Neon: `to_verify`, 07/11 21:30, cuarentena de recuperación histórica `publicationApproved=false`. La fuente apoya contenido; **el original, revisión y admisión editorial del caso** siguen siendo necesarios. No convertir sesión recurrente en infinitas funciones.
4. `cultural-6cf2d79cf70eac4e4006881207f111f2`: **Lección Magistral Emilio Custodio**, 18/11 10:00, FCNyM UNLP; comunicación oficial difundida [por la Facultad en LinkedIn](https://es.linkedin.com/posts/facultad-de-ciencias-naturales-y-museo_lecci%C3%B3n-magistral-emilio-custodio-las-activity-7520484756594221056-TPgg). Neon: `to_verify` y cuarentena `publicationApproved=false`, con URL de noticia institucional y evidencia `official_institution`. El título del ciclo no identifica al conferencista (Jesús Carrera); corregir solo mediante expediente editorial fechado. No autopublicar.

**Hipótesis general de QA**, por verificar contra el contrato SQL fuente: campos `fieldEvidence` y roles `first_party_ticketing` / `official_institution` podrían no estar siendo considerados por el gate de correlación. Una fuente puede ser un anuncio de ticketera legítimo sin ser la web del lugar. Una prueba general deberá:
- Validar coincidencia URL, día, hora de **show** frente a puertas, y sede;
- distinguir ticketera oficial/institución de agregador y prensa;
- respetar las cuarentenas `to_verify` y `publicationApproved=false`;
- no inferir aprobación a partir de que el enlace abre o de un título similar;
- preservar evidencia original, horario y recibos sin crear duplicados;
- registrar el resultado como `provenance_mismatch_review` si persiste el desacople, no como evento falso.

## Priorización por impacto de entidades

Nueve sedes con al menos un vínculo `hosted_at` aceptado hacia eventos futuros confirmados en esta base. Cuatro **sin fecha independiente de actividad verificada**: Pasaje Dardo Rocha, Ciudad de Gatos, En Eso Estamos e Hipódromo de La Plata. **No** rellenar `last_verified_activity_at` a partir de un evento anunciado que todavía no ocurrió. Priorizar una comprobación real de actividad del espacio y, por separado, ficha (dirección, descripción, oficialidad, fotos). Cinco ya registran fecha verificada: Casa Metro, Lumen Artis, Teatro Argentino, Teatro Ópera y Sala 420.

## Orden ejecutable sin complicación adicional

1. **Contrato de procedencia**: investigar los dos ticketings y los dos `to_verify` con un criterio común, sin escrituras masivas ni promociones automáticas.
2. **Presentación y SEO privados**: mini identidad vs programación real vs función vencida deben diferenciarse; mantener SSO y noindex. No reenviar a la home 123 históricos como funciones futuras.
3. **Lote 4 sedes en uso** antes que auditoría uniforme de 65 entidades sin fecha de actividad: verificar independencia entre evento anunciado y actividad real.
4. **URL oficial de entidad vs prueba de evento**: las 3 agrupaciones compartidas se revisan por rol de entidad, no por proximidad de nombres.
5. **Control recurrente integrado**: usar SQL read-only existente y tests del repositorio; conservar recibos y trazas. No cron nuevo, no build Vercel solo por diagnóstico, no borrado Neon.

**Estado:** auditoría y fuentes contrastadas, pendientes los cambios editoriales autorizados. La primera FULL con nuevo usuario limitado sigue siendo una prueba independiente de escritura de staging; no inferirla a partir de verify_only.
