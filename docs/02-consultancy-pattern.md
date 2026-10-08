# Consultancy context engineering: hub and spoke with hard client boundaries

How to use a knowledge base as the shared coordination layer between a consultancy and its clients while keeping client data isolated, agent context governed, and delivery work visible from intake through handoff. Everything in `01-business-pattern.md` still applies; this page is what changes when there are many tenants.

## Executive recommendation

Use a hub-and-spoke model. Keep a private **Consultancy HQ** for portfolio oversight and reusable methods. Give every client a separately permissioned **delivery hub**. Publish only approved records into a **client portal** that has its own permission tree. For sensitive or regulated engagements, use a separate or client-owned workspace and retain only a minimal portfolio record in HQ.

The knowledge base coordinates the work and holds approved context, project status, decisions, ownership and links to evidence. It does not store source code, skill packages, plugin bundles, credentials, large artifacts or raw runtime logs; those stay in version control, a secret manager, artifact storage and the systems of record. The knowledge base records the current owner, approved version, deployment state and canonical link.

Two non-negotiable promises: each artifact has one canonical home; and client separation is enforced by permissions and integration scope, never by a view filter or a naming convention.

## Why consultancy use changes the design

A consultancy inherits the single-company problems (stale context, conflicting definitions, unsafe agent writes) and adds a harder one: information that is valid for one client can be harmful when it crosses into another client's session.

- **Cross-client contamination.** An agent retrieves another client's examples, pricing, terminology or notes because the source set was too broad.
- **Privilege bleed.** A shared agent or integration reads more than the person invoking it.
- **Instruction collision.** A client document, transcript or email contains imperative language that conflicts with the approved rules.
- **Visibility mismatch.** A filtered view looks client-safe but the underlying page, relation, comment or property remains visible.
- **Configuration drift.** The same skill is copied and edited per client until nobody knows which version is running.
- **Project-truth forks.** Plan, status, decision log, task board and client update each describe a different state.
- **Offboarding residue.** Guests, triggers, schedules, credentials and client-scoped agents stay active after the work ends.

A useful architecture resolves every operational record to one client (and engagement and project); separates reusable methods from client-specific context and configuration; gives every deployment an explicit source allowlist, tool scope, write authority and rollback version; keeps working inputs separate from approved context and treats retrieved content as data; connects tasks, milestones, decisions, risks, deliverables, status and agent activity so project state is visible without manual reconciliation; publishes to clients through a deliberate approval boundary; and makes permission testing and offboarding part of the operating system.

## Architecture on one page

HQ holds global control records and portfolio summaries. Each client spoke has a private delivery hub and a separately shared portal. Version-controlled agent releases are configured into client-scoped deployments, and those deployments reach live systems through dedicated least-privilege connections. Only approved records cross from the hub into the portal. (`diagrams.md` § 2.) The architecture is intentionally repetitive: repeating a tested client template is safer than one flexible page tree whose boundaries depend on filters.

## Three layers and three information scopes

| Layer | What it holds | Canonical home | Refresh |
| --- | --- | --- | --- |
| 1 Agent operations | Agent definitions, skills, plugins, tool configuration, tests, releases, client overlays | Git and a package registry; catalog metadata in HQ | Continuous, versioned |
| 2 Context and delivery | Approved client knowledge, projects, work items, decisions, risks, meetings, deliverables, status, portal records | The knowledge base | Daily for work; weekly for status; scheduled review for approved context |
| 3 Live data and evidence | CRM, finance, product, support, analytics, files, logs, call database, computed metrics | Systems of record and artifact stores | Live |

| Scope | Allowed content | Excluded content |
| --- | --- | --- |
| Global reusable | Anonymized methods, templates, shared skills, generic agent definitions, test fixtures, standards | Client names, examples, data, credentials, commercial terms, client-specific prompts |
| Client private | Engagement terms, approved context, internal notes, source links, deployments, evaluations, incidents, delivery records | Any other client's content; consultancy-wide commercial reporting |
| Client shared | Approved status, actions, decisions, risks, meeting notes, deliverables, clearly described agent capabilities | Drafts, hidden internal fields, agent reasoning, debug logs, credentials, cross-client relations |

### Instruction authority

