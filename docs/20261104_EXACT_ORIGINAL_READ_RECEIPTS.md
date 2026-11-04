# Exact original-read receipts inside the existing Radar pipeline

The collector already opens official event detail pages. This patch keeps a bounded JSONB receipt on its **existing** `radar_definitivo.listing_occurrences` row without another network request, table, cron, writer, API or branch.

- Receipt: exact opened HTTPS URL, body SHA-256/size, run ID, timestamp, HTTP 200, parser method, tier, source role, and extracted program/date/venue (optional time).
- Only direct HTTP reads where `proof_url` equals the page opened, the registered source is first-party, the parser labels a primary detail, and the URL is not root/index get a receipt.
- Index-only, generic roots, secondary sources, unavailable/permalink not opened, browser-rendered without confirmed HTTP read, old legacy rows and inconsistent fields have **no new receipt**, and cannot become eligible merely because a source check is OK.
- This is a **collector receipt**, not a signature or independent validation. Editorial still checks official identity, reliable source authorization, source retraction/cancellation, exact day/venue, conflicts, duplicates, and the evidence age. The v2 QA writer using fake `checkedAt` remains **OFF** in production. Don't trust a supplied attestation object from Radar as publication permission.
- Old records remain preserved; next ordinary FULL/incremental will populate only actual pages opened, no backfilled fictional proof. Repeated reads overwrite the latest receipt for the same immutable listing key. Browser support is intentionally deferred until it provides verifiable original page receipts.
- QA: `python3 -m unittest discover -s tests -v` includes `tests/test_radar_exact_original_read_receipt.py`. Migration applied separately to QA/production staging before natural scheduled ingest, without grants.

Expected next step: editorial read-only preflight joins receipt `run_id` and exact fields to current staging, and verifies seller/venue/duplicates independently. No automatic publication until audited editor authorization.
