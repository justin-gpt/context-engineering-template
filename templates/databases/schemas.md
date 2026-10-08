# Database schemas

Property definitions for every database the two patterns use. The CSVs beside this file carry the same columns with two or three fictional rows each, so you can import them into Notion (Import → CSV), Airtable, Coda, a spreadsheet, or a SQL table and keep the shape. Select options are listed so a validator can check that the database and the skills that write to it never drift apart.

Universal metadata on every record: owner (a role), status, client, engagement, sensitivity, client visibility, agent readability, canonical home, version, last reviewed, next review, retention class. These fields support workflow and audits. **They do not replace real permissions.**

## Business pattern

### Canon Gaps (the agent write path)

| Property | Type | Options / notes |
| --- | --- | --- |
| Gap | title | One line: what is missing or conflicting. Lead with the term or fact. |
| Where it hurt | text | The task that failed or degraded, with a date. |
| Suggested page | select | every canonical slug · `new_page` · `decision_log` · `unsure` |
| Status | select | `new` · `accepted` · `patched` · `rejected` |
| Reporter | text | A person, or `Claude (<task>)` for autonomous runs. |
| Context link | url | The canon page with the problem, or the artifact where it surfaced. |
| Reported | created time | Automatic. |

### Metrics Catalog (definitions and pull methods, never values)

| Property | Type | Options / notes |
| --- | --- | --- |
| Metric | title | The metric's name as the business uses it. |
| Metric ID | text | Short stable key (R-01) so skills and briefs can reference rows unambiguously. |
| Definition | text | Plain language, aligned with the glossary. |
| Formula / grain | text | How it is computed and at what grain. |
| Source of truth | select | `CRM` · `BI / warehouse` · `Billing` · `Product analytics` · `HRIS` · `Derived` · `TBC` |
| Live-pull method | text | The exact query, explore and measure, or agent call; reconciliation caveats; ends with "re-query for the value". |
| Status | select | `stub` · `draft` · `grounded` |
| Availability | select | `measurable` · `implied` · `absent` |
| Domain | select | `Revenue engine` · `Finance` · `Product` · `People / Org` |
| Value-chain stage | select | `Demand` · `Acquire` · `Convert` · `Onboard` · `Retain` · `Expand` · `Monetize` · `Efficiency / Capital` |
| Cadence | select | `Daily` · `Weekly` · `Monthly` · `Quarterly` |
| Role | select | `North-star` · `Guardrail` |
| Owner / DRI | text | A role. Every grounded row has one. |
| Reconciliation notes | text | Why two systems disagree and which wins; corrections with dates. |
| Related | text | Sibling metrics, consumers, superseded rows. |
| Last verified | date | When the pull method was last run successfully. |

## Consultancy pattern

### Clients (the confidentiality boundary)

| Property | Type | Options / notes |
| --- | --- | --- |
| Name | title | |
| Client ID | text | `CLIENT-001`; every operational record resolves to one. |
| Status | select | `Prospect` · `Active` · `Paused` · `Closed` |
| Account owner | text | A role. |
| Sensitivity | select | `Standard` · `Confidential` · `Regulated` |
| Contract & retention rules | text | Retention period, export obligations, offboarding deadline. |
| Internal hub | url | The delivery hub (separate permission tree). |
| Portal | url | The client portal (separate permission tree). |
| Workspace model | select | `Consultancy teamspace` · `Separate workspace` · `Client-owned workspace` |
| Access review date | date | |
| Offboarding owner | text | A role. |

### Engagements

Name · Engagement ID · Client (relation → Clients) · Service type (`Workshop` · `Agent build` · `Fractional GTM engineering` · `Advisory`) · Lead (role) · Period (date range) · Status (`Proposed` · `Active` · `On Hold` · `Completed` · `Archived`) · Health (`Green` · `Amber` · `Red`) · Scope · Success criteria · Capacity · Cadence · Next touchpoint · Renewal checkpoint.

### Agent Deployments (registry of record)

Name · Deployment ID · Client (relation) · Purpose · Agent release · Context contract (url) · Project manifest (url) · Integration identity (the least-privilege identity, never a credential) · Read scope · Write scope · Approval mode (`Read only` · `Draft write` · `Controlled write` · `External action`) · Status (`Sandbox` · `Canary` · `Production` · `Disabled`) · Owner · Backup owner · Last access review · Rollback release.

### Work Items (inside each client's delivery hub)

Title · Work ID · Project (select or relation) · Type (`Activity` · `Deliverable` · `Milestone`) · Status (`Backlog` · `Ready` · `In Progress` · `Blocked` · `Internal Review` · `Client Review` · `Done` · `Canceled`) · Priority (`P1` · `P2` · `P3`) · Assignee (role) · Owner organization (`Consultancy` · `Client` · `Joint`) · Due · Workstream · Acceptance criteria · Evidence (url) · Visibility (`Internal` · `Client shared`) · Source (`Human` · `Agent (draft)`).

### Status Updates (one dated record per period)

Update · Period ending · Health · Summary · Completed · Next · Blockers · Decisions needed · Hours used · Author · Approver · Publishing state (`Internal Draft` · `Approved to Share` · `Published` · `Superseded` · `Withdrawn`) · Published link.

Full-model additions that follow the same pattern: Projects, Milestones, Deliverables, Decisions, Risks & Issues, Meetings, Handoffs, Agent Definitions, Agent Releases, Skills, Integrations, Evaluations & Runs, Changes & Incidents. Column lists for those are in `docs/02-consultancy-pattern.md`.
