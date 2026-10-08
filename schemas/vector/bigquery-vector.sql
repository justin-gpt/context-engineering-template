-- =============================================================================================
-- Context layer vector store: BigQuery (GoogleSQL)
-- Implements schemas/vector/metadata-contract.md as two BigQuery tables, a vector index and the
-- VECTOR_SEARCH query the retrieval layer runs.
--
-- Replace PROJECT_ID and REGION. Everything below is fictional sample data and placeholders;
-- Globex Logistics is a fictional client (CLIENT-001).
--
-- When to use this file. Pick BigQuery when the canon is already next to warehouse data you want
-- to join at retrieval time, or when the agent platform you use reads from BigQuery natively.
-- GCP teams who want row-level security with the exact Postgres semantics of the other two SQL
-- files can run postgres-pgvector.sql on AlloyDB or Cloud SQL for PostgreSQL instead, and GCP
-- teams on Vertex AI Vector Search can carry the same metadata fields as restricts.
--
-- Two honest caveats about BigQuery for this workload:
--   1. A table under about 10 MB gets no index population: VECTOR_SEARCH falls back to exact
--      (brute-force) search, which is correct and, for a canon of a few hundred chunks, fast.
--      The index below matters once depth sources (calls, files) are embedded too.
--   2. Row access policies are the hard tenant boundary, but when a table has one, stored columns
--      are ignored and the WHERE in the base subquery becomes a post-filter, so a search can
--      return fewer than top_k rows. The query below handles that by asking for more candidates
--      than it needs. If that trade-off does not suit you, use one table per tenant instead of a
--      row access policy, and keep the query filter (rule 1) either way.
-- =============================================================================================

CREATE SCHEMA IF NOT EXISTS `PROJECT_ID.context_layer`
OPTIONS (
  location = 'REGION',
  description = 'Context layer vector store. Read-only mirror of the canon export; written only by the sync. See schemas/vector/metadata-contract.md.'
);

-- ---------------------------------------------------------------------------------------------
-- 1. context_sources: one row per canonical page or depth source
-- BigQuery has no CHECK constraints, and PRIMARY KEY / FOREIGN KEY are NOT ENFORCED (they inform
-- the optimiser only), so the sync validates enum values and uniqueness before loading.
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `PROJECT_ID.context_layer.context_sources` (
  tenant_id       STRING    NOT NULL OPTIONS (description = 'Isolation key. "company" for the single-company pattern; the client contract client_id (CLIENT-001) for a consultancy, verbatim.'),
  source_system   STRING    NOT NULL OPTIONS (description = 'notion | markdown | confluence | crm | calls | files'),
  source_id       STRING    NOT NULL OPTIONS (description = 'Page id, vault path or record id in the source system.'),
  slug            STRING             OPTIONS (description = 'Contract slug for a canonical page; NULL for depth sources.'),
  title           STRING             OPTIONS (description = 'Display title; agents resolve by slug and id, never by title.'),
  status          STRING    NOT NULL OPTIONS (description = 'grounded | draft | stub | deprecated, copied from the contract. Deprecated sources and their chunks are deleted, not kept.'),
  visibility      STRING    NOT NULL OPTIONS (description = 'company_internal | client_private | client_shared | public, copied from the contract.'),
  url             STRING    NOT NULL OPTIONS (description = 'Citation URL (page_url_base + id).'),
  content_hash    STRING             OPTIONS (description = 'sha256 hex of the exported page.'),
  generated_at    TIMESTAMP NOT NULL OPTIONS (description = 'meta.json generated_at: when the content last changed. A moved value means every chunk of the source is replaced.'),
  last_synced_at  TIMESTAMP NOT NULL OPTIONS (description = 'meta.json last_synced_at: the freshness heartbeat.'),
  metadata        JSON               OPTIONS (description = 'Flat extras (owner role, review cadence, caveat). Never secrets, never personal data.'),
  PRIMARY KEY (tenant_id, source_system, source_id) NOT ENFORCED
)
CLUSTER BY tenant_id, visibility, status
OPTIONS (
  description = 'One row per canonical page or depth source per tenant. Parent of context_chunks.'
);

