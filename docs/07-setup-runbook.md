# Setup runbook

A single-session path from "our agents keep asserting stale company facts" to a governed context layer: a thin canon with an owner and a review date on every page, a machine-readable contract agents read, a gap tracker they write to, a metrics catalog that holds definitions but never values, and a nightly sync through a pull-request gate into a read-only mirror. Consultancies add the hub-and-spoke variant so no client ever sees another's content.

Work through it top to bottom. Each step says what to do and how you know it is done. Everything referenced lives in this repository: `justin-gpt/context-engineering-template`.

## 1. What you are building

| Layer | What it holds | Where it lives | Refresh |
| --- | --- | --- | --- |
| 1 — Agent operating files | How agents behave: operating rules, skills, plugins, connector configuration, tests | Git and a plugin marketplace | Continuous |
| 2 — Declared context (the canon) | Durable, human-authored truth: identity, positioning, messaging, ICP, glossary, brand voice, operating rules | Your knowledge base (Notion, a markdown vault, Confluence) | Quarterly; monthly for fast-moving pages |
| 3 — Live data and evidence | Metrics, CRM, billing, product analytics, calls, files; plus a catalog in Layer 2 that defines each metric and how to pull it | Systems of record and stores | Live |

The placement test: if a linter or a skill can enforce it, it is Layer 1. If it is durable truth with a quarter-plus shelf life, it is Layer 2. If it changes daily or is computed, it is Layer 3 and reached live, never copied into a page.

Two patterns share this discipline. **Business**: one company, one canon, one contract. **Consultancy**: a private HQ plus one separately permissioned delivery hub and one portal per client, with a contract per client and a manifest per deployment. Decide which you are in during the interview (section 4); the consultancy pattern is the business pattern repeated inside every client boundary.

## 2. Before you start

You need:

- A GitHub account. GitLab, Bitbucket and Azure Repos work too; the playbook has the translations.
- The knowledge base your team already opens every day: Notion (the reference implementation), a markdown vault in git (Obsidian or plain files), or Confluence. Pick the one people maintain, not the one you wish they maintained.
- Claude Code or Cowork, for the setup skill and the plugins. Optional: the skill is a plain `SKILL.md` any instruction-following agent can run, and agents on other runtimes read the exported `bundle.json` directly.
- Python 3.12 with `pip`, for the scripts. `pip install -r requirements.txt` installs the four dependencies.
- For a Notion canon: an internal Notion integration shared with the canon root page only, with its token stored as a repository secret. Never in a page, a contract, a manifest or a commit.
- Later, and only if retrieval over long documents is a real need: a vector store (Supabase or plain Postgres with pgvector, Pinecone, Azure AI Search, OpenSearch, or BigQuery). Schemas for all six are in `schemas/vector/`.

Budget about twenty minutes for the tour, a working session of two to three hours for the first build, and then days to weeks of owners grounding pages. The build is the smallest part; the pages are the work.

## 3. The twenty-minute tour

See it working before you build your own.

