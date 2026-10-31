-- Por Acá 2026-10-31, 05:00 baseline: editorial source-circuit labels only.
-- Source identity classification is NOT classification of every event.
-- Never mutate schedules, URLs, monitoring modes, candidates, canon or approvals.
-- Only sources whose current circuit is NULL are eligible. Idempotent and reversible.
-- Revert ONLY these records, after checking audit context, with:
-- UPDATE radar_definitivo.sources SET circuit=NULL WHERE source_id IN (...)
--   AND circuit=<explicit category assigned here>; do not erase later edits.
WITH labels(source_id,new_circuit) AS (VALUES
  ('rd-web-cine-ecoselect-oct2026','cine'),
  ('rd-web-fcnym-custodio-20261028','ciencia'),
  ('rd-web-4d978198','musica'),
  ('rd-web-dd87b781','musica'),
  ('rd-web-a8a74b0f','musica'),
  ('rd-web-59daab0a','talleres'),
  ('rd-web-67c96d38','arte_y_cultura'),
  ('rd-web-79bed621','yoga'),
  ('rd-web-2f6489bc','arte_y_cultura'),
  ('rd-web-70c42e9c','musica'),
  ('rd-web-3a0f8f67','musica'),
  ('rd-web-e601da0d','general'),
  ('rd-web-4240ca72','teatro_y_musica'),
  ('rd-web-9b9f9b7e','teatro_y_musica'),
  ('rd-web-11166a22','arte_y_cultura'),
  ('rd-web-9a2b7b68','arte_y_cultura'),
  ('rd-web-4e6890ff','general'),
  ('rd-web-043ed064','arte_y_cultura'),
  ('rd-web-b06d22a1','arte_y_cultura'),
  ('rd-web-0307ee20','musica'),
  ('rd-web-cd937166','teatro'),
  ('rd-web-e85f9084','teatro'),
  ('rd-web-3f811bd5','general'),
  ('rd-web-88482c94','arte_y_cultura'),
  ('rd-web-6595ccb6','arte_y_cultura'),
  ('rd-web-d2e02681','musica'),
  ('rd-web-958b89f3','musica'),
  ('rd-web-502a4326','cine'),
  ('rd-web-12ff32cb','festival'),
  ('rd-web-7daf6c20','general'),
  ('rd-web-5dc0c60d','talleres'),
  ('rd-web-233df4b8','general'),
  ('rd-web-7348786a','general'),
  ('rd-web-88f74b19','teatro_y_musica'),
  ('rd-web-5404c6e2','yoga'),
  ('rd-web-3250c205','musica'),
  ('rd-web-2bcebbf3','literatura'),
  ('rd-web-7f5653c9','literatura'),
  ('rd-web-cb1bbd30','cine'),
  ('rd-web-963d62a9','ciencia'),
  ('rd-web-2df929d1','arte_y_cultura'),
  ('rd-web-a5dbea58','arte_y_cultura'),
  ('rd-web-e1a88c63','general')
), changed AS (
 UPDATE radar_definitivo.sources s SET circuit=labels.new_circuit
 FROM labels
 WHERE s.source_id=labels.source_id
   AND s.enabled AND s.monitoring_mode='fetch'
   AND s.circuit IS NULL
   AND NOT EXISTS (SELECT 1 FROM radar_definitivo.runs WHERE status='running')
 RETURNING s.source_id,s.name,s.circuit
)
SELECT (SELECT count(*) FROM changed)::int labelled,
       (SELECT count(*) FROM radar_definitivo.sources WHERE enabled AND monitoring_mode='fetch' AND circuit IS NULL)::int still_uncategorized,
       (SELECT coalesce(jsonb_object_agg(circuit,n),'{}'::jsonb) FROM (
          SELECT circuit,count(*)::int n FROM changed GROUP BY circuit
       ) a) labelled_by_circuit,
       (SELECT count(*) FROM radar_definitivo.runs WHERE status='running')::int active_runs;
