-- =============================================================================================
-- Context layer vector store: Supabase (Postgres + pgvector)
-- Implements schemas/vector/metadata-contract.md on a Supabase project.
--
-- Idempotent: every statement is CREATE IF NOT EXISTS, CREATE OR REPLACE, or DROP IF EXISTS
-- followed by CREATE, so you can run it from the SQL editor or a migration as often as you like.
--
-- Design in one paragraph. Two tables: context_sources (one row per page or source) and
-- context_chunks (the embedded rows). Chunks denormalise status and visibility from their source
-- so a vector query filters without a join, and a trigger keeps them in step. Row-level security
-- confines every authenticated query to one tenant and to the visibilities that caller may see,
-- read from session settings (or the JWT) that the retrieval service sets from the caller's
-- identity, never from the prompt. The service role (the sync job) bypasses RLS to write. The
-- match function is SECURITY INVOKER so RLS applies to whoever calls it, and it still takes the
-- tenant as an explicit argument: belt and braces.
--
-- Everything below is fictional sample data and placeholders. Globex Logistics is a fictional client.
-- =============================================================================================

create extension if not exists vector;

-- ---------------------------------------------------------------------------------------------
-- 1. context_sources: one row per canonical page or depth source
-- ---------------------------------------------------------------------------------------------
create table if not exists public.context_sources (
  tenant_id       text        not null,
  source_system   text        not null
                              check (source_system in ('notion', 'markdown', 'confluence', 'crm', 'calls', 'files')),
  source_id       text        not null,
  slug            text        check (slug ~ '^[a-z][a-z0-9_]*$'),
  title           text,
  status          text        not null
                              check (status in ('grounded', 'draft', 'stub', 'deprecated')),
  visibility      text        not null
                              check (visibility in ('company_internal', 'client_private', 'client_shared', 'public')),
  url             text        not null,
  content_hash    text        check (content_hash ~ '^[0-9a-f]{64}$'),
  generated_at    timestamptz not null,
  last_synced_at  timestamptz not null,
  metadata        jsonb       not null default '{}'::jsonb,
  primary key (tenant_id, source_system, source_id)
);

comment on table  public.context_sources is
  'One row per canonical page or depth source per tenant. The parent of context_chunks; deleting a source deletes its chunks (rule 3: deprecation is deletion). Populated by the sync from export/meta.json and export/bundle.json.';
comment on column public.context_sources.tenant_id is
  'Isolation key. "company" for the single-company pattern; the client contract client_id (CLIENT-001) for a consultancy, verbatim and case-sensitive.';
comment on column public.context_sources.source_system is
  'Where the source lives: notion | markdown | confluence for canon pages; crm | calls | files for depth sources embedded under the same rules.';
comment on column public.context_sources.source_id is
  'Page id, vault path or record id in the source system. With tenant_id and source_system it is the natural key, so the sync can replace a changed page without a lookup table.';
comment on column public.context_sources.slug is
  'The contract slug for a canonical page (company_readme); null for depth sources. Unique per tenant where present.';
comment on column public.context_sources.status is
  'grounded | draft | stub | deprecated, copied from the contract. Setting it to deprecated deletes the chunks (see the trigger below).';
comment on column public.context_sources.visibility is
  'company_internal | client_private | client_shared | public, copied from the contract. Propagated to chunks by trigger so a query can filter on the chunk row alone.';
comment on column public.context_sources.url is
  'Citation URL (page_url_base + id). Returned with every hit; a source without one should not be embedded.';
comment on column public.context_sources.generated_at is
  'meta.json generated_at of the export that produced this version: when the content last changed. If it moves, every chunk of the source is replaced.';
comment on column public.context_sources.last_synced_at is
  'meta.json last_synced_at: the heartbeat. The context_freshness view reads max(last_synced_at) per tenant.';
comment on column public.context_sources.metadata is
  'Flat extras (owner role, review cadence, caveat). Never secrets, never personal data.';