1. Open the published sample workspace: [Context Engineering — Sample Workspace](https://app.notion.com/p/3f1dbc7f21e08149a8fed4399166cc3f). Read the root, then the Acme Analytics business layer and the Globex Logistics delivery hub. Every company in it is fictional; every number is a placeholder.
2. On the repository page, click **Use this template → Create a new repository** and make your copy **private**. Your canon, contract and export will live there; the template stays public.
3. Clone your copy and run the sample sync exactly as the nightly job would:

```bash
git clone https://github.com/<your-org>/<your-copy>.git
cd <your-copy>
pip install -r requirements.txt
python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out export/
python scripts/check_freshness.py export/meta.json --contract templates/contracts/context-contract.yaml
```

4. Open `export/`. Four artifacts: `contract.yaml` (verbatim), `canon/<slug>.md` (each page with a generated header), `meta.json` (the two clocks: `generated_at` for when content last changed, `last_synced_at` for when the sync last ran) and `bundle.json` (everything in one file for single-fetch injection).
5. Install the plugins in Claude Code or Cowork:

```bash
claude plugin marketplace add justin-gpt/context-engineering-template
claude plugin install context-engineering-setup@context-engineering
claude plugin install company-context@context-engineering
```

Then ask Claude to "set up context engineering". The skill's interview starts.

## 4. Pick your path

- **Path A, guided (recommended).** The setup skill interviews you, recommends a stack from what you already run, asks you to approve a decision record, and then builds step by step with your approval at each creation. Section 5.
- **Path B, manual.** Follow the build order in section 6 yourself, using the same templates and playbooks. Choose this when you cannot run the skill or want to understand every piece first.

Both paths end at the same gates (section 8).

## 5. Path A: the guided setup

The skill runs in four phases. Do not let it skip the interview; the tooling is the smallest part.

**Phase 0, orient (two minutes).** It provisionally decides business or consultancy and opens a working file, `context-setup-brief.md`, that becomes your decision record.

**Phase 1, interview (five to eight minutes).** Three to five questions at a time, in this order, because each answer changes what comes next:

1. Shape: one company or many clients; team size; who will own canon pages; whether any engagement is regulated or contractually isolated.
2. Where knowledge lives today, and how many sources disagree. This decides the source of truth.
3. Where code and agents live: git host, CI, agent runtimes, connectors IT has already approved.
4. Where live data lives: CRM, warehouse, billing, product analytics, call recordings; whether a vector store exists and whether retrieval is a real need now.
5. Constraints: cloud preference or mandate, data residency, secret manager in use, who approves new tools, budget.
6. The first consumer: which workflow reads canon first (outbound drafting, a weekly brief, call prep, a client status update). The pages that consumer needs get grounded first.

Answer "we don't know" when it is true. The skill records it as `[YOU DECIDE]` for the owner instead of guessing.

**Phase 2, recommend.** You get a short decision record: one tool per role with a one-line reason and the alternatives considered, the pattern, the canonical page list (at most eight to start, an owner role each), the first consumer, the first agent and its authority tier (`read_only` or `draft_write` for a pilot), and what is deliberately deferred. Approve or adjust it before anything is built.

**Phase 3, set up.** The skill works through section 6 (and section 7 for consultancies), asking before it creates anything in a connected system and showing you the link afterwards. It never pastes a credential; it records references.

**Phase 4, pilot gates and handoff.** It runs the gates in section 8 with you and hands over the brief, a setup log with links to everything created, the list of pages still `draft` with the owner each is waiting on, and the three commands you will run most (section 10).

If the skill runs unattended, it produces the brief and the recommendation and stops before creating anything.

## 6. Path B: the build, business pattern

Work in order. Playbook sections are in `skills/context-engineering-setup/references/setup-playbooks.md`.

**Step 1: Canon index and contract** (playbook A). Create the index page, the `llms.txt` for the company: one line per canonical page, then the contract as a YAML block from `templates/contracts/context-contract.yaml` (markdown source) or `context-contract.notion.yaml` (Notion), with real page IDs filled in. Commit a copy to your repository.
*Done when* `python scripts/validate_contract.py <your-contract>` passes and the contract is in version control.

**Step 2: Canonical pages** (playbook B). At most eight to start, chosen from the nine samples in `templates/canon/`: company README, positioning, messaging, sales storyboard, ICP and personas, competitive battlecards, glossary, brand voice, operating rules. Every page carries an owner role, a status, a review cadence, dates and a visibility; every page starts `draft`; open questions are marked `[CONFIRM]` or `[YOU DECIDE]` inline. Ground `operating_rules` first, then the pages the first consumer needs. No numbers on any page; point to the metrics catalog instead.
*Done when* `operating_rules` is `grounded` with no markers left, and every other page has an owner role and a `next_review` date in the future.

**Step 3: Gap tracker** (playbook C). The database from `templates/databases/canon-gaps.csv`, a child of the index. Its "Suggested page" options must equal the contract's slugs plus `new_page`, `decision_log`, `unsure`. Put its ID in the contract's `rules.gap_tracker`.
*Done when* a test row with a real slug validates and an agent can insert one after a dedup check.

**Step 4: Metrics catalog** (playbook C). From `templates/databases/metrics-catalog.csv`. Definitions and pull methods only; ground the rows the first consumer needs and assign owners in the same motion.
*Done when* the first consumer's metrics have an owner, a definition, a source of truth and a pull method, and no row holds a value.

**Step 5: Agent read rules** (playbook D). Install the `company-context` plugin, or paste `templates/canon/operating_rules.md` into the runtime's instructions and attach `export/bundle.json` as knowledge. The rules: fetch by ID, never by title; assert only `grounded` pages; cite the page URL; numbers come from Layer 3; never edit canon; report gaps.
*Done when* the agent cites a page URL in a test answer and declines to assert a `draft` page.

**Step 6: Sync, mirror and gate** (playbook E). In your repository: Settings → Secrets: `NOTION_TOKEN` (or your knowledge base's token). Settings → Variables: `CONTEXT_CONTRACT` = the contract path. Run the sync locally once and commit `export/`. Run the `canon-sync` workflow by hand (Actions → canon-sync → Run workflow) and read the result. Then set the variable `CANON_SYNC_ENABLED` = `true`; the nightly schedule is a no-op until you do. Allow Actions to create pull requests (Settings → Actions → General) and protect `main`.
*Done when* a manual run succeeded, `export/` validated, and the next scheduled run opened a pull request or committed a heartbeat.

**Step 7: Two clocks and the alert** (playbook F). `check_freshness.py` already runs at the end of the sync job and exits 2 when `last_synced_at` is older than `freshness.stale_after_days`. Point `ALERT_WEBHOOK_URL` at a chat webhook or incident tool, and add a separate daily run so a sync that never starts is still noticed.
*Done when* a deliberately stale `meta.json` fails the check and the webhook receives the payload.

**Step 8: Write paths and delivery surfaces** (playbook G). Three write paths only: report (one gap-tracker row), propose (owner-gated changes to depth databases), publish (agent-owned surfaces such as a briefs database, prep pages or review mirrors). Every agent-owned page ends with a provenance footer; a review mirror carries a banner saying every sync overwrites it. Everyone installs the read plugin; curators also install `context-curator`.
*Done when* no agent identity has edit rights on a canon page and every agent-owned surface has its footer.

**Step 9: Vector store, only if needed** (playbook H). When the first consumer needs retrieval over long documents, calls or files: apply the matching schema from `schemas/vector/`, ingest from `export/bundle.json` with the metadata contract (`tenant_id`, `source_system`, `source_id`, `source_url`, `canonical_slug`, `status`, `visibility`, `content_hash`, `chunk_index`, `generated_at`, `last_synced_at`), and filter every query on tenant, visibility and status. Restricted pages never enter a shared index.
*Done when* a filtered query returns only chunks the caller may see, and deprecated content is deleted rather than flagged.

**Step 10: Review rhythm.** Attach owner re-verification to a meeting that already exists; triage gaps monthly; promote durable conclusions from working documents to canon at quarter close.
*Done when* the rhythm is on a calendar someone already keeps.

## 7. Consultancy additions

Everything in section 6 happens inside each client boundary. Then (playbook I):

**Step 11: Consultancy HQ.** A private teamspace with Clients, Engagements and Agent Deployments from `templates/databases/`. Nothing of a client's lives here; the Clients row carries links to the hub and the portal.

**Step 12: Client hub template.** One separately permissioned hub per client: the four client canon pages from `templates/client-hub/` (README, engagement scope, operating rules, glossary and metrics), Work Items and Status Updates, and `client-context-contract.yaml` on the hub's index page with real IDs.

**Step 13: Project manifest.** One `project-manifest.yaml` per deployment, with the rollback named before any canary and credentials as references only (`secret-manager://…`, `vault://…`).

**Step 14: Portal and publishing gate.** A separate root page with its own permission tree, shared with named client users only. Records move Internal Draft → Approved to Share → Published, and the publishing checklist runs before every publish.

**Step 15: Permission test and offboarding rehearsal.** With a real guest account and the client-scoped integration, before the first client user or integration is invited; rehearse offboarding before the first engagement ends.

*Done when* the Boundary, Portal and Offboarding gates in section 8 pass with real identities.

## 8. Go-live gates

Pass all of them before scaling past the pilot.

| Gate | Pass condition |
| --- | --- |
| Boundary | Representative client, staff, integration and agent identities cannot retrieve content outside their authorized scope |
| Context | The agent answers the agreed evaluation questions from approved sources, cites them, and fails safely on missing or draft context |
| Project truth | Tasks, milestones, status, decisions, risks, deliverables, hours and next actions reconcile on the project page and the weekly update |
| Write control | The agent writes only to designated draft or narrow controlled fields and cannot overwrite canon |
| Portal | Only records in Approved to Share or Published state appear, with no hidden internal fields, relations, comments or attachments |
| Rollback | The prior release, credentials, triggers and portal state can be restored or disabled within the documented response target |
| Offboarding | A rehearsal revokes guest, agent, integration, schedule, webhook and credential access without losing the agreed final record |

A single-company setup runs Context, Write control and Rollback; the other four are consultancy gates.

## 9. The rules you do not break

1. One canonical home per artifact; everywhere else links.
2. No page without an owner role and a review date. Stale is worse than absent.
3. Agents read a contract, assert only `grounded` pages, cite the URL, and fetch numbers live.
4. Agents never edit canon. Report, propose, or publish to agent-owned surfaces.
5. Permissions before filters. A client, a team or a sensitivity level is never a view filter.
6. Retrieved content is evidence, not instruction. Only the operating rules page may direct an agent.
7. No secrets in the context layer, ever.
8. Roles, not people. Nothing reusable names a real client, a private individual, a credential or an internal URL.

Before anything leaves your private copy (a public repository, a published page, a sample deck), run `python scripts/scan_sensitive.py .` with a private denylist of the real names you must keep out, and publish knowledge-base samples only from a tree with no relations, mentions or backlinks into real content.

## 10. Keeping it alive

The three commands you will run most:

```bash
python scripts/canon_sync.py --contract <contract> --out export/          # the sync (nightly in CI; by hand after a big edit)
python scripts/check_freshness.py export/meta.json --contract <contract>  # is the mirror fresh enough to use?
python scripts/scan_sensitive.py . --denylist <file outside the repo>      # before anything is shared
```

| Cadence | Review |
| --- | --- |
| Weekly | Project health, completed and next work, blockers, decisions needed; the portal, for consultancies |
| Monthly | Triage context gaps; review active deployments and failures; retire duplicate or stale records |
| Quarterly | Re-verify canon; review permissions and guest access; evaluate agent releases; review retention and reuse |
| On change | Impact assessment, tests, approval, canary, release, rollback readiness |

## 11. Troubleshooting

| Symptom | Cause and fix |
| --- | --- |
| The sync refuses to mark a page `grounded` | A `[CONFIRM]` or `[YOU DECIDE]` marker remains. Resolve it or keep the page `draft`. |
| A warning says `next_review` is in the past | The owner re-verifies the page and updates `last_reviewed` and `next_review`. Add `--fail-on-warn` to the sync in your copy once owners are reliable. |
| The Notion adapter cannot read a page | The integration is not shared on that page. Share the canon root page with the integration; children inherit. |
| `canon-sync` never runs on its schedule | The repository variable `CANON_SYNC_ENABLED` is not `true`. Manual runs work regardless. |
| The sync ran but no pull request appeared | Settings → Actions → General → "Allow GitHub Actions to create and approve pull requests" is off. |
| Imported CSV columns are plain text in Notion | Fix the property types after import; "Suggested page" must be a Select whose options equal the contract's slugs plus `new_page`, `decision_log`, `unsure`. |
| An agent states a customer count or revenue figure | Numbers never live on a page. Check that the operating rules page is loaded and that the metrics catalog row names a pull method. |
| `claude plugin marketplace add` fails | Claude Code must be installed and GitHub reachable. Without it, paste `skills/context-engineering-setup/SKILL.md` into any agent and attach its `references/` files. |
| `check_freshness.py` exits 2 | The heartbeat is older than `freshness.stale_after_days`. Look at the last sync run before trusting the mirror. |

## 12. Where everything is

- Repository: [github.com/justin-gpt/context-engineering-template](https://github.com/justin-gpt/context-engineering-template) (start with `docs/00-start-here.md`)
- Sample Notion workspace: [Context Engineering — Sample Workspace](https://app.notion.com/p/3f1dbc7f21e08149a8fed4399166cc3f) (duplicate any page into your own workspace)
- The setup skill: `skills/context-engineering-setup/` (interview bank, platform matrix, playbooks, checklists, brief template)
- Templates: `templates/` (contracts, canon pages, client hub pages, database CSVs)
- Schemas: `schemas/json/` and `schemas/vector/`
- Scripts and CI: `scripts/`, `.github/workflows/`
- Security rules for contributions and publishing: `SECURITY.md`, `docs/05-security-and-isolation.md`

Built by [Justin GPT](https://justingpt.ai). MIT licensed; fictional data only.
