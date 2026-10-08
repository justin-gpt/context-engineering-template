# Vector store schemas

Sample schemas that put the canon into a vector store without losing its governance. Each file implements the same metadata contract for a different store; the contract is in `metadata-contract.md` and summarised below. Embedding the canon is optional. Most teams start with the bundle (`export/bundle.json`) injected whole, and add retrieval only when the depth sources (calls, files, CRM notes) make the bundle too large to inject.

## Which store

Pick the store you already run. The metadata is identical everywhere, so the choice is about operations, not retrieval quality.

| Situation | Suggested file | Why |
| --- | --- | --- |
| Already on Supabase | `supabase-pgvector.sql` | Row-level security keyed to the session or the auth token, one SQL function for the agent to call, nothing new to operate. |
| Postgres anywhere (RDS, Aurora, Cloud SQL, AlloyDB, Azure Database for PostgreSQL, a container) | `postgres-pgvector.sql` | Same model with per-tenant database roles, so a client security review can verify isolation at the database layer. |
| Want a managed, serverless index with a hard per-tenant boundary | `pinecone-index.json` | One namespace per tenant; the index scales without a database to run. |
| Azure shop | `azure-ai-search-index.json` | Vector and keyword search in one index; isolation is a service-side filter, or one index per tenant. |
| AWS shop | `opensearch-index.json` or `postgres-pgvector.sql` on Aurora | OpenSearch gives k-NN plus filtered aliases and document-level security; Aurora gives the Postgres model. |
| GCP shop | `bigquery-vector.sql`, or `postgres-pgvector.sql` on AlloyDB, or Vertex AI Vector Search with the same fields as restricts | BigQuery when the canon sits next to warehouse data; AlloyDB when you want Postgres row-level security. |

Two stores can run side by side (one per audience) as long as both carry the full metadata.

## The metadata contract, in one table

Every chunk row, in every store:

| Field | Type | Purpose |
| --- | --- | --- |
| `id` | text | Deterministic `{source_system}:{source_id}#{chunk_index}`; re-ingestion is an upsert |
| `tenant_id` | text | Isolation key: `company`, or the client contract's `client_id` (`CLIENT-001`) |
| `source_system` | enum | `notion` · `markdown` · `confluence` · `crm` · `calls` · `files` |
| `source_id` | text | Page, path or record id in the source system |
| `source_url` | text | The citation returned with every match |
| `canonical_slug` | text, nullable | Contract slug for canon pages; null for depth sources |
| `status` | enum | `grounded` · `draft` · `stub` · `deprecated`, copied from the contract |
| `visibility` | enum | `company_internal` · `client_private` · `client_shared` · `public`, copied from the contract |
| `content_hash` | sha256 hex | Dedupe and change detection |
| `chunk_index` | integer | Position within the source |
| `text` | text | The embedded text, returned with the match |
| `embedding` | vector(1536) | The embedding; change the dimension everywhere at once and re-embed |
| `token_count` | integer | Tokens in `text` |
| `generated_at` | timestamp | When the content last changed (`meta.json.generated_at`) |
| `last_synced_at` | timestamp | The freshness heartbeat (`meta.json.last_synced_at`) |
| `metadata` | JSON | Flat extras; never secrets or personal data |

The enum values are the same strings the contract uses (`schemas/json/context-contract.schema.json`), so a contract change and an index filter can never disagree about what a word means.

## The five rules

1. **Filter every query by `tenant_id` AND `visibility` AND `status`.** All three, every time, set by the retrieval service from the caller's identity and never from the prompt. Similarity ranks the survivors; it never widens the set. Use the store's own isolation (row-level security, namespaces, row access policies, document-level security) as the backstop, and keep the filter anyway.
2. **Audience before embedding.** Never embed a page whose contract `visibility` is more restricted than the index's audience. A client-facing index holds `client_shared` and `public` only; `company_internal` never enters a client index.
3. **Deprecation is deletion.** When a page becomes `deprecated` or leaves the contract, delete its chunks. Do not flag them: a flag is one forgotten `WHERE` clause away from being an answer.
4. **Dedupe by `content_hash`, re-embed on `generated_at`.** An existing hash within the tenant means no new embedding call; a moved `generated_at` on a source means all of its chunks are replaced in one transaction. A run where only `last_synced_at` moved touches no vectors.
5. **Cite `source_url`; store no secrets or personal data.** Every hit returns its URL and the agent puts it after the claim. The index is part of the context layer, where the contract fixes `secrets_in_context_layer: prohibited`; owners are roles, and nothing about a person is embedded.

## Chunking, briefly

Split by heading; 300 to 800 tokens per chunk with 10 to 15 percent overlap; keep the page frontmatter as a prefix in chunk 0; prefix every chunk with the page title and heading path; strip the generated header into the typed columns instead of embedding it. Details in `metadata-contract.md`.

## Files

| File | Contents |
| --- | --- |
| `metadata-contract.md` | The field table with the reason for each field, chunking guidance, ingestion rules, query rules, what never goes in metadata |
| `supabase-pgvector.sql` | Tables, HNSW index, propagation trigger, RLS policies for `service_role` and `authenticated` (session settings or JWT claims), `match_context_chunks`, `context_freshness`, usage notes |
| `postgres-pgvector.sql` | The same model for any Postgres 15+: `context_writer`, per-tenant reader roles mapped in `context_tenant_grants`, a shared `context_app` role scoped per transaction, same function and view |
| `pinecone-index.json` | Serverless index spec, namespace-per-tenant strategy, metadata schema, example upsert, filtered query and delete |
| `azure-ai-search-index.json` | Index definition with an HNSW vector profile and optional semantic configuration, security-trimming note, example document, query and delete |
| `opensearch-index.json` | k-NN mapping (HNSW, cosine), filtered alias per tenant, example document, two query shapes, delete-by-source, freshness aggregation |
| `bigquery-vector.sql` | Tables, `CREATE VECTOR INDEX` with stored columns, row access policies, freshness view, `VECTOR_SEARCH` query and ingestion sketch |

All data in these files is fictional (Acme Analytics, Globex Logistics, Vandelay Industries) and every URL, group and identifier is an `example.com` placeholder.
