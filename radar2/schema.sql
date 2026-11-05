-- Isolated empty acquisition schema. No old data imported, no DROP/DELETE.
CREATE SCHEMA IF NOT EXISTS radar2;
CREATE TABLE IF NOT EXISTS radar2.runs (
 run_id text PRIMARY KEY, finished_at timestamptz NOT NULL, summary jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS radar2.documents (
 url text PRIMARY KEY, source text NOT NULL, sha256 text NOT NULL,
 fetched_at timestamptz NOT NULL, first_seen_at timestamptz NOT NULL DEFAULT now(),
 last_run_id text NOT NULL REFERENCES radar2.runs, payload jsonb NOT NULL
);
CREATE TABLE IF NOT EXISTS radar2.proposals (
 proposal_id text PRIMARY KEY, document_url text NOT NULL REFERENCES radar2.documents,
 title text NOT NULL, event_date date, event_time text, venue text, category text,
 review_state text NOT NULL CHECK (review_state IN ('observado_agenda','investigable','fuente_original','historico','incompleto','contradictorio','actor')),
 first_seen_at timestamptz NOT NULL DEFAULT now(), last_seen_at timestamptz NOT NULL DEFAULT now(),
 last_run_id text NOT NULL REFERENCES radar2.runs, evidence jsonb NOT NULL
);
CREATE VIEW radar2.private_discoveries AS
 SELECT p.proposal_id,p.title,p.event_date,p.event_time,p.venue,p.category,p.review_state,
 p.document_url,d.source,p.first_seen_at,p.last_seen_at,p.evidence
 FROM radar2.proposals p JOIN radar2.documents d ON d.url=p.document_url;
GRANT USAGE ON SCHEMA radar2 TO poraca_radar_limited_prod,poraca_motor_qa;
GRANT SELECT,INSERT,UPDATE ON radar2.runs,radar2.documents,radar2.proposals TO poraca_radar_limited_prod;
GRANT SELECT ON radar2.private_discoveries TO poraca_motor_qa;
-- Existing publication tables and editorial admission remain untouched.
