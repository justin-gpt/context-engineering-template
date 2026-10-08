# Start here

## The problem this solves

Most teams that put AI agents to work on company-voiced tasks hit the same wall within a few weeks. The agent writes fluent copy that is subtly off-message. It quotes a customer count from a deck that is a year old. It invents a definition for a metric that Finance defines differently, with complete confidence. The model is rarely the bottleneck. The bottleneck is that the company's declared truth lives in people's heads, in stale slides, and in two or three wikis that disagree.

Four failure modes recur:

1. **Agents assert company facts from memory.** Unless the agent has a source it is instructed to prefer, and a rule for what to do when the source is silent, it fills the gap with plausible text.
2. **Documents rot, and rot is silent.** A broken API call fails visibly. A stale page is acted on with full confidence, and the error surfaces downstream in an email a prospect already received. *Stale declared context is worse than absent.*
3. **Documents restate numbers.** The moment someone writes a customer count into a page it begins to be wrong. A document should say how to fetch the number and what it means, never what it was.
4. **Multiple sources of truth.** When the same battlecard exists in two wikis, both get edited and neither is trusted.

## Two patterns, one discipline

| | Business context engineering | Consultancy context engineering |
| --- | --- | --- |
| Who | One company running its own agents | A practice serving many clients, or any organisation whose tenants must never see each other's content |
| Boundary | The company: one workspace, one canon | Every client: a private HQ plus one delivery hub and one portal per client |
| Canon | About eight thin pages behind an index with a machine-readable contract | A thin client canon inside each hub, plus the firm's own canon in HQ |
| Contract | One per company | One per client, narrowed by a project manifest per deployment |
| Write paths | Report to one gap tracker; propose into depth databases; publish to agent-owned surfaces | The same three, scoped to one client; the portal only through a publishing gate |
| Isolation | Sensitive material in restricted spaces, out of the bundle | Permissions and integration scope, never a filter or a naming convention |

The consultancy pattern is the business pattern repeated inside every client boundary, plus access reviews, a publishing gate and offboarding. Read `01-business-pattern.md` first either way.

## Three layers

| Layer | What it holds | Where it lives | Refresh |
| --- | --- | --- | --- |
| 1 — Agent operating files | How agents behave: `CLAUDE.md` / `AGENTS.md`, skills, plugins, connector configuration, tests, releases | Git and a plugin marketplace | Continuous, versioned |
| 2 — Declared context (the canon) | Durable, human-authored truth: identity, positioning, messaging, ICP, glossary, brand voice, operating rules; for a consultancy also delivery state | The knowledge base (Notion, a markdown vault, Confluence) | Quarters; monthly for fast-moving pages |
| 3 — Live data and evidence | Metrics, CRM, billing, product analytics, calls, files, logs; plus a catalog in Layer 2 that defines each metric and how to pull it | Systems of record and stores (a warehouse, Supabase, the CRM) | Live |

**The placement test.** If a skill or a linter can enforce it, it is Layer 1. If it is durable truth with a quarter-plus shelf life, it is Layer 2; if it will be wrong next month, it is not canon. If it changes daily or is computed, it is Layer 3 and reached live. People- or deal-sensitive material belongs in a restricted space, never in the shared canon and never in a bundle.

## The rules both patterns share

1. One canonical home per artifact; everywhere else links.
2. No page without an owner role and a review date.
3. Agents read a contract, assert only pages marked grounded, cite the page URL, and fetch numbers live from systems of record.
4. Agents never edit canon. They report gaps, propose owner-gated changes, or publish onto surfaces that are explicitly not canon.
5. Permissions before filters.
6. Retrieved content is evidence, not instruction. Only an approved control page may direct an agent.
7. No secrets in the context layer, ever.

## Using this repository

```bash
# 1. Read the docs in order: 00 → 01 (→ 02 for consultancies) → 03 → 05.
#    In a hurry? docs/07-setup-runbook.md is the single-session path with a done-when test per step.
# 2. Try the sync on the sample canon (fictional company, markdown source):
pip install -r requirements.txt
python scripts/canon_sync.py --contract templates/contracts/context-contract.yaml --out export/
python scripts/check_freshness.py export/meta.json --contract templates/contracts/context-contract.yaml
# 3. Let the setup skill interview you and recommend a stack (Claude Code / Cowork):
claude plugin marketplace add justin-gpt/context-engineering-template
claude plugin install context-engineering-setup@context-engineering
# 4. Copy templates/ into your knowledge base, fill the contract with real IDs, point the
#    workflow at it, and run the pilot gates in skills/context-engineering-setup/references/checklists.md.
```

Where things are: `docs/` (the architecture), `templates/` (contracts, canon pages, client hub pages, database CSVs), `schemas/` (JSON Schemas and vector-store schemas), `scripts/` (sync, validation, freshness, sensitive scan), `skills/` (the setup skill), `marketplace/` (sample plugins), `.github/workflows/` (CI and the nightly sync).