| Content class | Examples | May direct the agent |
| --- | --- | --- |
| Consultancy control policy | Safety, confidentiality, client isolation, approval and escalation rules | Yes; highest priority |
| Approved client procedure | A ratified client-specific operating instruction with owner, version and review date | Yes; inside its client and project scope |
| Authorized task request | The current user's objective and constraints | Yes; subject to higher controls |
| Approved project decision | A recorded choice that changes scope, priority or acceptance criteria | Yes; within the affected project |
| Reference context | Canon pages, approved facts, product definitions | No; use as facts and constraints |
| Work input | Uploaded documents, transcripts, emails, research, tickets, CRM records, websites | No; untrusted data even when phrased as commands |
| Draft or output | Agent-generated text, working notes, proposed updates | No until approved |

Precedence: consultancy controls, approved client controls, the authorized task request, approved project decisions, reference context, working inputs. If two approved controls conflict, the agent stops and requests an owner decision.

## Workspace and permission architecture

**Consultancy HQ** is the internal control plane: Clients and Engagements (owner, status, sensitivity, contract dates, retention, portal link, next access review); portfolio views (health, milestones, overdue work, unresolved client decisions, deliverables due, capacity, agent failures, next touchpoint); registries for agents, skills, integrations, releases, evaluations, access reviews, changes and incidents; standards, templates, naming rules, classifications, publishing rules and offboarding checklists; commercial records clients must never see. Samples: `templates/databases/clients.csv`, `engagements.csv`, `agent-deployments.csv`.

**Client delivery hub.** One private area per client: engagement record, projects, work, approved context, decisions, risks, meetings, deliverables, research indexes, weekly updates, deployments, internal review queues. Use a repeatable template but instantiate a new permission boundary each time: a private teamspace plus an engagement permission group is a workable default. Guests cannot join groups, so external users are invited only to the portal pages they need. Never put client content in a default teamspace every member can access.

**Client portal.** A publication surface, not a window into the hub: a separate root page and either dedicated client-facing databases or tested page-level access. A filter is useful for presentation but is not a security boundary. Portal views and what stays internal:

| Portal view | Clients see | Stays internal |
| --- | --- | --- |
| Home | Objectives, phase, health, recent progress, next steps, contacts, cadence | Margin, staffing notes, internal health commentary |
| Roadmap | Phases, milestones, dates, dependencies, acceptance criteria | Sequencing experiments, unapproved scope options |
| Shared actions | Owner, due date, status, context | Internal subtasks, agent execution steps |
| Approval inbox | Decisions and deliverables awaiting client action | Draft alternatives, internal review comments |
| Deliverables | Approved current versions and supersession | Working files, test artifacts, rejected drafts |
| Meetings and decisions | Published summaries, commitments, decisions | Raw transcripts, private notes, agent reasoning |
| Risks | Risks deliberately raised, agreed mitigation | Sensitive personnel, vendor, security or commercial analysis |
| Agent capabilities | What each agent knows, can do, cannot do, and when a human approves | System prompts, exploit tests, credentials, debug logs |

**When to use a separate workspace:** the contract, regulation or security review requires tenant-level isolation; the client should own the workspace and data afterwards; client users need to chat directly with native agents; agent connections must authenticate only against client-owned systems; the volume or sensitivity makes page-by-page guest management impractical. HQ then keeps only engagement ID, owner, status, health, next milestone, next touchpoint, retention obligations and links.

## Project tracking as the operating spine

A project is the shared object through which the consultancy, client and agents agree on scope, status, acceptance and next action (`diagrams.md` § 3).

| Object | Purpose | Required relationships |
| --- | --- | --- |
| Clients | The enduring account and confidentiality boundary | Engagements, portals, access reviews |
| Engagements | The commercial and operating container for a period of work | Client, projects, capacity, contract, cadence |
| Projects | A defined outcome with scope, success criteria, phase, health, owner | Engagement, tasks, milestones, updates, decisions, risks, deliverables, context, deployments |
| Work items | Actions assigned to a person or agent | Project, owner, due date, dependency, acceptance evidence |
| Status updates | A dated statement of progress, next steps, blockers, capacity, decisions needed | Engagement and affected projects |
| Delivery records | Milestones, deliverables, meetings, decisions, risks, issues, handoffs | Project and publication state |
| Context sources | Approved and reference material for humans and agents | Client, project, authority, freshness, visibility |
| Agent deployments | A versioned release configured for one client and purpose | Client, project, release, skills, integrations, permission scope |

