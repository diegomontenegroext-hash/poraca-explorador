-- POR ACÁ / rollback exacto de la vista de procedencia previa a V2.
-- Solo vista, ninguna fila de datos; usar únicamente ante regresión verificada.
-- La estructura anterior exige sourceRole='first_party' y no reconoce
-- por sí sola la ticketera o institución como prueba por campo.
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
          WHERE (x.value ->> 'url'::text) = e.source_url AND (x.value ->> 'sourceRole'::text) = 'first_party'::text)) AS source_url_primary_correlated,
    (EXISTS ( SELECT 1
           FROM jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                    ELSE '[]'::jsonb
                END) x(value)
          WHERE (x.value ->> 'url'::text) = e.source_url AND (x.value ->> 'sourceRole'::text) = 'first_party'::text AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
                   FROM jsonb_array_elements_text(x.value -> 'supports'::text) support(value)
                  WHERE lower(support.value) = ANY (ARRAY['hora'::text, 'time'::text, 'start_time'::text, 'open_start'::text, 'inicio'::text, 'hora_inicio'::text]))))) AS first_party_supports_start,
    (EXISTS ( SELECT 1
           FROM jsonb_array_elements(
                CASE
                    WHEN jsonb_typeof(e.evidence) = 'array'::text THEN e.evidence
                    ELSE '[]'::jsonb
                END) x(value)
          WHERE (x.value ->> 'url'::text) = e.source_url AND (x.value ->> 'sourceRole'::text) = 'first_party'::text AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
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
              WHERE (x.value ->> 'url'::text) = e.source_url AND (x.value ->> 'sourceRole'::text) = 'first_party'::text AND jsonb_typeof(x.value -> 'supports'::text) = 'array'::text AND (EXISTS ( SELECT 1
                       FROM jsonb_array_elements_text(x.value -> 'supports'::text) support(value)
                      WHERE lower(support.value) = ANY (ARRAY['hora'::text, 'time'::text, 'start_time'::text, 'open_start'::text, 'inicio'::text, 'hora_inicio'::text]))))) THEN 'start_supported_by_structured_primary_proof'::text
            ELSE 'start_missing_structured_primary_proof'::text
        END AS start_source_quality,
    'No suponer que fuente primaria sobre fecha o sede prueba por sí sola el horario; los soportes de evidencia son campos independientes'::text AS policy
   FROM radar_agenda_events e
     JOIN poraca_event_knowledge_integrated_v1 q ON q.event_key = e.event_key;
