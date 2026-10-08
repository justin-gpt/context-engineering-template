# Business context engineering: one company, one canon

The single-company pattern, distilled from a working implementation at a mid-sized B2B SaaS company where the CEO's office, product marketing and revenue operations stood the system up over roughly eight weeks and ran a plugin marketplace, a nightly sync, several in-house data agents and knowledge-base-native agents against it. Identifiers and company specifics are removed; the patterns, schemas and operating rules are reproduced so another team can copy them.

## The architecture on one page

People own and edit canonical pages in the knowledge base. A scheduled sync exports those pages, through a pull-request gate, into a read-only mirror repository and a plugin bundle that agents install. Agents read the bundle first, fall back to the live source when freshness or status matters, assert only content marked grounded, cite page URLs, resolve any number through the Layer 3 catalog's pull method against the live system, report gaps into a tracker instead of editing canon, and publish their own outputs onto agent-owned surfaces that are explicitly not canon. (`diagrams.md` § 1.)

Two ideas carry most of the weight: the **three-layer separation** (`00-start-here.md`) and the **context contract**, a small machine-readable block on one page that tells every agent which pages are canonical, what status each has, who owns it and how it may be used. Everything else is plumbing and discipline around those two ideas.

## Layer 2 in depth: the canon

### The canon index: an llms.txt for the company

One stable entrypoint page lists the canonical pages with a one-line description each, deliberately following the llms.txt convention: instead of letting an agent crawl a workspace and weigh a two-year-old draft equally with ratified positioning, the index points at authoritative content and nothing else. The reference set is eight pages, and eight is a ceiling rather than an accident: company README, positioning, messaging, sales storyboard, ICP and personas, competitive battlecards (a thin page over a depth database), glossary and product ontology, brand voice. This template adds a ninth, `operating_rules`, as the one page allowed to direct an agent. Samples: `templates/canon/`.

### The context contract

Below the human-readable index sits a YAML block (`templates/contracts/context-contract.yaml`, format in `formats.md` § 1). Agents parse it and ignore the surrounding prose. Three rules every downstream skill inherits: **assert only pages with status grounded; always cite page URLs; live numbers come from Layer 3, never from canon text.** A fourth lives in the skills: if the contract block is missing or unparseable, the agent stops and says so.

Why YAML on a page rather than a database? A code block is trivially exportable, diffable, version-controlled by the sync, and keeps the interface stable while the workspace is restructured. The trade-off is that the knowledge base cannot run views, rollups or reminders over it; the hardening roadmap below mirrors the contract into a database for exactly that.

### The status ladder

| Status | Meaning | How agents use it |
| --- | --- | --- |
| grounded | Verified, canonical | Assert freely; cite the page URL |
| draft | Written but unverified | Use, but label facts as unconfirmed in the sentence |
| stub | Guidance only | Never treat as truth; never load as context; note the coverage gap |
| deprecated | Superseded | Do not use; follow the replacement link |

New or materially changed content starts as draft until the owner verifies it. Because a page can be mostly right and partly open, pages carry per-section or per-term tags (each glossary term GROUNDED or GENERIC) so that a page that is draft overall still has assertable parts. Open questions are marked `[CONFIRM]` (check this) and `[YOU DECIDE]` (a choice only the owner can make). An unresolved marker blocks verification; the sync enforces it.

### Page metadata and change logs

Every canonical page opens with the same block: owner (a role, not a person), review cadence, last reviewed, next review. Review cadence rides an existing rhythm (quarterly planning, the monthly GTM review), never a standalone task that competes for attention. Every page ends with a dated change log recording what changed and why; it is the audit trail humans and automated reviewers read, and in practice it caught cases where a caveat was dropped from a line while the log still asserted it was in place. Pages also carry a Sources and depth section: where each claim came from, and where the deeper material lives.

### Depth layers

Canon pages stay thin. Enablement and reference detail lives in a depth layer that exists only in the knowledge base: a small page shelf when there are a handful of related pages, a database when there are many like-shaped items (one row per competitor behind the battlecards page). Depth pages are **not in the contract and not exported**. Repo-grounded agents receive pointers, not depth content; agents with the connector query depth live. If a depth page conflicts with canon, canon wins.

