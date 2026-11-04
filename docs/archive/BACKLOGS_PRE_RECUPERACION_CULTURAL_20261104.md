# Backlogs anteriores a la recuperación cultural · 04/11/2026

Se conservan los cuerpos íntegros leídos antes de actualizar el backlog; son antecedentes históricos, no el estado vigente.

## poraca-lp #16

# Por Acá — backlog ejecutivo único · consolidación funcional publicada 04/11/2026

Objetivo: plataforma acumulativa de vida cultural/social de La Plata. Misma cadena Radar → Neon → admisión y mantenimiento limitados → APIs existentes → web privada. Identidad, programa, actividad habitual y evento conservan significados distintos.

## Producción verificable
- Web/API: **0a581ae522cb4a1cd46922c6ef4974db27e7bbd5**; deployment **dpl_2xphm2vN4pqrk5Msn2KLviMctM3T READY**, [dominio habitual](https://poraca-lp-privado.vercel.app/), SSO all/noindex conservados.
- Radar main: **821758b8d8bb2c9a9fe4b3091d4969b814c81064**, código preparado para la próxima ejecución ordinaria. No se lo atribuye al run previo ni se disparó FULL/Action adicional.
- Neon: **frosty-union-52906378 / br-mute-recipe-b4odj2bl / neondb**. SQL aplicado; fuente y recibo de entrega en main **0c714a2ce49c056794cd930f745d62a929d87a9a** (solo SQL de lectura acotada/documentación/test después del despliegue, sin nuevo código web que publicar).
- [Contrato y evidencia de esta entrega](https://github.com/diegomontenegroext-hash/poraca-lp/blob/0c714a2ce49c056794cd930f745d62a929d87a9a/docs/operations/20261104_FUNCTIONAL_CONSOLIDATION.md).

## Completado — no reabrir
1. Admisión productiva existente conservada. Mantenimiento controlado de fecha/hora/cancelación/aplazamiento, ID estable, original + recibo/hash real de colector, HOLD/concurrencia/duplicados/kill switch. No revive histórico.
2. Recibo editorial persistente e idempotente, lectura por vista acotada para el ejecutor y agregado funcional en la misma API de memoria. Dos LINK reales de replay manual, con originales reabiertos y cero altas/cambios, guardados en el último run finalizado; no equivalen a ejecución autónoma.
3. Detección genérica de señales JSON-LD y relectura rotativa de originales admitidos incluso ausentes del índice, dentro del mismo presupuesto y sin duplicar URL.
4. Vistas de continuidad, pérdida de detalle, alternativas potenciales y 82 menciones con rol explícito recuperables del historial. No se declaran recuperaciones ni colaboraciones automáticas.
5. #201 corregida y aceptada con fuente institucional; cuatro créditos nuevos de En Eso Estamos. Tres propuestas prioritarias restantes con causa persistente.
6. Tarea **6ae17dc595d08191b5ec9a4ef0dcaa30** actualizada; horarios intactos, máximo ocho asuntos y tres escrituras de eventos combinadas por ejecución. Sin nuevo motor/cron/workflow/DB.

## Estado factual después del lote
| Indicador | Resultado |
|---|---:|
| Canónicos / futuros confirmed+scheduled | 169 / 34, sin nuevos eventos en este lote |
| Entidades / approved_public | 147 / 93 |
| Relaciones / accepted | 200 / 181 |
| Afirmaciones accepted | 394 → 399 |
| Propuestas prioritarias pendientes | 4 → 3 |
| Créditos nuevos del lote | 4, adicionales a los 23 anteriores |
| Fuentes sin detalle reciente del inventario | 28; no son 28 espacios cerrados |
| Menciones explícitas candidatas con rol/original | 82; no personas aprobadas |
| IICS histórico | 5,8, sin recalcular |

Validación: 463 pruebas Python locales PASS, una omitida; SQL con rollback positivo/negativo/concurrencia/idempotencia y roles limitados reales; build canónico Vercel PASS, 66 archivos/59 scripts. HTTP autenticado 200 con schema correcto del indicador, 93 entidades de memoria y descripción corregida visible en directorio. SSO all y noindex/no-store comprobados. No navegador/Chromium/QA visual ni campaña de navegación.

## Únicos pendientes comprobables, por dueño
1. **#10 — autonomía ordinaria y cambios reales:** primera corrida con nuevo Radar + functional_v1 y recibo editorial_v1, continuidad 3/7 días y un cambio de programación real conservando mismo ID hasta API. El replay manual y las fixtures no acreditan autonomía sostenida. No esperar esta observación para bloquear otros trabajos ni lanzar FULL artificial.
2. **#35 — conocimiento/cobertura:** #33/#80/#145 retenidas con causa. Fuentes/circuitos con pérdida efectiva de detalle requieren recuperación por original verificable; las alternativas son pistas, no autorreparación demostrada. Identidades, prosa y colaboraciones ambiguas siguen bajo revisión editorial, sin cuotas.
3. **#30 — certificación de experiencia a cargo de Chat:** navegación protegida, cuatro intenciones, vistas 390/768/1440 y comparación Babasónicos; comprobar recomendaciones y cambios con evidencia real, sin confundir HTTP con UI.
4. **#32 — medios P2:** fotografías auténticas existentes en cola. No bloquean cadena ni se reabrieron búsquedas repetidas.

#28 recibos sigue cerrado. No quedan pendientes de reimplementar writer, reconstruir Neon, reactivar Motor/Puente, crear un orquestador o repetir las seis identidades/23 créditos anteriores. La autonomía total no se declara cerrada.

## Hito siguiente · Certificación de descubrimiento real (Chat, 04/11/2026)

**Corte de pruebas en lectura, sin despliegues ni Actions ni ediciones en Neon.** IICS v1 **5,8 = 29/50 PASS**, histórica del 03/11; no se acreditaron puertas adicionales por pruebas redundantes de A1/A2/A3. La rúbrica conserva 9 FAIL y 12 NOT_CHECKED y exige nueva ejecución observada o evidencia humana según cada puerta. QA Chromium con último SHA sigue pendiente aunque U4/O5 estén PASS históricos en SHA anterior.

Pruebas con API privada de Vercel 200 y Neon operacional 04/11: **164 eventos API; 34 futuros confirmed+scheduled; 34/34 con original primario y placeId público; 8 categorías, 16 sedes nominales, 13 identidades de sede; 46 pistas futuras RADAR_UNVERIFIED con 43/46 horas y 46/46 sedes+URLs; 0 promoción automática.** Compresión por escena: Casa Metro 13/34 y Freezer 10/34 (distintas funciones, no duplicados). El selector v1 reproducido con corte local 04/11 18:31 entrega **6 categorías y 6 sedes en 6 tarjetas**, pero **0/6 con razón editorial cultural propia** en campo why; la API 0/34 entrega why/editorialHighlight (sí entrega descripciones de los 34). Esto es simulación determinista del algoritmo del repositorio sobre datos del API, NO DOM real.

**Próximo hito P0 = H1 utilidad de descubrimiento (sin otra arquitectura)**: (a) certificar recorrido protegido Salir/Explorar/Participar y cuatro perfiles en 390/768/1440; (b) seis primeras propuestas actuales distintas, con enlace original, explicación cultural basada en fuente y continuidad hacia escenas aun sin eventos; (c) mini lote editorial de observaciones ya encontradas, conciliando sesiones, duplicados y contradicciones sin aprobar por cuota; (d) reevaluar IICS v1 SOLO si se cierra algún gate con criterio original; (e) autonomía ordinaria en ranuras naturales y revisiones reales, no FULL artificial. Fuente de resultados #30 y ejemplos #35. **No inventar una nota 8–9 sin esos cierres.**


## Giro de producto — medir utilidad cultural, no cuotas de eventos (04/11)

Diagnóstico tras tres lotes grandes de Work: las capacidades y controles de seguridad mejoraron mucho, pero **IICS v1 sigue 5,8/10 (29 PASS/50)** porque su rúbrica histórica exige gates independientes de entregas técnicas, usos sociales reales o estabilidad temporal. **No cambiar ni subir retrospectivamente v1.** Dos criterios v1 muestran desajuste frente al objetivo editorial acordado: `S4` exige eventos futuros en vino/talleres/deporte y `A4` cuotas de tres funciones por escena en 15 días. Para vinos, yoga, arte, cerámica y talleres, interesa primero **encontrar y comprender espacios, prácticas, ciclos y eventos excepcionales**, no inventar horarios de clases o forzar una oferta diaria. Mantener esas puertas como histórico v1; no perseguirlas artificialmente para ganar nota.

**Hito inmediato H2 — Descubrimiento cultural que sirve** (antes de cualquier nuevo Work):
1. Fuentes rectoras: Luty debe producir señales de interés realmente LEÍDAS o quedar explícitamente BLOQUEADA; no aceptar checks `ok` sin escaneo del perfil como cobertura cultural. Tarea Radar existente actualizada sin variar horarios, permisos, presupuestos, cron ni Actions para controlar reel exacto `DfVEIVTSTGu` con cooldown.
2. Cinco casos concretos de otra publicación accesible de Luty 11/10 (La Plata Muerde, Bocanada aniversario, festival pizza, patio Dardo Rocha, MIGA). Corte 04/11: **1/5 tiene listing Radar, 0/5 figura en web/API**. Dos con respaldo público externo inicial (Hipódromo/0221/Pinta). Ver detalles en #35. No publicar sin original exacto y validación por writer limitado.
3. Evaluación de producto: en la home seis tarjetas con 6 disciplinas/6 sedes simuladas, pero sin razón cultural particular en `why`; navegar en móvil/desktop, ver lugar→circuito→organizador→fuente, y mantener acceso a espacios sin eventos futuros. #30.
4. **Tablero complementario de utilidad** (NO reemplaza IICS v1): cobertura de 5 referencias editoriales **0/5 en API**; casos triados con evidencia **0/5 cerrados**; razones culturales particulares **0/6 en selector**; 34/34 futuros tienen fuente primaria; prueba humana REAL pendiente. Las metas deben avanzar por hechos documentados, no por nuevos documentos, código, comparativas inadecuadas o porcentajes de clases inventados.
5. No abrir más lotes generales de Work ni hacer otra ronda de 463 pruebas sin cambios. Siguiente mejora a implementar: rescate editorial del lote Luty + UX visible sustentada en hechos. Una sola QA integral por lote, sin nuevas ramas/Actions si basta lectura. IICS se recalcula únicamente cuando se cierre algún gate según versión original, y el tablero de utilidad se actualiza en paralelo.

**Punto de decisión:** si los cinco casos no están detectados, el problema prioritario es cobertura de las referencias relevantes; si están detectados pero no mostrados, el problema es conciliación editorial / presentación. Ambos se miden por separado.


## poraca-lp #35

# Conocimiento cultural — consolidado por evidencia; tres propuestas prioritarias retenidas

[Entrega previa](https://github.com/diegomontenegroext-hash/poraca-lp/blob/main/docs/qa/20261104_EVOLUCION_INTEGRAL_PRODUCTO.md) · [consolidación actual](https://github.com/diegomontenegroext-hash/poraca-lp/blob/0a581ae522cb4a1cd46922c6ef4974db27e7bbd5/docs/operations/20261104_FUNCTIONAL_CONSOLIDATION.md).

## Completado
- Se conservan las 13 aceptaciones, seis identidades, 23 créditos y cinco vínculos del lote anterior; no se contabilizan como nuevos aquí. Entidades 147 / 93 públicas; relaciones 200 / 181 accepted.
- **#201 En Eso Estamos resuelta:** descripción corregida y aceptada con fuente institucional, homepage y página de infraestructura. Cocina de Ideas está documentada en su historia; el nombre Tomasa Mouras no se sostuvo. Se mantienen historia/infraestructura separadas de oferta actual. Valor previo y fundamento en review_log.
- **Cuatro créditos nuevos**, fuente propia: Juan Recchia Paez/Gisela Nomdedeu en programación; Damián Le Moal/Celeste Lucca en comunicación. No se afirman cargos actuales ni se crean identidades personales. Créditos de los dos lotes: 23+4. Afirmaciones accepted 394→399.
- Vista **poraca_knowledge_delta_queue_v1** recupera **82 menciones explícitas con rol y original** ya almacenadas en Radar, cruzadas por nombre exacto con identidad pública cuando existe. No son 82 personas nuevas ni colaboraciones aprobadas.
- Continuidad y recuperación persistentes identifican 28 fuentes sin detalle reciente en el corte inicial y proponen hasta tres fuentes de otro dominio del mismo circuito. Son pistas, no recuperación demostrada ni cierre de espacios.

## Tres propuestas prioritarias que permanecen
| ID | Campo | Bloqueo conservado en review_log |
|---|---|---|
| 33 | Teatro Argentino / primary_topic | Original acredita pluralidad lírica, musical y coreográfica, no tema dominante teatro |
| 80 | Pura Vida / primary_experience | Perfil primario no accesible para relectura independiente en esta intervención |
| 145 | En Eso Estamos / primary_topic | Historia propia transdisciplinar; no demuestra artes como tema dominante |

Cuatro pendientes anteriores→una resuelta+tres retenidas. Esto no borra las propuestas históricas no priorizadas. Nuevas identidades, prosa y colaboraciones siguen bajo criterio editorial; no una cuota por circuito ni promoción automática de microperfiles. La cola de créditos es una herramienta para investigar por delta, no 82 tareas obligatorias.

Pendientes comprobables: estos tres campos si aparece evidencia suficiente; recuperar fuentes/subcircuitos efectivamente sin detalle; validar uso real de conocimiento en recomendaciones con Chat (#30). #32 medios P2 conserva su cola, sin reabrir búsquedas repetidas. IICS 5,8 histórico.

## Auditoría de continuidad de fuentes — Chat 04/11/2026

Lectura real de `poraca_functional_status_v1()`, `poraca_source_continuity_v1` y `poraca_coverage_recovery_v1` (Neon operacional, **SELECT**, sin cambiar colector):
- Inventario automático 65 fuentes; estados en el universo de inventario: **21 evidencia de detalle reciente**, **28 sin detalle en siete días**, **16 con detalle pero sin nueva observación fechada en 30 días**. Otras 167 no son de adquisición automática; **no equiparar su ausencia a falla ni reclasificarlas masivamente**.
- **Vinos: 2/2 sin evidencia de detalle reciente**. `Casa Dionisio — actividades y vinos` = index_only:200; `Feria Catar V / Passline` = ok:200 pero sin detalle registrado. Para ambas, `potential_alternatives=[]`. No hay sustituto automático demostrado en ese circuito.
- **Yoga: 2/2 sin detalle reciente**, ambas index_only:200 (Casa Yogi Villa Elisa, Koshasyoga); alternativas vacías. Priorizar **espacios y oferta editorial**, no horarios de clases ni llenar agenda artificialmente.
- **Arte y cultura: 9/13 fuentes reclaman recuperación** según indicador. Algunos originales de Freezer están en agenda canónica (10 anuncios futuros), por lo que una marca `no_detail_evidence_7d` es una brecha de adquisición de esa fuente, no negación de los eventos existentes ni prueba de cierre.
- La API viva tiene **34 futuros confirmados, 8 categorías, 16 sedes**, pero 13 vinculados con Casa Metro y 10 con Freezer. No modificar selección para ocultarlo; mejorar fuentes originales y lectura transversal de circuitos, especialmente vino/fiestas/arte/autogestivo.

**Próximas acciones de impacto, sin nueva arquitectura:** (1) reconstruir circuito vinos desde organizadores/lugares/enlaces que aparecen en historial Dionisio y Catar, verificar originales vigentes y enriquecer identidades sin crear sesiones ficticias; (2) identificar y corroborar espacios de yoga y talleres especiales como entidades/actividades no fechadas; (3) auditar 9 fuentes de arte por falta de lectura detallada y priorizar nuevos originales, evitando duplicar Centro de Arte/Freezer; (4) mantener vínculos/propuestas ambiguas en HOLD con causa hasta evidencia primaria. Estas tareas son editoriales/de cobertura; **no están ejecutadas** por el presente read-only.


## Muestra editorial de 46 candidatos futuros — 04/11/2026

El feed Vercel expone **46/46 pistas RADAR_UNVERIFIED futuras con URL y sede; 43/46 con hora**, 0 publicationApproved. Pueden esconder sesiones válidas, repeticiones o productos auxiliares. Muestra en originales web (sin aprobar/escribir):
- **Las Hijas**, Teatro Metro, domingo 08/11: originales 100958 a **19:30** y 101000 a **21:30** = **dos sesiones reales distintas**, NO duplicar por título/día/sede ni colapsar ambas. https://www.teatrometrolp.com.ar/entrada/las-hijas-100958 y https://www.teatrometrolp.com.ar/entrada/las-hijas-101000
- **Lisandro Aristimuño – Experiencia Coral**, Teatro Metro, 23/11 **20:00**, presente en originales de Teatro Metro y Casa Metro = **una función, dos vías originales**, candidata a LINK/de-duplicación editorial; no dos canónicos. https://www.teatrometrolp.com.ar/entrada/lisandro-aristimuno-experiencia-coral-100959 y https://casametro.com.ar/evento/lisandro-aristimuno-experiencia-coral/
- **Julián Hernández**, 27/11: fuente Casa Metro anuncia **20:00**, cartelera Metro anuncia **21:00**. **HOLD** hasta corroboración de hora definitiva, no aceptar ni corregir canónico por intuición. https://casametro.com.ar/evento/julian-hernandez-moscoso/ y https://www.teatrometrolp.com.ar/entrada/julian-hernandez-moscoso-100941
- **Pan con Manteca**, 21/11, su **MEET & GREET** consta como producto adicional condicionado a entrada general: no aprobar como segunda función. https://casametro.com.ar/evento/meet-greet-pan-con-manteca-con-augusto-alonso-y-frankillo/
- **Bailó toda la noche, tomó agua fría y se murió**, 15/11 **19:00**, original Casa Metro disponible y pista visible; candidata a expediente editorial, no publicación automática. https://casametro.com.ar/evento/bailo-toda-la-noche-tomo-agua-fria-y-se-murio/

**Cuello de botella comprobable:** adquisición de originales produce candidatos; falta decisión editorial individual comprobable y exposición canónica. Próxima prueba: pequeño lote autorizado de revisión, medir `leads revisadas -> LINK/ACCEPT/HOLD -> API SAME-ID`, sin cupo de aprobaciones ni invasión de la agenda. Foco vino/yoga/arte fuentes no productivas continúa por separado.


## Luty: muestra de cobertura de 5 propuestas — 04/11/2026

**Auditoría read-only del criterio cultural principal, no ensayo de precisión sobre toda la ciudad.** Reel aportado por el usuario: https://www.instagram.com/reel/DfVEIVTSTGu/ — **NO DETECTADO** en las capas consultadas, **NO LEÍDO** (Instagram no accesible; ningún contenido inferido). Cuenta `rd-ig-lutitravelguide` habilitada como `discover_only`, priority=50. Seis `radar_definitivo.source_checks` con status `ok` / http 200 pero `error_type=EXACT_PERMALINK_ONLY_PROFILE_NOT_SCANNED`, links_found=0 en las seis y last_checked_at de la fuente NULL. Esto no acredita lectura del perfil ni del reel. Checkpoints de 24/10 y 26/10 registran lecturas bloqueadas o resultados secundarios históricos. No incrementar métricas de cobertura por esos checks.

**Control positivo:** caption público de OTRA publicación de Luty del 11/10/2026 (https://imginn.com/p/DeXYqWISZod/) ofrece cinco propuestas futuras al 04/11: (1) La Plata Muerde 07/11 Hipódromo; (2) Bocanada aniversario 07/11 Galpón de las Artes; (3) Festival de Pizza Platense 12/11 Estación Provincial/Ciudad de Gatos; (4) patio gastronómico Gran Premio Dardo Rocha 19/11 Hipódromo; (5) MIGA Merienda 23/11 Hipódromo. Verificación SQL por títulos de eventos, observaciones y listings más feed `/api/agenda` (164 eventos, 46 discoveries, 16 secondary): **solo Bocanada** figura como listing Radar `observed_unverified`; **0/5 en feed web de eventos o pistas**. La obra de teatro *Muerde* del 01/11 en Sala 420 es OTRO evento, no el festival gastronómico. No confundirlos.

Dos oportunidades ya cuentan con fuentes externas verificables: comunicado del Hipódromo https://www.hipodromolaplata.gba.gov.ar/h/Publica/sliderNota/sliderP.php?dato=2260&tipo=Eventos menciona La Plata Muerde 07/11 y MIGA 23/11, sin atestación completa de sus horarios de apertura; 0221 confirma detalles La Plata Muerde https://www.0221.com.ar/la-plata/vuelve-el-festival-hamburguesas-al-hipodromo-la-plata-y-los-visitantes-elegira-una-las-ganadoras-n134806 y Pinta ofrece MIGA https://pintamagazine.com/lo-que-viene/miga-el-primer-festival-platense-dedicado-a-la-merienda/ . Aún **no** son canónicos ni se habilitan altas sin original exacto y admisión controlada.

**Acción P0 con máxima rentabilidad cultural:** investigar **Muerde y MIGA primero** desde promotor/venue/ticketera originales; restaurar prueba y contexto de las otras tres propuestas. Resolver 5 expedientes con resultado claro: espacio/ciclo documentado, evento apto, fecha no acreditada o HOLD con motivo. No transformar clase/actividad habitual en agenda artificial, no exigir cuatro disciplinas por semana, no publicar 5 por cuota. Indicador de calidad para esta muestra: 1/5 pistas presentes en Radar, 0/5 mostradas en API, cierre editorial 0/5; objetivo real es **resolver documentalmente los cinco** y publicar solo los que cumplan admisión existente. Mantener esta muestra sin sustituir casos para medir avance.