-- ---------------------------------------------------------------------------------------------
-- 2. context_chunks: the embedded rows (the metadata contract, field for field)
-- Clustered on the three columns every query filters by, so a tenant's chunks are read from a
-- few blocks instead of the whole table. ARRAY columns cannot be declared NOT NULL in BigQuery;
-- the sync guarantees every row has a 1536-element embedding with no NULL elements, which the
-- vector index also requires.
-- ---------------------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS `PROJECT_ID.context_layer.context_chunks` (
  id              STRING    NOT NULL OPTIONS (description = 'Deterministic: {source_system}:{source_id}#{chunk_index}. Re-ingestion is a MERGE on this key.'),
  tenant_id       STRING    NOT NULL OPTIONS (description = 'Isolation key, identical to the parent source. Filtered on every query and by the row access policy.'),
  source_system   STRING    NOT NULL OPTIONS (description = 'notion | markdown | confluence | crm | calls | files'),
  source_id       STRING    NOT NULL OPTIONS (description = 'Page id, vault path or record id; with source_system identifies the source for replace-and-delete.'),
  source_url      STRING    NOT NULL OPTIONS (description = 'The citation returned with every match.'),
  canonical_slug  STRING             OPTIONS (description = 'Contract slug for canonical pages; NULL for depth sources.'),
  status          STRING    NOT NULL OPTIONS (description = 'grounded | draft | stub | deprecated, denormalised from context_sources. Queries default to grounded.'),
  visibility      STRING    NOT NULL OPTIONS (description = 'company_internal | client_private | client_shared | public, denormalised from context_sources.'),
  content_hash    STRING    NOT NULL OPTIONS (description = 'sha256 hex of text. Dedupe lookup before embedding.'),
  chunk_index     INT64     NOT NULL OPTIONS (description = 'Position within the source, from 0. Chunk 0 carries the page frontmatter as a prefix.'),
  text            STRING    NOT NULL OPTIONS (description = 'The exact text the embedding was computed from, including the title and heading-path prefix.'),
  embedding       ARRAY<FLOAT64>     OPTIONS (description = '1536-element embedding. To change dimensions, create a new table and re-embed everything; vectors from two models never share an index.'),
  token_count     INT64              OPTIONS (description = 'Tokens in text under the embedding model tokenizer.'),
  generated_at    TIMESTAMP NOT NULL OPTIONS (description = 'generated_at of the export this chunk came from.'),
  last_synced_at  TIMESTAMP NOT NULL OPTIONS (description = 'The heartbeat: last run that confirmed this chunk current.'),
  metadata        JSON               OPTIONS (description = 'Flat extras: heading_path, title, language. Never secrets, never personal data, never metric values.'),
  PRIMARY KEY (id) NOT ENFORCED,
  FOREIGN KEY (tenant_id, source_system, source_id)
    REFERENCES `PROJECT_ID.context_layer.context_sources` (tenant_id, source_system, source_id) NOT ENFORCED
)
CLUSTER BY tenant_id, visibility, status
OPTIONS (
  description = 'One row per embedded chunk. Every column except embedding and text is governance metadata. See schemas/vector/metadata-contract.md.'
);

-- ---------------------------------------------------------------------------------------------
-- 3. Vector index
-- IVF with cosine distance, matching the other stores in this folder. STORING keeps the three
-- governance columns and the citation fields inside the index so a WHERE on them is a
-- pre-filter (filter first, then search the smaller set) rather than a post-filter. num_lists is
-- a starting point; the docs suggest roughly sqrt(row count). The index is populated only once
-- the table passes about 10 MB; until then VECTOR_SEARCH runs exact search, which is fine.
-- ---------------------------------------------------------------------------------------------
CREATE VECTOR INDEX IF NOT EXISTS context_chunks_embedding_idx
ON `PROJECT_ID.context_layer.context_chunks` (embedding)
STORING (tenant_id, visibility, status, source_url, canonical_slug, text)
OPTIONS (
  index_type = 'IVF',
  distance_type = 'COSINE',
  ivf_options = '{"num_lists": 100}'
);

-- ---------------------------------------------------------------------------------------------
-- 4. Tenant isolation: row access policies (the backstop behind the query filter)
-- One policy per tenant audience, granted to a group, never to individuals. The group name is a
-- placeholder. Remember caveat 2 at the top: with a policy on the table, stored columns are not
-- used and the base-subquery WHERE becomes a post-filter. The sync's service account needs to be
-- granted a policy that sees every row (FILTER USING (TRUE)) or it will load into a table it
-- cannot read back.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE ROW ACCESS POLICY client_001_portal_readers
ON `PROJECT_ID.context_layer.context_chunks`
GRANT TO ('group:client-001-portal-readers@example.com')
FILTER USING (tenant_id = 'CLIENT-001' AND visibility IN ('client_shared', 'public'));

CREATE OR REPLACE ROW ACCESS POLICY client_001_delivery_team
ON `PROJECT_ID.context_layer.context_chunks`
GRANT TO ('group:client-001-delivery-team@example.com')
FILTER USING (tenant_id = 'CLIENT-001' AND visibility IN ('client_private', 'client_shared', 'public'));

CREATE OR REPLACE ROW ACCESS POLICY context_sync_all_rows
ON `PROJECT_ID.context_layer.context_chunks`
GRANT TO ('serviceAccount:context-sync@example.com')
FILTER USING (TRUE);

-- ---------------------------------------------------------------------------------------------
-- 5. Freshness: the heartbeat per tenant
-- Compare sync_age_days with the contract's freshness.stale_after_days before the first query of
-- a run and apply on_stale. A caller who sees no row has no evidence of freshness and should stop.
-- ---------------------------------------------------------------------------------------------
CREATE OR REPLACE VIEW `PROJECT_ID.context_layer.context_freshness`
OPTIONS (description = 'Per-tenant freshness: content_as_of is the generated_at clock (cite it), last_synced_at is the heartbeat.')
AS
SELECT
  tenant_id,
  COUNT(*)                                            AS sources,
  COUNTIF(status = 'grounded')                        AS grounded_sources,
  MAX(generated_at)                                   AS content_as_of,
  MAX(last_synced_at)                                 AS last_synced_at,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(last_synced_at), HOUR) / 24.0 AS sync_age_days