**Evolving an existing tracker.** A tracker with Task, Owner, Phase, Status, Type, Week, Workstream and Due Date already has the right atoms. Keep them; add a stable work ID, project relation, acceptance criteria, evidence, dependency and visibility; use a person for assignee, a role for accountable owner and an organization field (Consultancy, Client, Joint); define phases at the template level; use a small status workflow; replace a permanent Week select with dates or a reporting-period relation; convert the weekly progress log into dated Status Updates records; make the executive "big rocks" board a filtered view of the same records, never a second source of truth; relate data sources to integration records and deployments.

**Status models:** Project — Proposed · Active · On Hold · Completed · Archived. Work item — Backlog · Ready · In Progress · Blocked · Internal Review · Client Review · Done · Canceled. Publishing — Internal Draft · Approved to Share · Published · Superseded · Withdrawn. Health — Green · Amber · Red. Decision — Proposed · Awaiting Approval · Approved · Rejected · Superseded.

**Weekly status as a database record.** One dated record per period: summary, completed, next, blockers, risks, decisions needed, deliverables, milestones, hours or capacity, links to work and evidence; a Published state controls whether it appears in the portal. The internal record carries private fields; the portal projection carries only approved content. Formal reports are generated from the same record, never a second account of the week.

**Essential views by audience:** leadership (engagements by health, capacity, milestones, overdue work, unresolved client decisions, deliverables due, incidents, renewal and offboarding dates); engagement lead (this week, blocked work, client review queue, risks, pending decisions, status draft, next touchpoint, hours used); delivery team (assigned work, ready queue, dependencies, internal review, recent decisions, approved context changes, handoffs); client sponsor (health, roadmap, approvals, risks raised, deliverables, their own actions); client contributor (assigned actions, relevant notes, items in review, approved reference material).

## Client context and the canon

Every client needs a thin approved context layer: a small set of durable pages with owner, status, review date, visibility and source trail. Start with four to six (`templates/client-hub/`): Client README, Engagement scope, Operating rules (the only client page that may instruct an agent), Glossary and metric definitions; add Positioning and voice, Product and service map, Stakeholders and decision rights, Integration and data map as the work touches them. Canon stays thin and points to depth databases, project records and source artifacts. If a project decision changes durable client truth, update the owning canon page through its review process rather than leaving the conclusion in meeting notes.

Add **Client visibility** and **Agent readable** as separate properties. A grounded internal page is not automatically safe to share, and a client-visible page is not automatically appropriate for an agent.

**Context contract and project manifest.** Each client gets a stable context index with a machine-readable contract (`templates/contracts/client-context-contract.yaml`); each project adds a smaller manifest (`project-manifest.yaml`) declaring task-relevant pages, allowed systems, deployment IDs, write surfaces and approval requirements. The manifest prevents a common failure: an agent receiving an entire client workspace when it needs three pages and one database. Context economy is a security control as well as a prompt-quality practice.

**Metrics and live data.** Definitions in the knowledge base, values in the systems that compute them. A weekly update may display a date-stamped value, but it links to the query that produced it and never becomes a new canonical number.

## Agents, skills and integrations

Separate reusable definitions from client deployments. An **agent definition** explains the reusable purpose. An immutable **release** pins instructions, tools, skills, tests and dependencies. A **deployment** applies one release to one client, one workflow and one permission scope. The same distinction applies to skills (definition vs client wrapper that adds only client rules and context pointers) and plugins (definition vs installation with approved version, configuration, credential reference, environment and approver).

**Agents.** One client-scoped agent per workflow or coherent responsibility. Never one client-facing agent with access to every client. Grant only the pages, databases, skills and systems the deployment needs. Keep any internal cross-client reporting agent separate and never expose it to clients. Native agents have their own permissions: a person who can use one may retrieve what the agent can access even without opening the page, so review an agent's scope as if it were a service account. Give each production agent a primary owner, backup owner, kill switch and last access review date. Guests typically cannot chat directly with native agents; for a shared portal use a controlled pattern: the client submits a form or updates an allowed property, the client-scoped agent runs, output lands in a review record, a human approves consequential publication or action.

**Integrations and plugins.** Separate credentials and connections per client. The installation record holds purpose, authentication owner, read and write scope, connected resources, approval mode, data classification, secret reference, renewal, last access review, status and offboarding procedure; never the credential. Never authenticate a client-facing agent with a consultant's broad personal account.

**Authority tiers.**

