# Notion templates

A published sample workspace shows both patterns built in Notion with fictional companies: **Acme Analytics** (one company, one canon) and **Globex Logistics / Vandelay Industries** (a consultancy's hub and spoke). Every page is illustrative; roles stand in for people; every number is a placeholder. Open the root and use **Duplicate** to copy any page or database into your own workspace, then replace the fictional content and the contract IDs.

| Page | What it shows | Repository equivalent |
| --- | --- | --- |
| [Context Engineering — Sample Workspace](https://app.notion.com/p/3f1dbc7f21e08149a8fed4399166cc3f) | The root: both patterns, the shared rules, the swap-any-piece table | `docs/00-start-here.md` |
| [Business Context Layer — Acme Analytics](https://app.notion.com/p/3f1dbc7f21e08184b33ec6a3ebd7897f) | The five pieces, the three layers, the write paths | `docs/01-business-pattern.md` |
| [Canon Index — Acme Analytics](https://app.notion.com/p/3f1dbc7f21e0816b8bb2c636f11cd140) | The llms.txt-style index, the YAML contract with real page IDs, nine canon pages beneath it | `templates/contracts/context-contract.notion.yaml`, `templates/canon/` |
| [Canon Gaps](https://app.notion.com/p/f7ab08c6fb00418ca75ffc43eb3ef86e) | The agent write path with three logged gaps | `templates/databases/canon-gaps.csv` |
| [Metrics Catalog](https://app.notion.com/p/abdbea474ac248d886d14def4d137788) | Definitions and pull methods, never values; grounded, draft and stub rows | `templates/databases/metrics-catalog.csv` |
| [Agent Read Rules](https://app.notion.com/p/3f1dbc7f21e081fa9c54d992410c5fbf) | Drop-in skill text | `templates/canon/operating_rules.md`, `marketplace/plugins/company-context` |
| [Sync & Distribution](https://app.notion.com/p/3f1dbc7f21e0816e83aff96e88f7b43f) | The pipeline, the four artifacts, the two clocks, alternatives per role | `scripts/`, `docs/03-platform-guide.md` |
| [Consultancy Context Layer — Hub & Spoke](https://app.notion.com/p/3f1dbc7f21e081c39cc7e34f87c91e6a) | The shape, the two promises, what changes with many clients | `docs/02-consultancy-pattern.md` |
| [Consultancy HQ](https://app.notion.com/p/3f1dbc7f21e081068317e3502d0344c2) | Clients, Engagements and Agent Deployments databases; information scopes; client hubs as links only | `templates/databases/clients.csv`, `engagements.csv`, `agent-deployments.csv` |
| [Client Delivery Hub — Globex Logistics](https://app.notion.com/p/3f1dbc7f21e08109a897e866b89cb4fb) | The client canon, Work Items, Status Updates, the deployments on the engagement, the permission test | `templates/client-hub/`, `work-items.csv`, `status-updates.csv` |
| [Client Context Contract — Globex Logistics](https://app.notion.com/p/3f1dbc7f21e081939b2afcdcfd94adde) | One contract per client, with real page IDs | `templates/contracts/client-context-contract.yaml` |
| [Project Manifest — PROJ-001](https://app.notion.com/p/3f1dbc7f21e0815da9faeca2019bd66d) | One manifest per deployment, with the rollback named | `templates/contracts/project-manifest.yaml` |
| [Client Portal — Globex Logistics](https://app.notion.com/p/3f1dbc7f21e0816cb769cb52627aa23c) | What the client sees and nothing else | `skills/context-engineering-setup/references/checklists.md` § Publishing |

## Rebuilding it in your own workspace

1. Duplicate the root into a private teamspace. Rename the companies.
2. On the Canon Index, replace every page ID in the contract with the IDs of your duplicated pages (copy from each page's URL). Update `source_root` and `rules.gap_tracker`.
3. Fix property types on the duplicated databases if any imported as text; the select options must equal the contract's slugs plus `new_page`, `decision_log`, `unsure`.
4. Create an internal integration with access to the canon root only; put its token in your CI secret store as `NOTION_TOKEN`; set `source_of_truth: notion` in the contract committed to your mirror repository; run `scripts/canon_sync.py` once by hand, then turn the nightly workflow on by setting the `CANON_SYNC_ENABLED` repository variable to `true`.
5. For the consultancy pattern, give each client its own teamspace or page tree with its own permissions and a separate portal root. Never put a client hub under HQ.

## Why the samples live in their own tree

The sample workspace is a standalone tree with no relations, mentions or backlinks into any real page, so publishing it exposes nothing else. If you publish your own samples, do the same (`docs/05-security-and-isolation.md` § Publishing knowledge-base templates safely).