-- A tenant may hold a slug only once; depth sources have no slug and are excluded from the rule.
create unique index if not exists context_sources_tenant_slug_uidx
  on public.context_sources (tenant_id, slug)
  where slug is not null;

create index if not exists context_sources_tenant_vis_status_idx
  on public.context_sources (tenant_id, visibility, status);

-- ---------------------------------------------------------------------------------------------
-- 2. context_chunks: the embedded rows (the metadata contract, field for field)
-- ---------------------------------------------------------------------------------------------
create table if not exists public.context_chunks (
  id              text        primary key,
  tenant_id       text        not null,
  source_system   text        not null
                              check (source_system in ('notion', 'markdown', 'confluence', 'crm', 'calls', 'files')),
  source_id       text        not null,
  source_url      text        not null,
  canonical_slug  text        check (canonical_slug ~ '^[a-z][a-z0-9_]*$'),
  status          text        not null
                              check (status in ('grounded', 'draft', 'stub', 'deprecated')),
  visibility      text        not null
                              check (visibility in ('company_internal', 'client_private', 'client_shared', 'public')),
  content_hash    text        not null
                              check (content_hash ~ '^[0-9a-f]{64}$'),
  chunk_index     integer     not null check (chunk_index >= 0),
  text            text        not null,
  embedding       vector(1536) not null,
  token_count     integer     check (token_count > 0),
  generated_at    timestamptz not null,
  last_synced_at  timestamptz not null,
  metadata        jsonb       not null default '{}'::jsonb,
  unique (tenant_id, source_system, source_id, chunk_index),
  foreign key (tenant_id, source_system, source_id)
    references public.context_sources (tenant_id, source_system, source_id)
    on delete cascade
);

comment on table  public.context_chunks is
  'One row per embedded chunk. Every column except embedding and text is governance metadata: it is what confines a query to a tenant, keeps drafts out of answers and yields the citation. See schemas/vector/metadata-contract.md.';
comment on column public.context_chunks.id is
  'Deterministic: {source_system}:{source_id}#{chunk_index}. Re-ingestion is an upsert, and the id alone says where the chunk came from.';
comment on column public.context_chunks.tenant_id is
  'Isolation key, identical to the parent source. RLS compares it with the session tenant on every row.';
comment on column public.context_chunks.source_url is
  'The citation returned with every match. Copied from the source so no join is needed at query time.';
comment on column public.context_chunks.canonical_slug is
  'Contract slug for canonical pages, null for depth sources. Lets a caller ask for one page by name.';
comment on column public.context_chunks.status is
  'Denormalised from context_sources by trigger. Queries default to grounded only.';
comment on column public.context_chunks.visibility is
  'Denormalised from context_sources by trigger. RLS and the match function both filter on it.';
comment on column public.context_chunks.content_hash is
  'sha256 of text. Dedupe before embedding: an existing hash within the tenant means no new embedding call.';
comment on column public.context_chunks.chunk_index is
  'Position within the source, from 0. Chunk 0 carries the page frontmatter as a prefix.';
comment on column public.context_chunks.text is
  'The exact text the embedding was computed from, including the title and heading-path prefix.';
comment on column public.context_chunks.embedding is
  'vector(1536). To change dimensions (768, 1024, 3072 are common): truncate the table, run ALTER TABLE public.context_chunks ALTER COLUMN embedding TYPE vector(N), drop and recreate the HNSW index below, change the query_embedding parameter type in match_context_chunks, and re-embed everything. Vectors from two models never share an index. pgvector HNSW indexes the vector type up to 2000 dimensions; above that use halfvec.';
comment on column public.context_chunks.token_count is
  'Tokens in text under the embedding model tokenizer; for prompt budgeting and chunking audits.';
comment on column public.context_chunks.generated_at is
  'generated_at of the export this chunk came from. A moved generated_at on the source means every chunk is replaced.';
