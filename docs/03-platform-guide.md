# Platform guide

The pattern is tool-agnostic. The reference implementations used Notion, GitHub, GitHub Actions and Supabase; each role below can be filled by something else without changing the design. The long form, with pick-when and watch-out-for notes per option and three worked recommendations, is `skills/context-engineering-setup/references/platform-matrix.md`; the setup skill uses it to recommend from what you already run.

| Role in the architecture | Used in the reference implementation | Alternatives that fit the same design |
| --- | --- | --- |
| Context layer (canon, delivery state, portals) | Notion | Obsidian or any markdown vault in git, Confluence, Coda, SharePoint, Google Docs with a strict index page |
| Version control and publication gate | GitHub (pull requests) | Bitbucket, GitLab, Azure Repos |
| Scheduled sync and validation | GitHub Actions | GitLab CI, Bitbucket Pipelines, Google Cloud Build and Cloud Scheduler, AWS EventBridge, Azure DevOps Pipelines, n8n or Make |
| Live data and evidence (Layer 3) | Supabase (Postgres plus vector store) beside the CRM and warehouse | GCP (Cloud SQL, BigQuery, Cloud Storage), AWS (RDS, S3, OpenSearch), Azure (SQL, Blob Storage, AI Search), Snowflake, Databricks, Pinecone |
| Vector store (optional) | Supabase pgvector | pgvector on any Postgres, Pinecone, Azure AI Search, Amazon OpenSearch, BigQuery vector search, Vertex; schemas for each in `schemas/vector/` |
| Secret manager | A dedicated secret manager, never the knowledge base | GCP Secret Manager, AWS Secrets Manager, Azure Key Vault, HashiCorp Vault, 1Password |
| Agent runtime and connectors | Claude (Cowork, Claude Code, MCP connectors) | GPT and Copilot Studio, Gemini Enterprise, Amazon Bedrock agents, Azure AI Foundry; any runtime that can read a bundle and call a connector |

## What never changes

- One canonical home per artifact, with a generated read-only mirror. If the source and the mirror disagree, the source wins.
- A machine-readable contract agents fetch by stable ID, never by title search.
- A versioned gate (a pull request or merge request) between authoring and consumption, where the review question is "is this a sane export?" and content is never edited.
- A live system of record for every number, and a catalog that says how to pull it.
- Permissions, not filters, between tenants; a separate identity per client per system.
- A secret manager that is not the context layer.

## Choosing, in one paragraph

Pick the context layer people already open every day. Pick the git host the engineers already use and translate the shipped GitHub workflows to its CI. Add a vector store only when the first consumer needs retrieval over transcripts, long documents or files; the canon alone fits in a bundle. Use the cloud's own secret manager unless Vault or 1Password already exists. Pick the runtime the first consumer runs on; the bundle format keeps every other runtime possible later.

## Adapters in this repository

`scripts/adapters/` ships a markdown adapter (exercised by the test suite and the sample canon), a Notion adapter (REST API, token from the environment, tested offline with fake responses; needs a live workspace to exercise end to end) and a documented Confluence stub. Adding an adapter is one file with one `fetch_page` method; `scripts/README.md` has the steps.
