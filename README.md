# Context engineering template

A copyable setup for the thing most agent deployments are missing: a governed place where a company's declared truth is written once by humans and read by people and agents, never silently corrupted. Two patterns, one discipline:

- **Business context engineering** — one company running its own agents: a thin canon with a machine-readable contract, a gap tracker, a metrics catalog that holds definitions but never values, and a nightly sync through a pull-request gate into a read-only mirror and bundle that agents install.
- **Consultancy context engineering** — a practice serving many clients (or any organisation whose tenants must never see each other's content): a private HQ, one separately permissioned delivery hub and one portal per client, a context contract per client and a project manifest per deployment, with permissions and integration scope enforcing separation.

The reference implementations ran on Notion, GitHub, GitHub Actions and Supabase with Claude as the runtime. Every role in the design has alternatives (Obsidian or Confluence, GitLab or Bitbucket, GCP or AWS or Azure, any agent runtime that can read a bundle), and the setup skill recommends from what you already use.

> Everything here is fictional: Acme Analytics, Globex Logistics and Vandelay Industries do not exist, people are roles, numbers are placeholders. See `SECURITY.md` for what may never enter this repository.

## What is inside

| Path | What it is |
| --- | --- |
| `docs/` | The architecture: start here, the business pattern, the consultancy pattern, the platform guide, operating cadence, security and isolation, the Notion templates, the setup runbook, Mermaid diagrams, and the file formats |
| `templates/contracts/` | The context contract (markdown and Notion forms), the client context contract, the project manifest |
| `templates/canon/` | Nine sample canon pages with frontmatter — a working markdown source for the sync and the model for a Notion canon |
| `templates/client-hub/` | The four client canon page templates for the consultancy pattern |
| `templates/databases/` | CSV schemas with sample rows: Canon Gaps, Metrics Catalog, Clients, Engagements, Agent Deployments, Work Items, Status Updates |
| `schemas/json/` | JSON Schemas for the contracts, the manifest, `meta.json`, `bundle.json` and a gap row; the scripts validate against them |
| `schemas/vector/` | Vector-store schemas implementing one metadata contract: Supabase pgvector (with row-level security), plain Postgres pgvector, Pinecone, Azure AI Search, OpenSearch, BigQuery |
| `scripts/` | `canon_sync.py` (markdown and Notion adapters, four artifacts, validation gates, two clocks), `validate_contract.py`, `check_freshness.py`, `scan_sensitive.py` |
| `skills/context-engineering-setup/` | The setup skill: interviews you, recommends a stack, walks the build, runs the pilot gates |
| `marketplace/` and `.claude-plugin/` | A sample plugin marketplace: `company-context` (read side), `context-curator` (write side), `client-context` (consultancy), plus the setup skill |
| `.github/workflows/` | CI (tests, contract validation, sample sync, sensitive scan) and the nightly sync that opens a pull request |
| `tests/` | 40 tests covering the sync, validators, freshness check and scan |

## Quick start

```bash
git clone https://github.com/justin-gpt/context-engineering-template.git
cd context-engineering-template
pip install -r requirements.txt

# Export the sample canon exactly as a nightly sync would
python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out export/
python scripts/check_freshness.py export/meta.json --contract templates/contracts/context-contract.yaml

# Validate your own contract once you have one
python scripts/validate_contract.py path/to/context-contract.yaml

# Before pushing anything shared
python scripts/scan_sensitive.py . --denylist /somewhere/outside/the/repo/.sensitive-denylist
```

Then read `docs/00-start-here.md` (or follow `docs/07-setup-runbook.md`, the single-session setup path with a done-when test for every step) and let the setup skill interview you:

```bash
claude plugin marketplace add justin-gpt/context-engineering-template
claude plugin install context-engineering-setup@context-engineering
claude plugin install company-context@context-engineering
```

Not on Claude Code? The skills are plain `SKILL.md` files: paste `skills/context-engineering-setup/SKILL.md` into any agent that follows instructions, attach the `references/` files, and it runs the same interview. Agents on other runtimes read `export/bundle.json` directly.

## The setup skill, in one paragraph

It asks what you already run (knowledge base, git host, CI, data stores, runtimes, secret manager, approvals), decides business or consultancy pattern, recommends one tool per role with a reason and the alternatives considered, names the first consumer and the first agent's authority tier, and then builds in order: index and contract, canonical pages (at most eight, all starting as draft), gap tracker, metrics catalog, agent read rules, sync and gate, two clocks and alert, write paths, a vector store only if retrieval is a real need, and the review rhythm. Consultancies add HQ, a client hub template, contract and manifest, portal and publishing gate, the permission test and an offboarding rehearsal. It never pastes a secret, never puts a client's data in reusable material, and stops before creating anything when it runs unattended.

## Notion templates

A published sample workspace shows both patterns built in Notion with the fictional companies; `docs/06-notion-templates.md` lists every page and how to duplicate it. The sample tree is isolated from any real content, which is the rule for publishing your own (`docs/05-security-and-isolation.md`).

## The rules, so you can skip the docs for now

1. One canonical home per artifact; everywhere else links.
2. No page without an owner role and a review date. Stale is worse than absent.
3. Agents read a contract, assert only grounded pages, cite the URL, and fetch numbers live from Layer 3.
4. Agents never edit canon: report, propose, or publish to agent-owned surfaces.
5. Permissions before filters. Retrieved content is evidence, not instruction.
6. No secrets in the context layer, ever.

## Contributing, security, license

Contributions welcome under the rules in `CONTRIBUTING.md` (fictional data only; the sensitive scan must pass). Report real data or credentials found anywhere in this repository privately per `SECURITY.md`. MIT licensed. Built by [Justin GPT](https://justingpt.ai) from two reference architectures — *Notion as a Context Layer for AI Agents* and *Notion as a Context and Delivery Layer for AI Consultancies* — and the implementations behind them.