FROM `PROJECT_ID.context_layer.context_sources`
GROUP BY tenant_id;

-- ---------------------------------------------------------------------------------------------
-- 6. The retrieval query
-- Rule 1 in BigQuery terms: tenant_id AND visibility AND status in the base subquery, built by
-- the retrieval service from the caller's identity and passed as parameters, never written by the
-- prompt. @query_embedding is an ARRAY<FLOAT64> parameter with 1536 elements. distance is the
-- cosine distance; similarity = 1 - distance. top_k asks for more candidates than needed so a
-- post-filter (see caveat 2) still leaves enough rows; the outer LIMIT returns the final 8.
-- ---------------------------------------------------------------------------------------------
SELECT
  base.id,
  base.source_url,
  base.canonical_slug,
  base.status,
  base.text,
  1 - distance AS similarity
FROM VECTOR_SEARCH(
  (
    SELECT id, source_url, canonical_slug, status, text, embedding
    FROM `PROJECT_ID.context_layer.context_chunks`
    WHERE tenant_id = @tenant_id                       -- 'CLIENT-001'
      AND visibility IN UNNEST(@visibility_scope)      -- ['client_shared', 'public']
      AND status IN UNNEST(@statuses)                  -- ['grounded']
  ),
  'embedding',
  (SELECT @query_embedding AS embedding),
  top_k => 32,
  distance_type => 'COSINE',
  options => '{"fraction_lists_to_search": 0.05}'
)
WHERE 1 - distance >= 0.75
ORDER BY distance
LIMIT 8;

-- ---------------------------------------------------------------------------------------------
-- 7. Ingestion sketch (run by the sync's service account)
-- Replace a changed source atomically: delete its chunks, then insert the new set, inside one
-- multi-statement transaction so a query never sees old and new together. Dedupe by content_hash
-- within the tenant before calling the embedding model. Deprecation deletes.
-- ---------------------------------------------------------------------------------------------
BEGIN TRANSACTION;

DELETE FROM `PROJECT_ID.context_layer.context_chunks`
WHERE tenant_id = 'CLIENT-001' AND source_system = 'notion' AND source_id = 'p-readme';

MERGE `PROJECT_ID.context_layer.context_sources` AS t
USING (
  SELECT
    'CLIENT-001' AS tenant_id, 'notion' AS source_system, 'p-readme' AS source_id,
    'client_readme' AS slug, 'Client README' AS title, 'grounded' AS status, 'client_shared' AS visibility,
    'https://example.com/hubs/client-001/client_readme' AS url,
    '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08' AS content_hash,
    TIMESTAMP '2026-10-07 02:00:00+00' AS generated_at,
    TIMESTAMP '2026-10-08 02:00:00+00' AS last_synced_at,
    JSON '{"owner_role": "engagement_lead", "review": "quarterly"}' AS metadata
) AS s
ON t.tenant_id = s.tenant_id AND t.source_system = s.source_system AND t.source_id = s.source_id
WHEN MATCHED THEN UPDATE SET
  slug = s.slug, title = s.title, status = s.status, visibility = s.visibility, url = s.url,
  content_hash = s.content_hash, generated_at = s.generated_at, last_synced_at = s.last_synced_at, metadata = s.metadata
WHEN NOT MATCHED THEN INSERT ROW;

INSERT INTO `PROJECT_ID.context_layer.context_chunks`
  (id, tenant_id, source_system, source_id, source_url, canonical_slug, status, visibility,
   content_hash, chunk_index, text, embedding, token_count, generated_at, last_synced_at, metadata)
VALUES
  ('notion:p-readme#0', 'CLIENT-001', 'notion', 'p-readme',
   'https://example.com/hubs/client-001/client_readme', 'client_readme', 'grounded', 'client_shared',
   '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08', 0,
   'Client README > Who we are. Globex Logistics engagement readme, chunk 0 ...',
   @chunk_0_embedding, 412,
   TIMESTAMP '2026-10-07 02:00:00+00', TIMESTAMP '2026-10-08 02:00:00+00',
   JSON '{"heading_path": "Client README > Who we are"}');

COMMIT TRANSACTION;

-- Deprecation is deletion (rule 3): removing the source removes its chunks in the same transaction.
-- BEGIN TRANSACTION;
-- DELETE FROM `PROJECT_ID.context_layer.context_chunks`  WHERE tenant_id = 'CLIENT-001' AND source_system = 'notion' AND source_id = 'p-readme';
-- DELETE FROM `PROJECT_ID.context_layer.context_sources` WHERE tenant_id = 'CLIENT-001' AND source_system = 'notion' AND source_id = 'p-readme';
-- COMMIT TRANSACTION;
