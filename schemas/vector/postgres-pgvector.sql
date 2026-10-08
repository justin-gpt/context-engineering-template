-- =============================================================================================
-- Context layer vector store: plain PostgreSQL 15+ with pgvector
-- Implements schemas/vector/metadata-contract.md on any managed or self-hosted Postgres:
-- Amazon RDS / Aurora PostgreSQL, Google Cloud SQL / AlloyDB, Azure Database for PostgreSQL,
-- or a container. Same tables, indexes, trigger, match function and freshness view as
-- supabase-pgvector.sql; only the roles and the way a caller is identified differ.
--
-- Idempotent: CREATE IF NOT EXISTS, CREATE OR REPLACE, DROP IF EXISTS + CREATE, and role
-- creation guarded by a lookup, so it can be re-run as a migration.
--
-- Two ways to identify the caller, both enforced by row-level security; use one or both:
--   A. One login role per tenant (context_reader_client_001 ...), each a member of context_reader,
--      mapped to its tenant and visibility scope in context_tenant_grants. Isolation then rests on
--      database authentication, which is what auditors and client security reviews ask for.
--   B. One shared application role (context_app) that sets app.tenant_id and app.visibility_scope
--      per transaction from the caller's identity, for a retrieval service with a connection pool.
-- The sync job writes as context_writer and nothing else may write.
--
-- Managed-service notes: you will not be superuser. CREATE EXTENSION vector needs the service's
-- admin role (rds_superuser, cloudsqlsuperuser, azure_pg_admin) and on Azure the extension must be
-- allow-listed in the azure.extensions server parameter first. Prefer the platform's IAM or
-- Entra ID authentication for the login roles so no database password exists to leak.
--
-- Everything below is fictional sample data and placeholders. Globex Logistics is a fictional client.
-- =============================================================================================

create extension if not exists vector;

-- ---------------------------------------------------------------------------------------------
-- 0. Roles (guarded: CREATE ROLE has no IF NOT EXISTS)
-- ---------------------------------------------------------------------------------------------
do $$
begin
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'context_writer') then
    create role context_writer nologin;        -- the sync job; the only writer
  end if;
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'context_reader') then
    create role context_reader nologin;        -- group role; per-tenant login roles join it
  end if;
  if not exists (select 1 from pg_catalog.pg_roles where rolname = 'context_app') then
    create role context_app nologin;           -- shared application role, scoped per transaction
  end if;
end
$$;

comment on role context_writer is 'Context layer sync job. Full access to context_sources and context_chunks; bypasses nothing else. Grant LOGIN or IAM auth to a role that is a member of it.';
comment on role context_reader is 'Group role for per-tenant readers. Members see only the tenants and visibilities listed for them in context_tenant_grants.';
comment on role context_app   is 'Shared retrieval-service role. Sees only the tenant and visibilities set in app.tenant_id and app.visibility_scope for the current transaction.';

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
  'One row per canonical page or depth source per tenant; parent of context_chunks (delete cascades: deprecation is deletion). Populated by the sync from export/meta.json and export/bundle.json.';
comment on column public.context_sources.tenant_id is
  'Isolation key. "company" for the single-company pattern; the client contract client_id (CLIENT-001) for a consultancy, verbatim and case-sensitive.';
comment on column public.context_sources.source_system is
  'notion | markdown | confluence for canon pages; crm | calls | files for depth sources embedded under the same rules.';
comment on column public.context_sources.source_id is
  'Page id, vault path or record id in the source system. Natural key with tenant_id and source_system.';
comment on column public.context_sources.slug is
  'Contract slug for a canonical page; null for depth sources. Unique per tenant where present.';
comment on column public.context_sources.status is
  'grounded | draft | stub | deprecated, copied from the contract. Setting deprecated deletes the chunks via trigger.';
comment on column public.context_sources.visibility is
  'company_internal | client_private | client_shared | public, copied from the contract and propagated to chunks.';
comment on column public.context_sources.url is
  'Citation URL (page_url_base + id), returned with every hit.';
comment on column public.context_sources.generated_at is
  'meta.json generated_at: when content last changed. If it moves, every chunk of the source is replaced.';
comment on column public.context_sources.last_synced_at is
  'meta.json last_synced_at: the heartbeat read by context_freshness.';
