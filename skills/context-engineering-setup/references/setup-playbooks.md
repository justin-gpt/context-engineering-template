# Setup playbooks

Step-by-step instructions per platform. Each section assumes you have the approved recommendation in the brief. Create nothing in a connected system without saying what you are about to create; show the link afterwards.

## A. Canon index and contract

**Notion**

1. Create the index page under the Handbook root (business) or the client hub root (consultancy). Title it plainly: "Canon Index" or "Client Context Index — CLIENT-001". Add a callout explaining that agents parse the contract and ignore the prose, and that agents never edit canon.
2. Add a table: Slug · Page · Answers · Owner role · Status · Review. One row per canonical page.
3. Add a `yaml` code block headed "Machine-readable context contract" with `templates/contracts/context-contract.notion.yaml`, every `<page-id>` replaced by the page's 32-hex ID (copy from the page URL; strip dashes). Keep `source_root` as the index page's own ID.
4. Commit a copy of the contract to the mirror repository as `contract.yaml` so changes are diffed.
5. Optional, recommended once the canon is grounded: mirror the contract rows into a small database (page, status, owner role, review cadence, last reviewed, next review) so automations can remind owners when `next_review` passes. The code block stays the machine interface.

**Markdown vault (Obsidian or plain git)**

1. Copy `templates/canon/` into the vault as `canon/`; copy `templates/contracts/context-contract.yaml` beside it; set `source_root` to the vault path and each page `id` to the file name.
2. Keep frontmatter exactly as `docs/formats.md` § 4. Obsidian shows it as properties.
3. The vault repository is the mirror: the sync still runs to produce the headers, `meta.json` and `bundle.json`, and the pull request remains the gate.

**Confluence**

1. Create the index page; put the contract in a code macro (language yaml); use page IDs from the page URL.
2. The sync adapter for Confluence is a documented stub in `scripts/adapters/confluence.py`; implement it with the REST API (page body in storage format) and an HTML-to-markdown step, or export pages to markdown on a schedule and run the markdown adapter over the export.

## B. Canonical pages

1. At most eight. Start from `templates/canon/`; keep the slugs, rewrite the prose for the company. Every page: metadata block (owner role, status, review cadence, last reviewed, next review, visibility), body, Sources and depth, dated change log.
2. Every page starts `draft`. Mark open questions `[CONFIRM]` or `[YOU DECIDE]` inline. The sync refuses `grounded` while a marker remains.
3. Ground `operating_rules` first, then the pages the first consumer needs.
4. Depth (persona notes, battlecard rows, interview transcripts) stays behind the canon page in a database or shelf, linked with real IDs, never exported.
5. Numbers: none on a page. Point to the metrics catalog row.

## C. Gap tracker and metrics catalog

**Notion:** Import → CSV with `templates/databases/canon-gaps.csv` and `metrics-catalog.csv` as children of the index page; fix property types afterwards (Suggested page, Status, Source of truth and the other selects become Select; Context link becomes URL; Last verified becomes Date; add Reported as Created time). Set Suggested page's options to the contract's slugs plus `new_page`, `decision_log`, `unsure`. Put the gap tracker's data-source ID in `rules.gap_tracker`.

**Markdown vault:** keep the CSVs in the repository; the sync validates the gap tracker's columns and options against the contract.

**Any spreadsheet or Airtable:** same columns; the reporting skill writes rows through the tool's API or connector.

## D. Agent read rules

