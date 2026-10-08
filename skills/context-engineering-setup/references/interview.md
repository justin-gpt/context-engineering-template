# Interview question bank

Ask in batches of three to five. Each question says what the answer changes, so you can skip what is already known. Record answers in the brief; record unknowns as `[YOU DECIDE]` for the owner.

## Batch 1 — shape

| Question | What the answer changes |
| --- | --- |
| Is this for one company's own agents, or for a practice that serves several clients? (A single company with strict divisions or regions may still need the consultancy pattern.) | Business vs consultancy pattern; whether per-client contracts, hubs and portals are needed. |
| How many people will own canon pages, and are they available monthly for a 20-minute review? | Page count ceiling (fewer owners, fewer pages); review cadence; whether ratification is the bottleneck. |
| Who will act as agent operator: the role that owns the sync, the gap-tracker triage and the operating rules? | The `agent_operator` owner; whether that is one person or a rotation. |
| Is any engagement or dataset regulated, under a security review, or contractually required to be isolated? | Separate or client-owned workspace instead of a teamspace; stricter integration identities; retention rules. |

## Batch 2 — where knowledge lives today

| Question | What the answer changes |
| --- | --- |
| Where do people open company knowledge today: Notion, Confluence, Google Docs or Drive, SharePoint, Obsidian, a wiki, slides? List the top two. | The source of truth. Prefer the tool people already open daily. |
| How many of those sources currently disagree about positioning, ICP, metrics or terminology? | How much of the first month is migration and reconciliation versus authoring. |
| Is there an existing handbook, wiki or "about us" page a new hire reads? | Seed material for `company_readme` and the Handbook-versus-teamspace split. |
| Does anyone already keep a glossary or metric definitions? Where? | Seed for `glossary` and the metrics catalog; where the ontology fight will happen. |

## Batch 3 — where code and agents live

| Question | What the answer changes |
| --- | --- |
| Which git host do engineers use: GitHub, GitLab, Bitbucket, Azure Repos, other? | Mirror repository, pull-request gate, CI flavour (Actions, GitLab CI, Pipelines, Azure Pipelines). |
| Which agent runtimes are in use or approved: Claude Code or Cowork, Copilot Studio, Gemini, Bedrock, Azure AI Foundry, a framework of your own? | How read rules are installed (marketplace plugin vs pasted instructions vs bundle.json injection). |
| Which connectors or integrations are already approved by IT (knowledge base, CRM, calendar, email, call recordings)? | What the first consumer can reach without a new approval. |
| Is there a plugin or skill registry already, or will this repository's marketplace be the first? | Whether to publish the `company-context` plugin there or install from this repo. |

## Batch 4 — where live data lives

| Question | What the answer changes |
| --- | --- |
| Systems of record for CRM, billing, warehouse or BI, product analytics, support? | Layer 3 inventory; which rows the metrics catalog grounds first. |
| Is there a vector store today (Supabase, pgvector on any Postgres, Pinecone, OpenSearch, Azure AI Search, BigQuery, Vertex)? | Which `schemas/vector/` file to use, or whether to defer retrieval entirely. |
| Does the first consumer need retrieval over long documents, call transcripts or files, or only the canon pages? | Whether a vector store is in scope now. Canon alone fits in a bundle; retrieval needs the store. |
| Call recordings: where do they live and who may read them? | Whether transcripts enter Layer 3, under which visibility, and never into canon. |

## Batch 5 — constraints

| Question | What the answer changes |
| --- | --- |
| Cloud preference or mandate (GCP, AWS, Azure, none)? Data residency rules? | Vector store, secret manager and CI region choices. |
| Secret manager in use (cloud-native, Vault, 1Password, none)? | Where credential references point; whether a secret manager is step one. |
| Who approves a new tool, and how long does it take? | Prefer existing tools; sequence anything new after the pilot. |
| Budget for new SaaS this quarter? | Whether to propose anything paid at all. |

## Batch 6 — the first consumer

| Question | What the answer changes |
| --- | --- |
| Which workflow should read canon first: outbound drafting, a weekly leadership brief, call prep, a client status update, a support macro? | The pages to ground first and the evaluation set. |
| Who runs that workflow today, and what goes wrong (off-message copy, stale numbers, conflicting definitions)? | The gap tracker's first rows and the success criteria. |
| What authority may the first agent have: read only, drafts for review, narrow controlled writes? | `risk_class` of the first deployment; pilot goes no higher than `draft_write`. |
| What would make the sponsor say the pilot worked, in one sentence? | The acceptance test written into the brief. |

## Consultancy-only batch

| Question | What the answer changes |
| --- | --- |
| How many active clients, and how many will be in the pilot (recommend one)? | Hub template now, roll-out later. |
| Do any clients need to chat directly with agents, or only consume agent output through shared pages? | Separate workspace for direct chat; portal pattern otherwise. |
| What do clients see today: a shared page, a deck, an email? | The portal's first views; the publishing gate's first records. |
| What happens at offboarding today: who revokes guests, credentials, schedules? | The offboarding checklist owner; retention rules per client. |
| Is there an existing client tracker (tasks, owners, phases, weeks)? | Keep its fields; relate them to Clients, Engagements and Projects rather than rebuild. |