comment on column public.context_chunks.last_synced_at is
  'The heartbeat: last run that confirmed this chunk current.';
comment on column public.context_chunks.metadata is
  'Flat extras: heading_path, title, language. Never secrets, never personal data, never metric values.';

-- Approximate nearest neighbour index, cosine distance. HNSW needs no training step and stays
-- accurate as rows arrive, which suits a nightly sync. m and ef_construction are the pgvector
-- defaults; raise ef_construction for recall at the cost of build time.
create index if not exists context_chunks_embedding_hnsw_idx
  on public.context_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- The three filters every query carries, in one btree, so the planner can narrow before the
-- vector comparison when the tenant is small.
create index if not exists context_chunks_tenant_vis_status_idx
  on public.context_chunks (tenant_id, visibility, status);

-- Replace-by-source (rule 4) and the FK lookup.
create index if not exists context_chunks_source_idx
  on public.context_chunks (tenant_id, source_system, source_id);

-- Dedupe lookup (rule 2).
create index if not exists context_chunks_content_hash_idx
  on public.context_chunks (tenant_id, content_hash);

-- ---------------------------------------------------------------------------------------------
-- 3. Keep chunks in step with their source: propagate status/visibility/url, delete on deprecation
-- ---------------------------------------------------------------------------------------------
create or replace function public.context_sources_propagate()
returns trigger
language plpgsql
as $$
begin
  if new.status = 'deprecated' then
    -- Rule 3: deprecation is deletion. A flag is one forgotten WHERE clause away from an answer.
    delete from public.context_chunks c
     where c.tenant_id = new.tenant_id
       and c.source_system = new.source_system
       and c.source_id = new.source_id;
    return new;
  end if;

  update public.context_chunks c
     set status         = new.status,
         visibility     = new.visibility,
         source_url     = new.url,
         canonical_slug = new.slug,
         last_synced_at = new.last_synced_at
   where c.tenant_id = new.tenant_id
     and c.source_system = new.source_system
     and c.source_id = new.source_id;
  return new;
end;
$$;

comment on function public.context_sources_propagate() is
  'Row trigger on context_sources: copies status, visibility, url and slug down to the chunks, and deletes the chunks when the source becomes deprecated.';

drop trigger if exists context_sources_propagate_trg on public.context_sources;
create trigger context_sources_propagate_trg
  after update of status, visibility, url, slug, last_synced_at on public.context_sources
  for each row
  execute function public.context_sources_propagate();

