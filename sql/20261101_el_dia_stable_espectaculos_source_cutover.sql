-- POR ACA / EL DIA stable section root / QA then PROD / 2026-11-01
-- Root cause: /ttags/espectaculos missed the most recent daily agenda.
-- /espectaculos is stable, publisher-owned and links the current
-- /espectaculos/agenda-septimo-dia_<timestamp> article.
-- Keep the SAME source_id for source receipts and provenance.
-- NO canonical/admission/venue/observation writes. Idempotent (0 on replay).
-- Execute in QA branch br-icy-night-b4larkc3 first, production only after
-- read-only test suite and branch-specific preflight. No additional Radar jobs.
UPDATE radar_definitivo.sources AS s
SET url='https://www.eldia.com/espectaculos'
WHERE s.source_id='rd-web-1ee7792f'
 AND s.name='El Día — Espectáculos'
 AND s.source_role='local_press'
 AND s.monitoring_mode='fetch'
 AND s.enabled IS TRUE
 AND s.url='https://www.eldia.com/ttags/espectaculos'
 AND current_setting('neon.project_id',true)='frosty-union-52906378'
 AND current_setting('neon.branch_id',true)
     IN ('br-icy-night-b4larkc3','br-mute-recipe-b4odj2bl')
 AND NOT EXISTS(SELECT 1 FROM radar_definitivo.runs r
     WHERE r.finished_at IS NULL AND r.started_at>now()-interval '3 hours')
 AND NOT EXISTS(SELECT 1 FROM radar_definitivo.sources other
     WHERE other.source_id<>s.source_id
       AND trim(trailing '/' FROM lower(other.url))='https://www.eldia.com/espectaculos')
RETURNING source_id,name,url,source_role,monitoring_mode,enabled;
-- Exact isolated rollback if ever needed:
-- UPDATE radar_definitivo.sources SET url='https://www.eldia.com/ttags/espectaculos'
-- WHERE source_id='rd-web-1ee7792f' AND url='https://www.eldia.com/espectaculos';
-- Do NOT change source_id: historical run receipts key by that ID.
