# Acta única de madurez — Radar 2 — 07/11/2026 UTC

**Decisión: GO condicionado para descubrimiento privado con revisión editorial. NO GO para certificar inteligencia cultural autónoma 10/10 ni precisión/recuperación editorial 95%/90%.** Se corrigieron y publicaron capacidades internas reales. Persisten límites internos medidos, separados de credenciales y continuidad externa.

Parser final: **caption-v2.2**, código de extracción en `main`, implementación `6be3a87af9118f4dee6e8e0a9f5b6fbc6c176039`. El commit que contiene esta acta agrega evidencia y endurece el manejo de redirecciones del journal; no vuelve a adquirir fuentes. API existente `de5ab69`, producción privada **dpl_C5JjCbBCtHXZYfaRfFgGNabn4piG READY**, SSO `all` comprobado nuevamente. No se necesitó un despliegue web: la API consume directamente las vistas actualizadas.

[Backlog maestro vigente](https://github.com/diegomontenegroext-hash/poraca-lp/issues/16). No se cierra el maestro ni se cierran las obligaciones editoriales pendientes.

## 1. Defectos corregidos

- Eliminado el descarte de una actividad por compartir fecha con otra. Se segmentan múltiples horarios, rangos y medianoche; un descuento o límite de ingreso no se convierte en inicio.
- Se preservan obra, evento agrupador y funciones con IDs trazables. Las funciones de una publicación con título/sede coincidentes comparten evento/obra. Una URL explícita `/obra/` también permite esa agrupación; no se fusionan homónimos entre fuentes sin evidencia.
- Las sinopsis que mencionan el pasado ya no ocultan automáticamente un anuncio futuro. Se reconocen cancelaciones, publicaciones comerciales relativas y reglas recurrentes sin expandir fechas inexistentes.
- Los programas de festival sin fecha civil mantienen componentes pendientes. Los programas narrativos conservan sus fragmentos, sin asignar el inicio general a cada participante.
- Hay spans exactos sobre el texto original, incluso con horarios Unicode estilizados; créditos explícitos y ciclos documentados, sin convertir menciones en identidades verificadas.
- Reprocesamiento versionado, retiro de interpretaciones anteriores de la vista activa y mantenimiento de originales/historial. Se evita conciliar un resultado nuevo contra la interpretación antigua que va a retirarse.
- Corregida la exclusión de cuentas de control cuando les toca una selección incremental. Se añaden elegibilidad observada, productividad/cooldown y descubrimiento acotado de cuentas.
- Journal por documento y protección de credenciales en redirecciones de artifacts; etapas de postprocesamiento fallidas quedan diferenciadas del cierre exitoso del replay.

## 2. Extracción: evidencia antes/después y calidad

| Conjunto/medida | Antes | Después | Interpretación correcta |
|---|---:|---:|---|
| Guajira, anuncio DfQOVDWmRMd | 6 actividades/fechas | 10 actividades | Cuatro anuncios de medianoche preservados; su día civil sigue pendiente. |
| Cine, DfartNwlwom | 0 ocurrencias | 3 | Nuestra Tierra, María Antonieta y Las vírgenes suicidas. Medianoche sin fecha/hora civil inventadas. |
| Reunión de padres | 3 eventos separados | 1 evento/obra con 3 funciones | Lectura SQL y HTTP protegida. |
| 30 originales del cierre anterior, slots de fecha anunciada | 21 TP / 0 FP / 4 FN | 25 TP / 1 FP / 0 FN | Precisión 96,15%, recuperación 100%; NO es exactitud editorial integral y el falso positivo sigue registrado. |
| Primera reserva de 18, fecha+hora por slot, primera pasada | 9 TP / 1 FP / 4 FN | 12 TP / 1 FP / 1 FN | Precisión/recuperación 92,31%. Después se consumió para corregir reglas; no se presenta el resultado posterior como holdout. |
| Reserva final de 20, código congelado 3bba2ae | 5 TP / 2 FP / 8 FN | 8 TP / 1 FP / 5 FN | Precisión 88,89%, recuperación 61,54%. Es el resultado previo a corregir sus fallos; se conserva sin reemplazarlo. |
| Mismos 20 después de correcciones v2.2 | — | 11 TP / 0 FP / 2 FN | 100%/84,62% sobre conjunto ya consumido, NO evaluación independiente. Los dos componentes narrativos están guardados para revisión, sin contarlos como ocurrencias resueltas. |
| Revisión de campos de desarrollo: 10 publicaciones reales | — | 21/21 títulos y valores de sede esperados; 3/3 créditos de facilitadoras; 11 componentes sin fecha conservados | Incluye valores desconocidos correctos. No acredita identidad de sedes ni precisión de actores de todo el corpus. |

Las anotaciones fueron realizadas por el agente. No hubo validación humana independiente. Hay muestras reservadas antes de sus predicciones y casos de distintas cuentas, pero ninguna es una certificación representativa de todas las fuentes de la ciudad. No se usan porcentajes de fechas para certificar títulos, lugares, actores, roles o utilidad editorial completa. Las ocurrencias ambiguas de medianoche se puntúan como slots anunciados; la API mantiene `date/time=null` y conserva `announced_date/announced_time`.

Evidencia: [30 originales](evidence/maturity-original30-before-after-20261107.json), [primera reserva](evidence/maturity-quality-20261107.json), [reserva final y fallos](evidence/maturity-final-evaluation-20261107.json), [campos](evidence/maturity-field-review-20261107.json).

## 3. Identidades y relaciones consolidadas

Se añadieron al ledger 59 nodos observados entre ambas versiones de esta intervención; el total queda en 173 nodos, 170 activos. Son **nombres/roles documentados**, no 59 identidades nuevas verificadas. Hay 322 observaciones de relaciones, 312 activas; varias pueden aportar pruebas al mismo vínculo conceptual, por lo que no se llaman 312 hechos independientes.

Ejemplos verificables: **Ciclo Ardiente**, `part_of_cycle` y sus anuncios en Guajira; **Anna Skrypnyk y Lucía Gamba**, acreditadas como facilitadoras en Salud digestiva; **Josefina Araneda**, acreditada en Neriage. Los alias conservan evidencia y las identidades dudosas siguen pendientes. La segunda pasada v2.2 agregó **cero nodos y cero relaciones**.

## 4. Descubrimiento cultural genuino

Cadena completa comprobada: anuncio local **Nosotras dos** → organizador estructurado **Teatro Espacio 44** → enlace explícito `instagram.com/teatroespacio44` → candidato de fuente → admisión acotada en la rotación → `account:teatroespacio44` consultable en Neon y API HTTP 200.

Original: https://agendalaplata.ar/evento/nosotras-dos-teatro-espacio-44-20261028194056 . También quedó como pista Teatro La Nonna. Son fuentes nuevas para este padrón, no teatros culturalmente desconocidos. No se consultó la cuenta recién admitida para fabricar una elegibilidad: permanece `pending_meta_eligibility`/sin intento.

Se conservan las 123 cuentas originales; padrón actual **124**. Máximo una incorporación por día ART y 200 cuentas en total. La frontera web limita 1500 enlaces y 60 altas por corrida, manteniendo el presupuesto de consultas. Un ciclo nombrado expresamente se representa como tal; **no se inventó ni se certificó un circuito emergente nuevo**.

## 5. Neon y API: lo persistido y comprobado

Relectura final: **847 documentos, 893 versiones documentales, 1200 propuestas y 4110 versiones de propuestas**. Ningún original actual carece de su versión. No hubo reset, borrado de originales, nueva arquitectura ni escritura en agenda aprobada.

v2.2 procesó **499 originales / 607 propuestas**; retiró 15 interpretaciones v2.1 adicionales de la vista activa. La segunda pasada mantuvo 1200 propuestas, retiró cero interpretaciones y agregó cero nodos/relaciones. Las propuestas anteriores continúan en tablas/versiones. Integridad contractual: **0 referencias colgantes**.

Hay 236 candidatos futuros fechados en la vista activa y 171 con fecha/hora/sede; 9 de estos últimos provienen de captions v2.2. Son cifras de completitud de candidatos, no eventos aprobados ni garantía de ausencia de duplicados semánticos.

HTTP protegido 200 comprobado para obra/funciones, medianoche, ciclo, relación y nueva cuenta. Una lectura posterior devuelve un componente narrativo **v2.2** con fecha/hora desconocidas. Cabeceras privadas/noindex conservadas. La aplicación puede consumir estos recursos mediante la API existente; no se certifica una experiencia visual completa de grafo/circuitos.

Evidencia: [API](evidence/maturity-api-20261107.json), [API final v2.2](evidence/maturity-v22-api-20261107.json), [inventario](evidence/maturity-final-inventory-20261107.json), [integridad](evidence/maturity-final-integrity-20261107.json), [replay final](evidence/maturity-v22-production-20261107.json), [segunda pasada](evidence/maturity-v22-idempotence-20261107.json).

## 6. Autonomía de las tres corridas

Se conserva **un workflow**, FULL 05:27 y dos incrementales 13:27/20:27 ART; misma adquisición oficial, rotación CAS/lease, roles restringidos y API. Las mejoras se aplicarán a las corridas ordinarias desde `main`.

[Actions 42330359195 SUCCESS](https://github.com/diegomontenegroext-hash/poraca-explorador/actions/runs/42330359195) ejecutó dos relecturas reales de originales y salud Meta: **cero adquisiciones de publicaciones**. El parche v2.2 se verificó y reprocesó después con el mismo escritor limitado. No se repitieron tres adquisiciones ni se disparó una FULL para simular continuidad.

La consulta histórica encontró una corrida `radar2-ghdaily-*` anterior, del 06/11, sin modo en su resumen. No demuestra varios días con la configuración final. **Continuidad natural de las tres ventanas con esta versión: todavía no observada.**

## 7. Meta: caducidad comprobada y control

Introspección oficial real: `USER`, válido y con permisos requeridos. Token: **05/01/2027 19:08:08 ART**. Acceso a datos: **04/02/2027 19:39:52 ART**. Los valores no se infieren de una variable manual; `expiry_introspected=true`.

Hay avisos de ≤14 días, caducidad desconocida y credencial inválida; se evita adquirir desde Meta ante invalidez comprobada. No se imprimen tokens ni errores con URLs sensibles. Se conserva procedimiento mínimo de renovación en [el contrato](CONTRACT_V1.md).

**Renovación automática: NO implementada ni certificada.** No se acreditó un flujo de renovación compatible y almacenamiento seguro del reemplazo para la credencial actual. No se aplica el refresh de Instagram Login al flujo Facebook Login/Business Discovery. La documentación oficial de tokens y debug_token devolvió 429 al consultarla; la introspección operativa sí funcionó. La intervención humana permanece necesaria antes del vencimiento.

## 8. Límites internos, externos y editoriales abiertos

**Internos:** componentes de programas narrativos aún sin identidad/ocurrencia resuelta; un falso positivo en la muestra histórica; títulos y roles incompletos fuera de las reglas explícitas; conciliación conservadora entre fuentes y obras homónimas sin resolver globalmente. La selección adaptativa usa señales de productividad y silencio, no una comprensión infalible del valor cultural.

**Editoriales:** no hay validación humana independiente ni prueba 95%/90% suficientemente representativa. Las sedes implícitas, medianoche, roles ambiguos y cancelaciones dudosas requieren revisión. Nada se autoaprueba.

**Externos/operativos:** renovación humana de Meta, elegibilidad de las cuentas restantes y observación natural de varios días. El journal conserva originales ante fallos de SQL y permite recuperar artifacts en el mismo workflow; **el recorrido real caída total de Neon → artifact → siguiente cron todavía no fue ensayado**. Se probó la conservación/replay en disco con fallos simulados y los reintentos acotados. No se promete supervivencia si el runner se pierde antes de subir el artifact o fallan ambos almacenamientos.

## 9. Versión publicada y controles

`main`: parser **caption-v2.2**; contrato v1 ampliado en las vistas existentes, sin nuevos recursos obligatorios ni servicios. API desplegada existente READY/SSO all. **511 pruebas locales ejecutadas, 1 omitida**; las 41 específicas de Radar 2 pasan. Sintaxis Python y YAML comprobadas. El run agrupado de GitHub pasó sus controles v2.1 y replay; los cambios v2.2 pasaron regresiones locales y ejecuciones reales con relectura de producción. No se atribuye la QA de v2.2 al run de GitHub anterior.

La migración de vistas se ensayó en el clon existente `br-calm-queen-b46np7a8` antes de producción. Se comprobaron idempotencia, referencias y agrupación de funciones. No se creó una rama permanente, no se desactivó SSO ni se repitieron adquisiciones de originales disponibles. QA visual no ejecutada en esta intervención.

## 10. Decisión y obligaciones que se cierran

**GO condicionado** para conservar y utilizar el motor privado de descubrimientos, con revisión humana antes de agenda. Se cierran los defectos comprobados de pérdida por fecha compartida, separación de funciones en los casos documentados, introspección de caducidades, reprocesamiento idempotente y exposición de los nuevos datos en API.

**NO GO** para presentarlo como inteligencia cultural autónoma certificada 10/10. Los resultados reservados y los límites internos anteriores impiden ese cierre; no se culpa únicamente a Meta o al tiempo. El backlog maestro queda abierto exclusivamente con esas obligaciones pendientes y la continuidad operativa, sin convertir ejemplos resueltos en una certificación general.
