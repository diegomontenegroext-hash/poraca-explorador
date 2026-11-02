-- POR ACA · clasificación editorial de fuentes (NO eventos) · 01/11/2026.
-- Una sola operación de metadatos con fuente original examinada; evita
-- castigar al inventario por cuatro circuitos NULL históricos.
-- En una FULL futura se volverá a medir rendimiento por circuito.
-- No crea funciones, no asigna género a eventos, no cambia cron ni monitoreo.
-- Laura Gan: sitio original y biografía cerámica/clases de taller.
-- GASAV: sede oficial de deportes náuticos (Punta Lara).
-- Forma y Sonido: fuente histórica arte sonoro 888 Casa (abril 2023).
-- La Compostera: cooperativa gastronómica y actividad comunitaria; enlace
-- documental ESSApp, no evidencia de cartelera fechada actual.
DO $classify$
DECLARE n_pre integer; n_changed integer;
BEGIN
 SELECT count(*)::int INTO n_pre
 FROM radar_definitivo.sources s
 WHERE s.circuit IS NULL AND
 ((s.source_id='rd-web-1eaeb12c' AND s.url='https://lauragan.com.ar/')
  OR (s.source_id='rd-web-c89fab31' AND s.url='https://gasav.com.ar/')
  OR (s.source_id='rd-web-e06ff3c8' AND s.url='https://formaysonido.org/ma23-radio1.html')
  OR (s.source_id='rd-web-f6f10f2c' AND s.url='https://www.essapp.coop/cooperativa-la-compostera-ltda/sede-cooperativa-la-compostera-ltda'));
 IF n_pre NOT IN (0,4) THEN
   RAISE EXCEPTION 'PORACA_UNCLASSIFIED_SOURCE_COHORT_UNEXPECTED_%',n_pre
   USING ERRCODE='check_violation';
 END IF;
 UPDATE radar_definitivo.sources s SET circuit=CASE s.source_id
   WHEN 'rd-web-1eaeb12c' THEN 'talleres'
   WHEN 'rd-web-c89fab31' THEN 'deportes_nauticos'
   WHEN 'rd-web-e06ff3c8' THEN 'arte_y_cultura'
   WHEN 'rd-web-f6f10f2c' THEN 'gastronomia'
   ELSE s.circuit END
 WHERE s.circuit IS NULL AND
 ((s.source_id='rd-web-1eaeb12c' AND s.url='https://lauragan.com.ar/')
  OR (s.source_id='rd-web-c89fab31' AND s.url='https://gasav.com.ar/')
  OR (s.source_id='rd-web-e06ff3c8' AND s.url='https://formaysonido.org/ma23-radio1.html')
  OR (s.source_id='rd-web-f6f10f2c' AND s.url='https://www.essapp.coop/cooperativa-la-compostera-ltda/sede-cooperativa-la-compostera-ltda'));
 GET DIAGNOSTICS n_changed=ROW_COUNT;
 IF n_changed<>n_pre THEN
   RAISE EXCEPTION 'PORACA_SOURCE_CLASSIFICATION_MISMATCH_%_%',n_pre,n_changed
   USING ERRCODE='check_violation';
 END IF;
END $classify$;

SELECT s.source_id,s.circuit,s.monitoring_mode,s.source_role,
       s.url
FROM radar_definitivo.sources s
WHERE s.source_id IN ('rd-web-1eaeb12c','rd-web-c89fab31',
                      'rd-web-e06ff3c8','rd-web-f6f10f2c')
ORDER BY s.source_id;