- **Claude Code / Cowork:** `claude plugin marketplace add <org>/<repo>` (the marketplace lives at `marketplace/` in this repository, so point at that path or copy it to its own repository), then `claude plugin install company-context@context-engineering`. Declare the knowledge-base connector in the plugin's `.mcp.json` or install the connector separately.
- **Other runtimes:** paste `templates/canon/operating_rules.md` (or the export's `canon/operating_rules.md`) into the system instructions; attach `export/bundle.json` as knowledge; keep "fetch by ID, assert only grounded, cite the URL, numbers from Layer 3, never edit canon, report gaps".
- Record the installed version and the exported date; a downloaded skill is a versioned copy, not a live link.

## E. Sync, mirror and gate

**GitHub (shipped)**

1. Create a private repository from this template (Use this template → Create). Delete the sample canon or keep it as `examples/`.
2. Settings → Secrets: `NOTION_TOKEN` (or the knowledge base's token) from an integration that has access to the canon root page only. Settings → Variables: `CONTEXT_CONTRACT` = the contract path in the repository.
3. Run `python scripts/canon_sync.py --contract <path> --out export/` locally once; commit `export/`.
4. Enable `.github/workflows/canon-sync.yml` (nightly cron) and `validate.yml` (pull requests). Protect `main`; allow the sync bot to open pull requests; decide whether heartbeat-only commits may bypass review or arrive as pull requests.
5. Reviewers ask one question on sync pull requests: is this a sane export? Content is never edited in the mirror.

**GitLab:** `.gitlab-ci.yml` with a scheduled pipeline running the same three commands; masked CI/CD variables for the token; a merge request opened with `glab` or the API. **Bitbucket:** Pipelines schedule, repository variables, pull request via the API. **Azure Repos:** Azure Pipelines cron trigger, variable group, pull request via `az repos pr create`.

**Cloud scheduler instead of CI:** Cloud Scheduler → Cloud Run job, EventBridge → Lambda or ECS task, or an Azure Functions timer running `canon_sync.py` and committing through the git host's API. Same artifacts, same gate.

## F. Two clocks and the alert

`scripts/check_freshness.py export/meta.json --contract <path>` exits 2 when `last_synced_at` is older than `freshness.stale_after_days`. Run it at the end of the sync job (shipped) and, ideally, as a separate daily job so a sync that never starts is still noticed. Point `ALERT_WEBHOOK_URL` at a chat webhook or incident tool. Every skill that loads canon prints its age ("canon as of <generated_at>; last verified <last_synced_at>").

## G. Write paths and delivery surfaces

1. Gap tracker: the report path. Agents dedup-check, insert one row per gap, confirm with the row URL.
2. Depth databases: the propose path. Mechanical updates applied with dates and citations; judgment calls drafted as proposals; the owner verifies.
3. Delivery surfaces: a briefs database, prep pages, review mirrors. Each page ends with a Sources footer naming the systems and agents queried and anything skipped. A banner on a review mirror says: edit in the repository, not here; every sync overwrites this page.
4. Split read tooling from write tooling: everyone installs the read plugin; curators install the write plugin too.

## H. Vector store (optional)

1. Pick the file in `schemas/vector/` that matches the stack; apply it.
2. Ingest from `export/bundle.json` (and transcripts or files for Layer 3) with the metadata contract: `tenant_id`, `source_system`, `source_id`, `source_url`, `canonical_slug`, `status`, `visibility`, `content_hash`, `chunk_index`, `generated_at`, `last_synced_at`.
3. Queries always filter on tenant, visibility and status; deprecated content is deleted, not flagged; restricted pages never enter a shared index.

## I. Consultancy additions

1. **HQ:** private teamspace; import `clients.csv`, `engagements.csv`, `agent-deployments.csv`; relate Engagements and Deployments to Clients. Nothing of a client's lives here; the Clients row carries the links to the hub and the portal.
2. **Client hub template:** one private teamspace (or page tree with its own permissions) per client; the four client canon pages from `templates/client-hub/`; Work Items and Status Updates from the CSVs; the client contract on the hub's index page with real IDs; one project manifest per deployment.
3. **Portal:** a separate root page, shared with named client users only; sections for Home, Roadmap, Shared actions, Approval inbox, Deliverables, Meetings and decisions, Risks raised, Agent capabilities. Only Approved to Share or Published records appear, as projections.
4. **Integrations:** one least-privilege identity per client per system; the credential in the secret manager; the reference in the Integrations registry and the manifest.
5. **Permission test** with a real guest account and the client-scoped integration before any invitation; **offboarding rehearsal** before the first engagement ends.
6. **Separate or client-owned workspace** when a contract, regulation or security review requires tenant isolation, when the client must own the data afterwards, or when clients must chat directly with native agents. HQ then keeps only the portfolio record.