comment on column public.context_sources.metadata is
  'Flat extras (owner role, review cadence, caveat). Never secrets, never personal data.';

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
  'One row per embedded chunk. Every column except embedding and text is governance metadata: tenant, visibility, status, citation. See schemas/vector/metadata-contract.md.';
comment on column public.context_chunks.id is
  'Deterministic: {source_system}:{source_id}#{chunk_index}. Re-ingestion is an upsert.';
comment on column public.context_chunks.tenant_id is
  'Isolation key, identical to the parent source. Every RLS policy compares it.';
comment on column public.context_chunks.source_url is
  'The citation returned with every match, copied from the source so no join is needed.';
comment on column public.context_chunks.canonical_slug is
  'Contract slug for canonical pages, null for depth sources.';
comment on column public.context_chunks.status is
  'Denormalised from context_sources by trigger. Queries default to grounded only.';
comment on column public.context_chunks.visibility is
  'Denormalised from context_sources by trigger. RLS and the match function both filter on it.';
comment on column public.context_chunks.content_hash is
  'sha256 of text. Dedupe before embedding.';
comment on column public.context_chunks.chunk_index is
  'Position within the source, from 0. Chunk 0 carries the page frontmatter as a prefix.';
comment on column public.context_chunks.text is
  'The exact text the embedding was computed from, including the title and heading-path prefix.';
comment on column public.context_chunks.embedding is
  'vector(1536). To change dimensions: truncate, ALTER COLUMN embedding TYPE vector(N), recreate the HNSW index, change the query_embedding parameter type in match_context_chunks, re-embed everything. pgvector HNSW indexes vector up to 2000 dimensions; above that use halfvec.';
comment on column public.context_chunks.token_count is
  'Tokens in text under the embedding model tokenizer.';
comment on column public.context_chunks.generated_at is
  'generated_at of the export this chunk came from.';
comment on column public.context_chunks.last_synced_at is
  'The heartbeat: last run that confirmed this chunk current.';
comment on column public.context_chunks.metadata is
  'Flat extras: heading_path, title, language. Never secrets, never personal data, never metric values.';

-- Approximate nearest neighbour index, cosine distance; HNSW needs no training and stays accurate
-- as rows arrive nightly. Defaults for m and ef_construction; raise ef_construction for recall.
create index if not exists context_chunks_embedding_hnsw_idx
  on public.context_chunks using hnsw (embedding vector_cosine_ops)
  with (m = 16, ef_construction = 64);

-- The three filters every query carries.
create index if not exists context_chunks_tenant_vis_status_idx
  on public.context_chunks (tenant_id, visibility, status);

-- Replace-by-source and the FK lookup.
create index if not exists context_chunks_source_idx
  on public.context_chunks (tenant_id, source_system, source_id);

-- Dedupe lookup.
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
-- 4. Tenant grants for pattern A (one login role per tenant)
--
-- A reader role is mapped to the tenants it may read and the visibilities it may see. One login
-- role per client keeps each client's credential separate (rotate, revoke, audit per client) and
-- lets a client security review verify isolation at the database layer, not in application code.
-- Rows are data, so onboarding and offboarding a client is an INSERT and a DELETE, not a deploy.
-- ---------------------------------------------------------------------------------------------
create table if not exists public.context_tenant_grants (
  role_name         name    not null,
  tenant_id         text    not null,
  visibility_scope  text[]  not null
                            check (visibility_scope <@ array['company_internal', 'client_private', 'client_shared', 'public']::text[]),
  granted_at        timestamptz not null default now(),
  note              text,
  primary key (role_name, tenant_id)
);

comment on table public.context_tenant_grants is
  'Which database role may read which tenant at which visibilities. Read by the RLS policies for members of context_reader. Group roles work: a row for a group role covers every member.';
comment on column public.context_tenant_grants.visibility_scope is
  'Subset of the four visibilities. A client user gets {client_shared,public}; the delivery team for that client gets {client_private,client_shared,public}; the company''s own staff get {company_internal,public}.';
comment on column public.context_tenant_grants.note is
  'Why the grant exists and who approved it (an engagement id, a ticket). Never a person''s name.';

