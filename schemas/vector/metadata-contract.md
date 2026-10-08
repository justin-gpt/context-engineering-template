# Vector store metadata contract

When any part of the context layer is embedded for retrieval, every chunk carries the same metadata, whatever the store. The metadata is what makes the index governable: it is how a query is confined to one tenant, how a draft is kept out of an answer, how a deprecated page is removed, and how a reader gets a citation instead of a paraphrase. The embedding is the least important column in the row.

The files beside this one implement the contract for several stores. They differ in syntax, not in fields. `README.md` has the decision guide.

## 1. The chunk row

Every chunk row carries these fields. Names are snake_case and identical in every store so a retrieval layer can be ported by changing the client, not the query.

| Field | Type | Required | Why it exists |
| --- | --- | --- | --- |
| `id` | text, primary key | yes | Stable chunk identity. Deterministic: `{source_system}:{source_id}#{chunk_index}` (the tenant lives in the namespace, schema or row filter). A deterministic id makes re-ingestion an upsert and lets a store that cannot delete by filter delete by id prefix. |
| `tenant_id` | text | yes | The isolation key. `company` for the single-company pattern; the client contract's `client_id` (`CLIENT-001`) for a consultancy, verbatim and case-sensitive. Row-level security, namespaces and every query filter on it. Never derived from a name. |
| `source_system` | text, enum | yes | `notion` · `markdown` · `confluence` · `crm` · `calls` · `files`. Where the chunk came from. Canon pages come from the first three; the rest are depth sources that may be embedded under the same rules but are never canon. |
| `source_id` | text | yes | The page id, file path or record id in the source system. With `source_system` and `tenant_id` it identifies the source; the sync uses it to find and replace every chunk of a changed page. |
| `source_url` | text | yes | The citation. The retrieval layer returns it with every hit and the agent puts it after the claim. A chunk without a URL cannot be cited and should not be embedded. |
| `canonical_slug` | text, nullable | yes (nullable) | The contract slug (`company_readme`) when the chunk belongs to a canonical page; null for depth sources. Lets a query ask for "the positioning page" and lets the sync map contract changes to chunks. |
| `status` | text, enum | yes | `grounded` · `draft` · `stub` · `deprecated`, copied from the contract at export time. Queries default to `grounded`; `deprecated` never reaches a query because deprecated chunks are deleted (rule 3). |
| `visibility` | text, enum | yes | `company_internal` · `client_private` · `client_shared` · `public`, copied from the contract. The second isolation key: a client user's query is confined to `client_shared` and `public`; the delivery team adds `client_private`. |
| `content_hash` | text, sha256 hex (64 chars) | yes | Hash of the chunk text (after the frontmatter prefix is applied). Dedupes identical chunks across runs and tells the ingestion job whether a chunk needs re-embedding. |
| `chunk_index` | integer ≥ 0 | yes | Position of the chunk within its source. Keeps neighbours findable for context expansion and makes `id` deterministic. |
| `text` | text | yes | The chunk content the embedding was computed from, stored so the retrieval layer can show what matched without a second fetch. |
| `embedding` | vector(1536) | yes | The embedding. 1536 dimensions is a common default; change it everywhere at once (see each file) and re-embed the whole index when the model changes, because vectors from two models do not live in the same space. |
| `token_count` | integer | no | Tokens in `text` under the embedding model's tokenizer. Used for prompt budgeting and to audit chunking. |
| `generated_at` | timestamp (UTC) | yes | `meta.json.generated_at` of the export the chunk came from: when the content last changed. A chunk is stale and must be re-embedded when the source's `generated_at` moves. |
| `last_synced_at` | timestamp (UTC) | yes | `meta.json.last_synced_at` of the run that confirmed the chunk current: the freshness heartbeat. Per-tenant `max(last_synced_at)` feeds the freshness view and the stale alert. |
| `metadata` | JSON object | no | Extras that do not belong in a typed column: page title, heading path, section anchor, language. Flat and small. Never secrets, never personal data (rule 5). |

A companion `context_sources` record (one per page or source) carries `tenant_id`, `source_system`, `source_id`, `slug`, `status`, `visibility`, `url`, `generated_at`, `last_synced_at`. Chunks denormalise `status` and `visibility` from it so a vector query can filter without a join and so stores without joins (Pinecone, OpenSearch, AI Search) hold the same fields.