### Governance rules that make it hold

- **No page without an owner and a review date.** Once people and agents hit a stale page a few times they stop trusting the whole system and route around it.
- **Single source of truth.** One canonical page per artifact. Cross-link, never duplicate.
- **Prune aggressively.** If deleting a line would not cause a person or an agent to make a mistake, cut it.
- **Keep root pages short.** A thin, high-signal page that points to depth beats a long page nobody reads to the end.
- **Agents never edit canon.** They report gaps to the tracker for a human owner to resolve.
- **Conclusions go to the governing artifact.** A conclusion that lands only in a working document or a chat is invisible to agents and to the mirror; that is how truth forks.
- **Metrics never live in canon.** Canon states the definition and the decision and points at the data.

## Layer 3 in depth: the metrics catalog

Layer 3 is mostly systems that already exist. What the architecture adds is a **metrics catalog** (`templates/databases/metrics-catalog.csv`) that stores, for every KPI, its definition and its live-pull method, and never a value. Each row carries a name and short ID, definition, formula and grain, source-of-truth system, the exact query or explore or agent call with the date it was last verified, a status (stub / draft / grounded), an availability verdict (measurable / implied / absent), domain, value-chain stage, cadence, role (north-star or guardrail), owner, reconciliation notes and related rows.

The pull method frequently encodes hard-won reconciliation: which currency-converted field to sum, why a raw amount field overstates by a factor of two, which filter separates new business from renewals, why weekly deltas must be date-stamped rather than differenced from cumulative snapshots. Those notes are the real asset; they are what stops two agents from producing two truths from the same warehouse.

Build it in stages: derive the candidate set, draft definitions, audit against source systems, reconcile with the owning function, then govern. Ground the rows a real consumer executes against first (a weekly leadership brief, forecast prep), because those consumers expose ambiguity fast. Assign the owner in the same motion as grounding, or the catalog becomes another unowned document.

## Distribution: getting canon into agents

### The sync pipeline

A scheduled routine (nightly in the reference implementation) reads the contract through the knowledge base's API or connector, exports each canonical page to markdown, and writes four artifacts: `contract.yaml`, `canon/<slug>.md` with a generated header, `meta.json`, `bundle.json` (`formats.md` § 5; `scripts/canon_sync.py`). One export feeds two consumers: the mirror repository and the references folder inside the company-context plugin in the marketplace. Pages the sync cannot read are exported as explicit placeholders so no agent mistakes a placeholder for canon.

**Validation gates** fail the sync if the contract does not parse or lacks a required slug, if any slug has neither an export nor a `pages_missing` entry, or if any file lacks its header; they warn when the bundle exceeds roughly 150 KB or a page is past its review cadence. **Publication is a pull request.** Review is "does this look like a sane export," never content editing. Merging bumps the plugin's patch version, and auto-updating plugins deliver the fresh bundle to every consumer. Two governance lines close the loop: nobody edits the repository (if the source and the mirror disagree, the source wins), and access is never broadened by syncing.

### Two clocks

`generated_at` advances only when bundle content changed; it drives the pull request and the version bump and is what consumers cite. `last_synced_at` advances on every successful run; it is the freshness heartbeat. A quiet canon stays fresh, and only a sync that stops running trips the staleness check. Alert on the heartbeat from day one; the reference implementation found an eleven-day-old heartbeat against a seven-day threshold with nobody paged. Skills treat a stale heartbeat as "verify statuses live," not as "bundle unusable."

### The read order inside an agent

First the bundled snapshot, cited as canon as of `generated_at`. Second, the live source: when the heartbeat is older than seven days, when the user asks for the latest, when a page's status matters for an outward-facing deliverable, or when a page is missing from the bundle. Third, fail loudly: if neither is reachable, say so; never substitute company facts from memory. Pages are always fetched by ID, never by title search. The skill exposes three operations: get the context index, get one page by slug, get a task-relevant bundle (for outward drafting: positioning, messaging, brand voice, storyboard; glossary when terminology matters; ICP and battlecards for GTM work), filtered to grounded. Drop-in text: `templates/canon/operating_rules.md`; installable form: `marketplace/plugins/company-context`.