-- Example provisioning for one client, kept as comments so this file creates no credentials:
--   create role context_reader_client_001 login in role context_reader;
--   -- Attach authentication out of band: IAM auth (rds_iam / cloudsqliamuser), Entra ID, or
--   -- ALTER ROLE ... PASSWORD set by your secret manager's rotation job. Never a literal here.
--   insert into public.context_tenant_grants (role_name, tenant_id, visibility_scope, note)
--   values ('context_reader_client_001', 'CLIENT-001', '{client_shared,public}', 'ENG-001 portal retrieval')
--   on conflict (role_name, tenant_id) do update set visibility_scope = excluded.visibility_scope;
--   -- Offboarding: delete the grant row, then DROP ROLE. The grant row goes first so a reconnect
--   -- between the two steps sees nothing.

-- ---------------------------------------------------------------------------------------------
-- 5. Caller identity helpers for pattern B (shared application role with per-transaction scope)
--
--   select set_config('app.tenant_id', 'CLIENT-001', true);
--   select set_config('app.visibility_scope', 'client_shared,public', true);
-- The third argument true scopes the setting to the current transaction, so a pooled connection
-- cannot carry one caller's tenant into the next request. Missing or empty settings resolve to
-- null, the policy comparison is null, and no row is visible: fail closed.
-- ---------------------------------------------------------------------------------------------
create or replace function public.context_current_tenant()
returns text
language sql
stable
as $$
  select nullif(current_setting('app.tenant_id', true), '');
$$;

comment on function public.context_current_tenant() is
  'The tenant the current transaction may read (app.tenant_id), or null, which hides every row.';

create or replace function public.context_current_visibility_scope()
returns text[]
language sql
stable
as $$
  select string_to_array(nullif(current_setting('app.visibility_scope', true), ''), ',');
$$;

comment on function public.context_current_visibility_scope() is
  'Visibilities the current transaction may read (app.visibility_scope, comma-separated) as a text array, or null, which hides every row.';

-- ---------------------------------------------------------------------------------------------
-- 6. Row-level security
--
-- Policies are permissive and OR together only within the role they are granted TO, so a
-- per-tenant reader is judged by its grants and the application role by its session, never both.
-- The table owner and superusers bypass RLS: run this file as an administrative role that no
-- service connects as, and connect the sync as context_writer, never as the owner.
-- ---------------------------------------------------------------------------------------------
alter table public.context_sources       enable row level security;
alter table public.context_chunks        enable row level security;
alter table public.context_tenant_grants enable row level security;

-- Writer: the sync job, full access.
drop policy if exists context_sources_writer_all on public.context_sources;
create policy context_sources_writer_all on public.context_sources
  for all to context_writer using (true) with check (true);

drop policy if exists context_chunks_writer_all on public.context_chunks;
create policy context_chunks_writer_all on public.context_chunks
  for all to context_writer using (true) with check (true);

drop policy if exists context_tenant_grants_writer_all on public.context_tenant_grants;
create policy context_tenant_grants_writer_all on public.context_tenant_grants
  for all to context_writer using (true) with check (true);

-- Pattern A: members of context_reader see the tenants and visibilities granted to them (or to a
-- group they belong to). The join to pg_roles means a grant row for a dropped role is ignored
-- instead of raising an error.
drop policy if exists context_tenant_grants_self_read on public.context_tenant_grants;
create policy context_tenant_grants_self_read on public.context_tenant_grants
  for select to context_reader
  using (
    exists (
      select 1
        from pg_catalog.pg_roles r
       where r.rolname = context_tenant_grants.role_name
         and pg_has_role(current_user, r.oid, 'member')
    )
  );

drop policy if exists context_sources_reader_read on public.context_sources;
create policy context_sources_reader_read on public.context_sources
  for select to context_reader
  using (
    exists (
      select 1
        from public.context_tenant_grants g
        join pg_catalog.pg_roles r on r.rolname = g.role_name
       where g.tenant_id = context_sources.tenant_id
         and context_sources.visibility = any (g.visibility_scope)
         and pg_has_role(current_user, r.oid, 'member')
    )
  );

drop policy if exists context_chunks_reader_read on public.context_chunks;
create policy context_chunks_reader_read on public.context_chunks
  for select to context_reader
  using (
    exists (
      select 1
        from public.context_tenant_grants g
        join pg_catalog.pg_roles r on r.rolname = g.role_name
       where g.tenant_id = context_chunks.tenant_id
         and context_chunks.visibility = any (g.visibility_scope)
         and pg_has_role(current_user, r.oid, 'member')
    )
  );

