# Platform matrix

The architecture has seven roles. For each, the options that fit, when to pick each, and what to watch. Recommend from what the user already runs; say when something is optional; never recommend a paid tool to solve a discipline problem.

## 1. Context layer (canon, delivery state, portals)

| Option | Pick when | Watch out for |
| --- | --- | --- |
| **Notion** | The team already lives in it; you want databases, relations, verified pages, per-page sharing and a mature API or MCP connector; a consultancy needs teamspaces plus guest-level portals. | A filter is not a permission boundary; guests cannot join groups; integrations granted a parent page see its children; a code block cannot run rollups (mirror the contract into a database view if you need reminders). |
| **Obsidian / any markdown vault in git** | Engineers or a solo operator own the canon; you want the mirror and the source to be the same repository; offline and diffable matter. | No per-page permissions: isolation is one repository per tenant; non-technical owners need a friendly editor; databases become CSV or frontmatter conventions. |
| **Confluence** | The company standardised on Atlassian; Jira and Bitbucket sit beside it. | Page trees and labels stand in for databases; the API returns storage-format HTML, so the sync adapter needs an HTML-to-markdown step (the template ships a documented stub). |
| **Coda** | Doc-plus-table workflows are already there; Packs cover the integrations needed. | Smaller connector ecosystem; export by API. |
| **SharePoint / OneNote** | A Microsoft shop with no appetite for new tools; Copilot Studio is the runtime. | Treat one site as the canon root; export via Graph; keep the contract in a repo because the pages cannot hold a reliable code block. |
| **Google Docs / Sites** | Small team already on Workspace. | Weak structure; use a strict index doc and a Sheet for the catalogs; export by Drive API. |

Decision rule: the tool people open every day wins. Moving the canon to a better tool nobody opens recreates the rot the system exists to stop.

## 2. Version control and publication gate

| Option | Pick when | Watch out for |
| --- | --- | --- |
| **GitHub** | Default; Actions for the schedule, pull requests as the gate, Dependabot and secret scanning built in. | Branch protection blocks the heartbeat commit; allow the sync bot or accept heartbeat PRs. |
| **GitLab** | Already in use; merge requests and scheduled pipelines map one to one. | Use CI/CD variables (masked) for the token. |
| **Bitbucket** | Atlassian shop; Pipelines for the schedule. | Repository variables for secrets; pull requests as the gate. |
| **Azure Repos** | Microsoft shop; Azure Pipelines schedule. | Variable groups for secrets; policies for required reviewers. |

The mirror repository is private by default. Make it public only when the canon itself is public.

## 3. Scheduled sync and validation

| Option | Pick when |
| --- | --- |
| **GitHub Actions / GitLab CI / Bitbucket Pipelines / Azure Pipelines** | Same host as the repository; nightly cron plus manual dispatch. The template ships GitHub workflows; the others are a translation of the same steps. |
| **Cloud scheduler + job** (Cloud Scheduler + Cloud Run, EventBridge + Lambda or ECS, Azure Functions timer) | Security policy forbids CI runners from holding the knowledge-base token; or the sync must run inside a VPC. |
| **n8n, Make, Zapier** | No engineer is available to own CI; the sync still commits through the git API and still opens a pull request. |

Whatever runs it, the gate stays: validation, automated review, a human asking "is this a sane export?", never content edits in the mirror.

## 4. Live data and evidence (Layer 3)

Keep what exists. The architecture adds only the metrics catalog (definitions and pull methods) and, where retrieval is needed, a vector store. Typical systems of record: a CRM, billing, a warehouse or BI layer, product analytics, support, call recordings. The catalog names the system, the exact query or explore, the reconciliation caveats and the owner, and ends every pull method with "re-query for the value".

## 5. Vector store (optional)

| Option | Pick when | Schema in this repo |
| --- | --- | --- |
| **Supabase (Postgres + pgvector)** | Already on Supabase, or you want RLS-based tenant isolation with one managed Postgres. | `schemas/vector/supabase-pgvector.sql` |
| **pgvector on any Postgres** (RDS, Aurora, Cloud SQL, AlloyDB, Azure Database for PostgreSQL) | A Postgres already runs in your cloud; you want roles and RLS. | `schemas/vector/postgres-pgvector.sql` |
| **Pinecone** | Managed, serverless, namespace per tenant, no database to run. | `schemas/vector/pinecone-index.json` |
| **Azure AI Search** | Azure shop; hybrid search with security trimming. | `schemas/vector/azure-ai-search-index.json` |
| **Amazon OpenSearch** | AWS shop already running OpenSearch. | `schemas/vector/opensearch-index.json` |
| **BigQuery vector search / AlloyDB / Vertex** | GCP shop; data already in BigQuery. | `schemas/vector/bigquery-vector.sql` (AlloyDB uses the Postgres file) |