### Context economy

Context is finite and bloat buries the lines that matter. Load only the pages a task needs; summarize the less relevant ones when a bundle exceeds about 4,000 words. The reference bundle sat near 144 KB with the glossary a third of it, which is what forces the thin-canon, deep-shelves discipline.

## Write paths: report, propose, publish

Graded by risk to company truth (`diagrams.md` § 4).

**Report, never edit.** Agents never edit canon or Handbook pages, not even with approval in the moment, because an in-place patch bypasses the owner review, the marker discipline and the change log that make the page trustworthy. A Canon Gaps database, a child of the index page, is the write path (`formats.md` § 6). Dedup-check before inserting; route definitional failures to the glossary; one row per gap; confirm with the row URL. The gaps a real tracker collects are instructive: two pages disagreeing on a headline figure because they measured different things; terminology drift between two spellings; a glossary with no metric definitions, then four formula conflicts once definitions were imported; competitors present in CRM loss data but absent from any battlecard; a CRM field populated on under a tenth of records, so every claim built on it had to be labeled directional.

**Propose, owner-gated.** Depth databases are where agents add value on a cadence and where the risk of quietly promoting an unverified claim is highest. The battlecard refresh is the model: the mechanical layer (refresh snapshots with an as-of date, append dated and cited evidence, tag unconfirmed claims, supersede rather than delete, append a review-log entry) is applied; the judgment layer (status transitions, tag removals, tier moves, retirements, any change to the canon page's table) is drafted as proposals. The agent proposes; the owner verifies. The only exception: the directing user is the page owner and explicitly approves a named change in the session.

**Publish, agent-owned surfaces.** Where an agent is the author of record it writes directly onto surfaces that are explicitly not canon: a weekly brief database (one row per week), prep pages in a shared document hub (each ending with a Sources footer naming the systems and agents queried and anything skipped), and read-only mirrors of long-form drafts pushed from a repository for review, with a banner saying edit in the repo, every sync overwrites this page, comments are harvested back. Working research lives as markdown in its project folder and, the moment anyone else must cite it, as an entry in a research database; conclusions go to the governing artifact.

**Drift detection.** A wrap-up skill reviews a session for durable changes, fetches the Handbook pages in scope by ID, and reports what is missing, contradicted, partial or lapsed. It never writes the page; it hands the drift to the authoring path (`marketplace/plugins/context-curator`).

**Split read tooling from write tooling.** After two months the reference team split the plugin: the read side (load canon, report a gap) installed broadly; the write side (populate pages, migrate, file research) for a handful of curators. Bundling the two had shipped five write-path skills to everyone who only wanted positioning in a draft.

## Knowledge-base-native AI alongside external agents

Native assistants are good at finding the canonical destination for a new page, assessing placement, improving structure, reviewing consistency across related pages and flagging staleness. Point them at the canon index so their answers are status-aware and cite the same pages external agents do. The knowledge base's verification badge is the human-facing trust signal; "unverified means draft" is the one-sentence version for people, mirroring the contract's ladder for machines. Keep the two signals connected (roadmap, below).

## Information architecture that makes the layer possible

**Three content systems, one job each.** The knowledge base holds uncontrolled company knowledge: the Handbook is the single source of truth for how the company operates; functional teamspaces are where work happens. A controlled-document system holds SOPs, policies and anything needing an approval workflow or audit trail; the Handbook indexes it with pointers, never copies. A file store holds files and working artifacts.

**Handbook versus teamspace.** Would a new hire read it to learn how we operate, where there should be exactly one version? Handbook. Do you use it to do the work, whether it ends (a PRD) or runs continuously (an issues register)? Teamspace. A PRD never migrates to the Handbook; the decisions it produced get promoted.

**A standard teamspace template.** Every function's teamspace has the same five sections and no more: OKRs (one database), Projects (one database, each row the project's home), Meetings (what each instance produces), Registers (live operational surfaces that are never done), and an optional restricted Processes section. Anti-patterns: no catch-all document database (one lasted three days), no process docs squatting in the teamspace, no restated metrics, nothing decision-bearing that stays only in the teamspace, databases rather than page trees for anything with a repeated shape.