-- Pattern B: the application role sees what the current transaction says, and nothing without it.
drop policy if exists context_sources_app_read on public.context_sources;
create policy context_sources_app_read on public.context_sources
  for select to context_app
  using (
    tenant_id = public.context_current_tenant()
    and visibility = any (public.context_current_visibility_scope())
  );

drop policy if exists context_chunks_app_read on public.context_chunks;
create policy context_chunks_app_read on public.context_chunks
  for select to context_app
  using (
    tenant_id = public.context_current_tenant()
    and visibility = any (public.context_current_visibility_scope())
  );

-- Privileges. Readers and the app role may only SELECT; nothing that answers questions may write.
revoke all on public.context_sources, public.context_chunks, public.context_tenant_grants from public;
grant usage on schema public to context_writer, context_reader, context_app;
grant select, insert, update, delete on public.context_sources, public.context_chunks, public.context_tenant_grants to context_writer;
grant select on public.context_sources, public.context_chunks to context_reader, context_app;
grant select on public.context_tenant_grants to context_reader;

-- ---------------------------------------------------------------------------------------------
-- 7. match_context_chunks: the one query the retrieval layer calls
--
-- Cosine distance (<=>) to match the HNSW operator class; similarity is 1 - distance.
-- SECURITY INVOKER so RLS applies to the caller; the explicit tenant, visibility and status
-- arguments are still required because a query that does not name them is a bug by rule 1.
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
  'Nearest grounded chunks for one tenant inside a visibility scope, by cosine similarity, with the citation URL. match_statuses defaults to {grounded}; pass {grounded,draft} only when the caller labels drafts unconfirmed. Tune min_similarity against your evaluation set.';

revoke execute on function public.match_context_chunks(vector, text, text[], text[], int, float) from public;
grant  execute on function public.match_context_chunks(vector, text, text[], text[], int, float) to context_reader, context_app, context_writer;

-- Filtered ANN recall: with a selective WHERE, HNSW may return fewer than match_count rows because
-- it inspects ef_search candidates before the filter applies. Raise the budget per session
-- (set hnsw.ef_search = 100;) or on pgvector 0.8+ enable iterative scans
-- (set hnsw.iterative_scan = relaxed_order;) so the scan continues until match_count rows pass.

-- ---------------------------------------------------------------------------------------------
-- 8. context_freshness: the heartbeat per tenant
-- security_invoker (Postgres 15+) makes the view honour the caller's RLS.
-- Alert when sync_age_days passes the contract's freshness.stale_after_days.
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

grant select on public.context_freshness to context_reader, context_app, context_writer;

-- =============================================================================================
-- How to use from an agent
--
-- Pattern A (per-tenant login role): connect as the tenant's role; RLS already scopes everything.
--   select tenant_id, content_as_of, sync_age_days from public.context_freshness;
--   select id, source_url, canonical_slug, status, text, similarity
--     from public.match_context_chunks('[0.0123, -0.0456, ...]'::vector(1536),
--                                      'CLIENT-001', array['client_shared', 'public']);
--
-- Pattern B (shared context_app role, one transaction per request):
--   begin;
--   select set_config('app.tenant_id', 'CLIENT-001', true);                 -- from the caller's identity
--   select set_config('app.visibility_scope', 'client_shared,public', true); -- never from the prompt
--   select tenant_id, content_as_of, sync_age_days from public.context_freshness;
--   --   sync_age_days > freshness.stale_after_days  ->  apply on_stale (verify_live_or_stop / stop / verify_live)
--   select id, source_url, canonical_slug, status, text, similarity
--     from public.match_context_chunks('[0.0123, -0.0456, ...]'::vector(1536),
--                                      'CLIENT-001', array['client_shared', 'public'], array['grounded'], 8, 0.75);
--   commit;
--
-- Then answer with citations: every claim ends with its source_url. Text that cannot be cited is
-- not an answer from canon; file a gap row instead (schemas/json/gap-tracker.schema.json).
--
-- Ingestion (as context_writer, per source, in one transaction): upsert context_sources; if
-- generated_at moved, delete that source's chunks and insert the new set; skip embedding calls for
-- chunks whose content_hash already exists in the tenant; set status = 'deprecated' or delete the
-- source row to remove a page. Nothing that answers questions ever holds the writer role.
-- =============================================================================================
