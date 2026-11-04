-- Operational Radar staging only: no new table/service/cron/permissions.
-- Must be applied BEFORE deploying code that references the column.
-- Does not touch public.radar_agenda_events, public identity or privileges.
ALTER TABLE radar_definitivo.listing_occurrences
 ADD COLUMN IF NOT EXISTS last_original_read_receipt jsonb;
COMMENT ON COLUMN radar_definitivo.listing_occurrences.last_original_read_receipt
 IS 'Collector-provided digest of a directly opened original page for this exact listing. NOT independent editorial verification or publication approval. Time may be null.';