**Migration from a legacy wiki.** Inventory before moving; a disposition table with one row per page; stop for the owner's confirmation; find the canonical destination first and update it; treat legacy content as claims to verify; leave originals untouched until a single deliberate freeze; a post-migration check for images, attachments and macros (`marketplace/plugins/context-curator/skills/migrate-legacy-wiki`).

## What running it taught

| Area | Observation | Why it matters for you |
| --- | --- | --- |
| Freshness drift is silent | A heartbeat eleven days old against a seven-day threshold; a cleared caveat still hedged in the bundle; nothing alerted anyone | The two-clock design only helps if someone is paged. Freshness must be observable, not merely checkable |
| Ratification is the bottleneck | Three of eight pages still draft after two months, the glossary among them; all depth cards pending | Authoring is fast once agents help. Owner verification is a human act on a human calendar. Budget and instrument it |
| The gap backlog ages | Twelve of fourteen gaps open; the tracker's schema narrower than the reporting skill documented | Validate the tracker schema in the sync like the contract; set a triage expectation and a monthly digest |
| Layer 3 ownership lags grounding | Most catalog rows unowned and stub | Ground rows in the order a consumer needs them and assign the owner in the same motion |
| Two trust signals, not yet connected | Every page unverified in the knowledge base although the stated human signal is the verified badge | Contract status and page verification should agree, or people learn to ignore one |
| Isolation creates dead links | Restricted spaces returned not-found; a page linked a log removed from the contract weeks earlier | Run a link and access check in the sync; export explicit restricted placeholders |
| Documentation surfaces split | The plugin catalog and change log on the legacy wiki, weeks behind the repository | Decide where the record lives and declare everything else legacy |
| The system page drifted | The page describing the sync disagreed with the sync's own specification | The page documenting the system needs the same owner-and-review discipline as the canon |
| Adoption, not tooling, is the gap | Usage concentrated in one agent; field teams did not know when to load context | Make loading canon the default inside drafting skills, not a command users must remember |

## Hardening roadmap

**Tier 1, close the silent-failure gaps:** alert on the heartbeat and print freshness on every load; validate the gap tracker schema in the sync and add a triage expectation; run a ratification sprint and formalize partial grounding. **Tier 2, connect what exists:** mirror the contract into a database so reminders and rollups work; link contract status to page verification with an expiry matching the review cadence; give every grounded catalog row an owner and a verified-on date; check links and access during the sync. **Tier 3, extend:** consolidate documentation surfaces; instrument canon loads alongside agent telemetry; point native agents at the contract; declare depth pages in the contract with `exported: false`; run evaluations from `bundle.json`.

## Getting started: ten steps

1. Pick at most eight canonical pages; assign a role owner and a review cadence; write the metadata block; start every page as draft.
2. Create the canon index: one line per page, then the contract. Nothing else on that page.
3. Create the gap tracker as a child database of the index.
4. Stand up the metrics catalog with definitions and pull methods only; ground the rows your first brief needs and assign owners as you go.
5. Write the agent read rules into a skill or plugin; declare the connector as a dependency; fetch by page ID.
6. Build the sync: export, pull request, validate, version bump on merge.
7. Add the two clocks and the live-fallback rule; alert on the heartbeat from day one.
8. Decide your depth layers; keep them out of the bundle; state that canon wins on conflict.
9. Define the three write paths and put agent outputs on agent-owned surfaces with a provenance footer.
10. Wire the review rhythm onto meetings that already exist; triage gaps monthly; promote durable conclusions at quarter close.

**The one rule that makes the rest work:** no page without an owner and a review date. Stale is worse than absent, because an agent acts on it confidently instead of failing visibly.