"None yet" is the right answer when the first consumer only needs canon pages: the bundle is under 150 KB and fits in a prompt. Add a store when transcripts, long documents or files must be retrieved.

## 6. Secret manager

Use the cloud's own (GCP Secret Manager, AWS Secrets Manager, Azure Key Vault) unless the company already runs HashiCorp Vault or 1Password. Every contract, manifest and registry row stores only a reference (`secret-manager://...`); the schemas reject anything that looks like a secret.

## 7. Agent runtime and connectors

| Runtime | How the read rules get in | Notes |
| --- | --- | --- |
| **Claude Code / Cowork** | Install `company-context` from this repository's `marketplace/`; the knowledge-base MCP connector is the dependency. | Skills are plain `SKILL.md` files; the plugin is a folder. |
| **Any runtime that reads a system prompt** (Copilot Studio, Gemini Enterprise, Bedrock agents, Azure AI Foundry, LangChain or your own loop) | Inject `export/bundle.json` or the `canon/*.md` files; paste `templates/canon/operating_rules.md` as the instruction block. | Nothing in the architecture is runtime-specific; the bundle exists for exactly this. |
| **Knowledge-base native agents** (for example custom agents inside the knowledge base) | Point them at the canon index page and the gap tracker. | Their permissions are their own: review a native agent's resource scope as if it were a service account. |

## Recommendation heuristics

1. Start from the user's inventory. Change at most one thing in the first month, and make it the contract plus the sync, not the knowledge base.
2. Business pattern for one company; consultancy pattern as soon as two tenants must never see each other's content, whatever the organisation is called.
3. Pages: at most eight. Ground the ones the first consumer needs; leave the rest draft on the owner's calendar.
4. First agent at `read_only` or `draft_write`. `controlled_write` and `external_action` wait for the pilot gates.
5. Vector store only with a retrieval need in the first consumer. Secret manager before any credential exists. Portal before any client is invited.
6. Prefer a translation of the shipped GitHub workflows over a new orchestrator.

## Three worked recommendations (fictional)

**Solo consultant, several clients, lives in Notion, Claude Cowork, GitHub, a Supabase call database.** Consultancy pattern. Context layer: Notion, a private HQ plus one teamspace per client and a separate portal page each. Git: GitHub, private mirror, Actions nightly. Layer 3: the CRM, invoicing, and Supabase for call transcripts (tenant_id = client ID, never shared). Vector: Supabase pgvector, because the transcripts are already there. Secrets: 1Password references. Runtime: Cowork with the `client-context` plugin. First consumer: the weekly client status draft at `draft_write`. Deferred: client-owned workspaces until a contract requires one.

**120-person B2B SaaS company, Notion handbook, GitHub, BigQuery and a BI tool, Claude Code for engineers, no vector store.** Business pattern. Context layer: Notion, the existing handbook becomes the canon root; eight pages; owners are the CEO, PMM, RevOps and Data roles. Git: GitHub Actions nightly into a private mirror with a plugin marketplace. Layer 3: CRM, billing reconciled into BigQuery, the catalog grounded for the weekly leadership brief. Vector: none; defer until call transcripts are in scope, then BigQuery vector search or AlloyDB. Secrets: GCP Secret Manager. Runtime: Claude Code plugin for engineers, bundle.json for the marketing team's drafting tool. First consumer: the weekly brief.

**Regulated enterprise division, Confluence and SharePoint, Azure, Copilot Studio, strict IT approvals.** Business pattern with one isolated teamspace per division. Context layer: Confluence as the canon root (the adapter needs the HTML step; budget a day), SharePoint stays for files. Git: Azure Repos and Pipelines, nightly, private. Layer 3: CRM and the warehouse; Azure AI Search when retrieval is approved. Secrets: Key Vault. Runtime: Copilot Studio with bundle.json injected as knowledge; the operating rules pasted as instructions. First consumer: an internal sales-enablement assistant at `read_only`. Deferred: any write path until the security review signs the manifest.