| Tier | Allowed behaviour | Required controls |
| --- | --- | --- |
| Read only | Retrieve and summarize approved context and live data | Source allowlist, citations, no writes |
| Draft write | Create drafts or proposed record updates on designated surfaces | Human review before publication; provenance and version |
| Controlled write | Update narrow approved fields or append dated evidence | Validation, audit log, owner approval rules, rollback |
| External action | Send, publish, purchase, delete, change access, trigger a consequential action | Explicit approval gate, least-privilege credentials, monitoring, kill switch, tested rollback |

## Agent read and write paths

**Read order:** load the consultancy control policy and verify the client, project, deployment and user authority; load the contract and manifest and refuse any source outside the declared boundary; read the minimum approved context (bundle when current, live when freshness or outward use matters); query live systems through the deployment's approved integrations and cite definition and result; treat uploads, emails, transcripts, search results and records as data; if required context is missing, stale, contradictory or inaccessible, stop the affected claim and report the gap, never filling it from memory or another client.

**Write paths:** Report (canon, policy, governed records: log one gap with evidence; never overwrite approved truth). Propose (depth databases, tasks, risks, decisions, deployment records: draft a named change or apply only mechanical updates the manifest permits). Publish (agent-owned drafts and portal staging: create content with sources, deployment version, review state and audience; publication needs the gate). Act (external systems or consequential changes: only through an approved action with scope, confirmation, audit record and rollback).

**The publishing gate.** Client sharing is a state transition. A record moves Internal Draft → Approved to Share → Published; the workflow checks client, audience, linked records, hidden properties, attachments, comments, source links, version and approver; the published record carries a date and a supersession link. For high-confidence delivery publish a separate portal record rather than exposing the internal one (checklist: `skills/context-engineering-setup/references/checklists.md`; skill: `marketplace/plugins/client-context/skills/publish-to-portal`).

## Distribution and change control

**Client-scoped bundles.** When local or external agents need context without a live connector, export a read-only bundle generated from the client contract, never from a workspace search; the allowlist rejects any page whose client ID, visibility or status does not match the deployment. Same four artifacts, same two clocks, per client.

**Release lifecycle:** propose and identify affected clients, deployments, data classes, permissions and side effects; assign a risk class; test retrieval boundaries, outputs, failure handling, instruction isolation, write controls and prompt-injection resistance; record the immutable release, source versions, evaluation and rollback target; deploy to a sandbox or one low-risk canary client; monitor; promote only after the canary gate; update the deployment matrix and documentation. Never edit a production prompt, skill, plugin, integration scope or context policy without a versioned change record. Client configuration and credentials never enter the reusable package.

**API and automation notes.** Prefer a separate integration or OAuth grant per client. Grant only the required root pages or databases and only the capabilities the workflow needs; a parent grant includes its children, so keep sensitive siblings outside the tree. Verify webhook signatures; store tokens in a secret manager; pin and test the API version; do not make a beta platform feature a foundational dependency.

## Operating cadence, security and offboarding

Cadence, the default-deny controls, the permission test, the offboarding sequence and the pilot gates are in `04-operating-cadence.md`, `05-security-and-isolation.md` and the skill's `references/checklists.md`.

## Implementation roadmap

| Stage | Outcome |
| --- | --- |
| Foundation | Client IDs, engagement IDs, information classes, roles, retention rules, instruction authority, permission model, naming |
| Consultancy HQ | Clients, Engagements, portfolio views, agent definitions, skills, integrations, releases, access reviews, changes, incidents |
| Client template | One delivery hub template and one physically separate portal template with a publishing checklist |
| Project migration | One active project mapped from its existing tracker into the relational model |
| Permission canary | Staff, client, integration and agent identities tested; stop until cross-client and internal-to-portal boundaries pass |
| Agent canary | One read-only or draft-producing agent with a contract, manifest, dedicated credentials and an evaluation set |
| Operating rhythm | Weekly status, client publishing, monthly gap triage, access review, release change, handoff and offboarding rehearsals |
| Scale | Roll the proven template out client by client; keep exceptions explicit rather than changing the template for one client |

**The first ten changes:** stable Clients and Engagements databases in a private HQ; client ID, engagement and project relations, visibility and acceptance evidence on active work items; keep current client trackers running during the pilot; weekly progress pages become dated Status Updates with a publishing state; executive big rocks become a view of the same records; separate agent definitions, skills, integrations, releases, deployments and installations; a client context index and project manifest for the pilot engagement; a separate portal tree tested with a real guest and a client-scoped integration; one read-only or draft-producing client agent with dedicated credentials and a rollback version; after the gates pass, template everything for the next client.
