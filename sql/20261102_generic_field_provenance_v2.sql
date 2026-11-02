-- POR ACÁ / EVIDENCIA DE CAMPOS V2 — MIGRACIÓN ADITIVA DE SEMÁNTICA (no de datos).
-- Aplica a la vista de auditoría, preserva exactamente columnas y tipos.
-- Ticketera oficial / institución acreditan hora de FUNCIÓN solo si:
-- URL fuente, título, día, hora y lugar son IGUALES al expediente;
-- supports contiene los 4 campos. No confunde puertas con inicio.
-- sourceRole first_party legacy mantiene su significado original.
-- Nunca convierte verification=to_verify a confirmed, jamás publica.
-- QA Neon br-icy-night-b4larkc3: 144 filas; 105->112 correlacionadas,
-- 88->95 inicio, 97->104 sede. 2 confirmados futuros pasan a
-- structurally_reviewed_needs_independent_publication_gate.
-- Las dos cuarentenas del 07/11 y 18/11 siguen hold_event_confirmation.
-- Negativos verificados: hora distinta, sede distinta, URL distinta,
-- sin support y rol desconocido -> NO aceptados.
CREATE OR REPLACE VIEW public.poraca_event_field_evidence_quality_v1 AS
SELECT e.event_key,
    e.title,
    e.event_date,
    e.event_time,
    e.verification,
    e.source_url,
    q.hosting_entity_id,
    q.is_duplicate_alias,
    (EXISTS ( SELECT 1
           FROM jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                    ELSE '[]'::jsonb
                END) x(value)
          WHERE (x.value ->> 'url'::text) = e.source_url AND ((x.value ->> 'sourceRole'::text) = 'first_party'::text OR ((x.value ->> 'sourceRole'::text) = ANY (ARRAY['first_party_ticketing'::text, 'official_institution'::text])) AND jsonb_typeof(x.value -> 'fieldEvidence'::text) = 'object'::text AND ((x.value -> 'fieldEvidence'::text) ->> 'title'::text) = e.title AND ((x.value -> 'fieldEvidence'::text) ->> 'date'::text) = e.event_date::text AND ((x.value -> 'fieldEvidence'::text) ->> 'time'::text) = e.event_time AND ((x.value -> 'fieldEvidence'::text) ->> 'venue'::text) = e.venue AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (x.value -> 'supports'::text) @> '["title", "date", "time", "venue"]'::jsonb))) AS source_url_primary_correlated,
    (EXISTS ( SELECT 1
           FROM jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                    ELSE '[]'::jsonb
                END) x(value)
          WHERE (x.value ->> 'url'::text) = e.source_url AND ((x.value ->> 'sourceRole'::text) = 'first_party'::text OR ((x.value ->> 'sourceRole'::text) = ANY (ARRAY['first_party_ticketing'::text, 'official_institution'::text])) AND jsonb_typeof(x.value -> 'fieldEvidence'::text) = 'object'::text AND ((x.value -> 'fieldEvidence'::text) ->> 'title'::text) = e.title AND ((x.value -> 'fieldEvidence'::text) ->> 'date'::text) = e.event_date::text AND ((x.value -> 'fieldEvidence'::text) ->> 'time'::text) = e.event_time AND ((x.value -> 'fieldEvidence'::text) ->> 'venue'::text) = e.venue AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (x.value -> 'supports'::text) @> '["title", "date", "time", "venue"]'::jsonb) AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
                   FROM jsonb_array_elements_text(x.value -> 'supports'::text) support(value)
                  WHERE lower(support.value) = ANY (ARRAY['hora'::text, 'time'::text, 'start_time'::text, 'open_start'::text, 'inicio'::text, 'hora_inicio'::text]))))) AS first_party_supports_start,
    (EXISTS ( SELECT 1
           FROM jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                    ELSE '[]'::jsonb
                END) x(value)
          WHERE (x.value ->> 'url'::text) = e.source_url AND ((x.value ->> 'sourceRole'::text) = 'first_party'::text OR ((x.value ->> 'sourceRole'::text) = ANY (ARRAY['first_party_ticketing'::text, 'official_institution'::text])) AND jsonb_typeof(x.value -> 'fieldEvidence'::text) = 'object'::text AND ((x.value -> 'fieldEvidence'::text) ->> 'title'::text) = e.title AND ((x.value -> 'fieldEvidence'::text) ->> 'date'::text) = e.event_date::text AND ((x.value -> 'fieldEvidence'::text) ->> 'time'::text) = e.event_time AND ((x.value -> 'fieldEvidence'::text) ->> 'venue'::text) = e.venue AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (x.value -> 'supports'::text) @> '["title", "date", "time", "venue"]'::jsonb) AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
                   FROM jsonb_array_elements_text(x.value -> 'supports'::text) support(value)
                  WHERE lower(support.value) = ANY (ARRAY['lugar'::text, 'venue'::text, 'place'::text, 'location'::text, 'sede'::text]))))) AS first_party_supports_venue,
        CASE
            WHEN e.event_time IS NULL THEN 'no_clock'::text
            WHEN e.event_time = ANY (ARRAY['00:00'::text, '00:00:00'::text]) THEN 'midnight_requires_civil_day_proof'::text
            WHEN (EXISTS ( SELECT 1
               FROM jsonb_array_elements(
                    CASE
                        WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                        ELSE '[]'::jsonb
                    END) x(value)
              WHERE (x.value ->> 'url'::text) = e.source_url AND ((x.value ->> 'sourceRole'::text) = 'first_party'::text OR ((x.value ->> 'sourceRole'::text) = ANY (ARRAY['first_party_ticketing'::text, 'official_institution'::text])) AND jsonb_typeof(x.value -> 'fieldEvidence'::text) = 'object'::text AND ((x.value -> 'fieldEvidence'::text) ->> 'title'::text) = e.title AND ((x.value -> 'fieldEvidence'::text) ->> 'date'::text) = e.event_date::text AND ((x.value -> 'fieldEvidence'::text) ->> 'time'::text) = e.event_time AND ((x.value -> 'fieldEvidence'::text) ->> 'venue'::text) = e.venue AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (x.value -> 'supports'::text) @> '["title", "date", "time", "venue"]'::jsonb) AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
                       FROM jsonb_array_elements_text(x.value -> 'supports'::text) support(value)
                      WHERE lower(support.value) = ANY (ARRAY['hora'::text, 'time'::text, 'start_time'::text, 'open_start'::text, 'inicio'::text, 'hora_inicio'::text]))))) THEN 'start_supported_by_structured_primary_proof'::text
            ELSE 'start_missing_structured_primary_proof'::text
        END AS start_source_quality,
    'No suponer que fuente primaria sobre fecha o sede prueba por sí sola el horario; los soportes de evidencia son campos independientes'::text AS policy
   FROM radar_agenda_events e
     JOIN poraca_event_knowledge_integrated_v1 q ON q.event_key = e.event_key;

-- Verificar con sql/20261102_event_provenance_readback_READ_ONLY.sql.