## 2. Chunking guidance

- **Split by heading.** A canon page is written in sections (`## Who we are`, `## Systems of record`); a section is the natural retrieval unit because the heading tells the reader what the chunk is about. Split a section further only when it exceeds the size band.
- **300 to 800 tokens per chunk,** with 10 to 15 percent overlap between consecutive chunks of the same section so a sentence cut at the boundary appears whole in one of them. Below 300 tokens a chunk loses its context; above 800 it dilutes the embedding with several topics.
- **Keep the frontmatter as a prefix in the first chunk** (`chunk_index` 0): slug, title, owner, status, visibility, last_reviewed. The prefix makes the page's governance visible in the retrieved text, and it is part of what `content_hash` covers.
- **Prefix every chunk with the page title and heading path** (`Company README > Systems of record`) so a chunk makes sense alone. Store the heading path in `metadata.heading_path` as well.
- **Do not chunk the generated header** (`<!-- generated by canon-sync ... -->`): strip it, then read `status`, `owner` and `source` from it into the typed columns.
- **Tables stay whole.** A table split across chunks is two half-tables that both mislead.
- **One tokenizer.** Count tokens with the embedding model's tokenizer, not a word count, and record it in `token_count`.

## 3. Ingestion rules

1. **Audience before embedding.** Never embed a page whose contract `visibility` is more restricted than the index's audience. A shared client index (what a client user can query) holds `client_shared` and `public` only; `client_private` pages go into a separate index or namespace for the delivery team, or are not embedded at all. `company_internal` never enters any client index. Decide the audience when you create the index and write it down in the index description.
2. **Dedupe by `content_hash`.** Before embedding a chunk, look up `content_hash` within the tenant. A hit means the text already exists; update `last_synced_at` and the pointer fields, skip the embedding call.
3. **Deprecation is deletion.** When a page's status becomes `deprecated`, or a page leaves the contract, delete its chunks (`tenant_id` + `source_system` + `source_id`). Do not flag them and rely on queries to filter: a flag is one forgotten `WHERE` clause away from being an answer. The SQL files cascade the delete from `context_sources`.
4. **Re-embed on `generated_at`.** A source whose `generated_at` moved has changed content: replace all of its chunks in one transaction (delete by source, insert the new set), so a query never sees half old and half new. A run where only `last_synced_at` moved touches no vectors.
5. **Copy the contract, do not interpret it.** `status`, `visibility`, `canonical_slug` and `source_url` are copied from the export (`bundle.json`, `meta.json` and the generated headers), never inferred from the text.

## 4. Query rules

1. **Always filter by `tenant_id` AND `visibility` AND `status`.** All three, on every query, applied by the retrieval service from the caller's identity, never from the prompt. Similarity ranks the survivors; it never widens the set. `status` defaults to `grounded`; a caller that wants drafts asks for them explicitly and labels the result unconfirmed.
2. **Use the store's row-level isolation when it has one** (Postgres RLS, Pinecone namespaces, BigQuery row access policies, OpenSearch document-level security). The query filter is still required; the store-level control is the backstop for the day the filter is forgotten.
3. **Cite `source_url`.** The retrieval layer returns `source_url`, `canonical_slug` and `status` with every hit, and the agent cites the URL in the sentence. Text without a citation is not an answer from canon.
4. **Fail closed.** No tenant in the session, no results. An empty visibility scope, no results. A stale heartbeat past the contract's `stale_after_days` and `on_stale: stop`, no results and a clear message.
5. **Check freshness first.** Read the freshness view (or per-tenant `max(last_synced_at)`) before the first query of a run and apply the contract's `on_stale` rule.

## 5. What never goes in metadata

- **Secrets.** No API keys, tokens, connection strings, credentials or `credential_reference` values. The contract fixes `secrets_in_context_layer: prohibited` and the index is part of the context layer.
- **Personal data.** No names, emails, phone numbers or identifiers of people. Owners are roles. Reporter strings from the gap tracker are not embedded.
- **Metric values.** Canon pages do not carry values, so chunks do not either; a number in a chunk is a stale number.
- **Another tenant's anything.** A chunk whose `tenant_id` does not match the index audience is a leak, not an edge case.