-- ---------------------------------------------------------------------------------------------
-- 4. Row-level security
--
-- Who is the caller? The retrieval service resolves the caller's identity to a tenant and a
-- visibility scope and puts them in the session:
--   select set_config('app.tenant_id', 'CLIENT-001', true);
--   select set_config('app.visibility_scope', 'client_shared,public', true);
-- (third argument true = local to the current transaction, so a pooled connection cannot leak
-- one caller's tenant into the next request).
-- When the query arrives through PostgREST with a Supabase Auth JWT instead of a server-side
-- connection, the same two values are read from app_metadata claims on the token, which only
-- the Auth admin API can set, never the user. The helpers below try the session first, then the JWT.
--
-- Visibility scope by role, set by the service, never by the caller:
--   company employee (single-company pattern)      company_internal,public
--   client user in the portal                      client_shared,public
--   consultancy delivery team for that client      client_private,client_shared,public
--   anonymous / public site                        public
--
-- Fail closed: no tenant or no scope in the session and no claim on the token means
-- current_setting() returns null, the comparison is null, and no row is visible.
-- ---------------------------------------------------------------------------------------------
create or replace function public.context_current_tenant()
returns text
language sql
stable
as $$
  select coalesce(
    nullif(current_setting('app.tenant_id', true), ''),
    nullif(auth.jwt() -> 'app_metadata' ->> 'tenant_id', '')
  );
$$;

comment on function public.context_current_tenant() is
  'The tenant the current caller may read: session setting app.tenant_id, else the app_metadata.tenant_id JWT claim, else null (which hides every row).';

create or replace function public.context_current_visibility_scope()
returns text[]
language sql
stable
as $$
  select string_to_array(
    coalesce(
      nullif(current_setting('app.visibility_scope', true), ''),
      nullif(auth.jwt() -> 'app_metadata' ->> 'visibility_scope', '')
    ),
    ','
  );
$$;

comment on function public.context_current_visibility_scope() is
  'Comma-separated visibilities the current caller may read, from app.visibility_scope or the app_metadata.visibility_scope claim, as a text array; null hides every row.';

alter table public.context_sources enable row level security;
alter table public.context_chunks  enable row level security;

-- The sync job connects as service_role. In Supabase that role bypasses RLS anyway; the explicit
-- policy documents the intent and keeps working if the role is ever recreated without bypassrls.
drop policy if exists context_sources_service_all on public.context_sources;
create policy context_sources_service_all on public.context_sources
  for all to service_role
  using (true) with check (true);

drop policy if exists context_chunks_service_all on public.context_chunks;
create policy context_chunks_service_all on public.context_chunks
  for all to service_role
  using (true) with check (true);

-- Authenticated callers read their own tenant, inside their visibility scope. SELECT only:
-- nothing that reads the index may write to it; writes come from the sync alone.
drop policy if exists context_sources_tenant_read on public.context_sources;
create policy context_sources_tenant_read on public.context_sources
  for select to authenticated
  using (
    tenant_id = public.context_current_tenant()
    and visibility = any (public.context_current_visibility_scope())
  );

drop policy if exists context_chunks_tenant_read on public.context_chunks;
create policy context_chunks_tenant_read on public.context_chunks
  for select to authenticated
  using (
    tenant_id = public.context_current_tenant()
    and visibility = any (public.context_current_visibility_scope())
  );

-- anon gets nothing: no policy exists for it, so RLS hides every row. Public canon served to an
-- unauthenticated site should go through a server-side function that sets tenant and
-- visibility_scope = 'public' itself.

grant usage on schema public to authenticated;
grant select on public.context_sources, public.context_chunks to authenticated;

-- ---------------------------------------------------------------------------------------------
-- 5. match_context_chunks: the one query the retrieval layer calls
--
-- Cosine distance (<=>) because the HNSW index is built with vector_cosine_ops; similarity is
-- 1 - distance. SECURITY INVOKER (the default, stated here on purpose): RLS applies to the caller,
-- so even a wrong match_tenant argument cannot cross a tenant. The explicit arguments remain
-- because an index query that does not name its tenant, visibility and status is a bug by rule 1.
-- ---------------------------------------------------------------------------------------------
create or replace function public.match_context_chunks(
  query_embedding  vector(1536),
  match_tenant     text,
  match_visibility text[],
  match_statuses   text[]  default '{grounded}',
  match_count      int     default 8,
  min_similarity   float   default 0.75
)
returns table (
  id             text,
  source_url     text,
  canonical_slug text,
  status         text,
  text           text,
  similarity     float
)
language sql
stable
security invoker
set search_path = public
as $$
  select
    c.id,
    c.source_url,
    c.canonical_slug,
    c.status,
    c.text,
    1 - (c.embedding <=> query_embedding) as similarity
  from public.context_chunks c
  where c.tenant_id = match_tenant
    and c.visibility = any (match_visibility)
    and c.status = any (match_statuses)
    and 1 - (c.embedding <=> query_embedding) >= min_similarity
  order by c.embedding <=> query_embedding
  limit match_count;
$$;

comment on function public.match_context_chunks(vector, text, text[], text[], int, float) is
  'Nearest grounded chunks for one tenant inside a visibility scope, by cosine similarity, with the citation URL. match_statuses defaults to {grounded}; pass {grounded,draft} only when the caller will label drafts unconfirmed. min_similarity 0.75 is a starting point; tune it against your evaluation set.';

revoke execute on function public.match_context_chunks(vector, text, text[], text[], int, float) from public;
grant  execute on function public.match_context_chunks(vector, text, text[], text[], int, float) to authenticated, service_role;

-- Filtered ANN recall. With a selective WHERE, HNSW may return fewer than match_count rows
-- because it inspects ef_search candidates before the filter is applied. Raise the budget per
-- session (set hnsw.ef_search = 100;) or, on pgvector 0.8+, enable iterative scans
-- (set hnsw.iterative_scan = relaxed_order;) so the scan continues until match_count rows pass.

-- ---------------------------------------------------------------------------------------------
-- 6. context_freshness: the heartbeat per tenant
-- security_invoker (Postgres 15+) makes the view honour the caller's RLS, so a client user sees
-- only their tenant's row. Alert when sync_age_days passes the contract's freshness.stale_after_days.
-- ---------------------------------------------------------------------------------------------
create or replace view public.context_freshness
  with (security_invoker = true)
as
select
  tenant_id,
  count(*)                                               as sources,
  count(*) filter (where status = 'grounded')            as grounded_sources,
  max(generated_at)                                      as content_as_of,
  max(last_synced_at)                                    as last_synced_at,
  now() - max(last_synced_at)                            as sync_age,
  extract(epoch from now() - max(last_synced_at)) / 86400.0 as sync_age_days
from public.context_sources
group by tenant_id;

comment on view public.context_freshness is
  'Per-tenant freshness: content_as_of is the generated_at clock (cite it), last_synced_at is the heartbeat. Compare sync_age_days with the contract freshness.stale_after_days before the first query of a run and apply on_stale. Under RLS the view counts only the sources the caller may see; a caller who gets no row has no evidence of freshness and should stop.';

grant select on public.context_freshness to authenticated, service_role;

-- =============================================================================================
-- How to use from an agent (server-side connection, one transaction per request)
--
--   begin;
--   -- 1. Scope the session from the caller's identity. Never from the prompt.
--   select set_config('app.tenant_id', 'CLIENT-001', true);
--   select set_config('app.visibility_scope', 'client_shared,public', true);
--
--   -- 2. Check the heartbeat and apply the contract's on_stale rule.
--   select tenant_id, content_as_of, sync_age_days from public.context_freshness;
--   --    sync_age_days > freshness.stale_after_days  ->  verify_live_or_stop / stop / verify_live
--
--   -- 3. Retrieve. The arguments repeat the scope on purpose (rule 1: tenant AND visibility AND status).
--   select id, source_url, canonical_slug, status, text, similarity
--     from public.match_context_chunks(
--            '[0.0123, -0.0456, ...]'::vector(1536),     -- the embedded question
--            'CLIENT-001',
--            array['client_shared', 'public'],
--            array['grounded'],
--            8,
--            0.75);
--   commit;
--
--   -- 4. Answer with citations: every claim ends with its source_url. Text that cannot be cited
--   --    is not an answer from canon; file a gap row instead (gap-tracker.schema.json).
--
-- Through PostgREST / supabase-js with a user JWT, call the function as an RPC:
--   supabase.rpc('match_context_chunks', { query_embedding, match_tenant: 'CLIENT-001',
--                 match_visibility: ['client_shared', 'public'] })
-- and RLS reads tenant_id and visibility_scope from the token's app_metadata claims.
--
-- Ingestion (service role, per source, in one transaction): upsert context_sources; if
-- generated_at moved, delete that source's chunks and insert the new set; skip embedding calls for
-- chunks whose content_hash already exists in the tenant; set status = 'deprecated' or delete the
-- source row to remove a page. Never write from anything that also answers questions.
-- =============================================================================================
