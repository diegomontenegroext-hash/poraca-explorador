-- Por Acá · Certificación acotada de IDENTIDAD de dos sedes aprobadas.
-- QA branch br-icy-night-b4larkc3 primero, PROD br-mute-recipe-b4odj2bl después.
-- Identidad estable ≠ actividad vigente ≠ publicación de un evento.
-- Nunca UPDATE entidades, eventos, links, lifecycle o last_verified_activity_at.
WITH proposed(entity_id,evidence_url,tier,description) AS (
 VALUES
 ('pasaje-dardo-rocha',
  'https://bafilma.gba.gob.ar/locaciones/la-plata/centro-cultural-pasaje-dardo-rocha',
  'institutional',
  'El Centro Cultural Pasaje Dardo Rocha es un espacio cultural de La Plata ubicado sobre calle 50, entre 6 y 7, en un antiguo edificio ferroviario reconvertido. La fuente institucional acredita su identidad y ubicación, pero no verifica horarios de apertura ni actividades actuales.'),
 ('en-eso-estamos',
  'https://enesoestamosfc.wordpress.com/',
  'first_party',
  'En Eso Estamos se presenta en su propio sitio como una Fábrica Cultural autogestiva de La Plata, con trabajo cultural comunitario y organización cooperativa, ubicada en calle 62 Nº 274. La página acredita identidad histórica y dirección declarada, no demuestra programación ni apertura actual.')
), authorized AS (
 SELECT p.* FROM proposed p
 JOIN public.poraca_knowledge_entities e USING(entity_id)
 WHERE current_database()='neondb'
 AND current_setting('neon.project_id',true)='frosty-union-52906378'
 AND current_setting('neon.branch_id',true) IN (
   'br-icy-night-b4larkc3','br-mute-recipe-b4odj2bl')
 AND e.editorial_state='approved_public'
 AND e.entity_kind='venue'
 AND e.merged_into_id IS NULL
 AND e.lifecycle_state NOT IN ('closed_confirmed','merged_duplicate')
 AND e.official_url LIKE 'https://%'
 AND p.evidence_url LIKE 'https://%'
 AND NOT EXISTS (
  SELECT 1 FROM public.poraca_knowledge_assertions a
  WHERE a.entity_id=e.entity_id AND a.predicate='descripcion'
  AND a.review_state='accepted'
  AND a.evidence_tier IN ('first_party','official','institutional')
 )
), added AS (
 INSERT INTO public.poraca_knowledge_assertions
  (entity_id,predicate,value,evidence_url,evidence_tier,
   evidence_observed_at,reuse_policy,review_state,reviewed_by,reviewed_at)
 SELECT entity_id,'descripcion',
   jsonb_build_object('text',description,
    'scope','identity_only_non_current_activity',
    'evidence_checked_day','2026-11-02',
    'does_not_prove_current_opening',true,
    'does_not_prove_current_events',true,
    'not_full_dossier',true),
   evidence_url,tier,now(),'own_research','accepted',
   'ChatGPT / comprobación directa de fuente institucional o autodescripción primaria · 2026-11-02',
   now()
 FROM authorized
 WHERE (SELECT count(*) FROM authorized)=2
 RETURNING assertion_id,entity_id,predicate,evidence_tier,review_state
)
SELECT * FROM added ORDER BY entity_id;
