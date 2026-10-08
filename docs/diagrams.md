# Diagrams

Mermaid renders on GitHub. Each diagram matches a section of `01-business-pattern.md` or `02-consultancy-pattern.md`.

## 1. Business pattern: the architecture on one page

```mermaid
flowchart LR
  subgraph People
    O[Canon owners<br/>roles, not people<br/>edit canon · flip status · review on cadence]
  end
  subgraph KB[Knowledge base]
    C[Layer 2 · Canon<br/>index = llms.txt · YAML contract<br/>≤8 thin pages · status ladder<br/>Canon Gaps tracker]
    D[Layer 3 · Metrics catalog<br/>definitions + pull methods<br/>never a value]
    E[Delivery surfaces<br/>briefs · prep pages · review mirrors<br/>none of it is canon]
  end
  subgraph Dist[Agents & distribution · Layer 1]
    S[Nightly sync → PR gate<br/>contract.yaml · canon/*.md<br/>meta.json · bundle.json]
    M[Mirror repo + plugin bundle<br/>read-only · source wins<br/>auto-update on merge]
    A[Agents & skills<br/>bundle first · live if stale<br/>assert only grounded · cite URL]
  end
  L[Live systems of record<br/>CRM · warehouse · billing · product<br/>queried live, never restated]

  O -->|1 edit| C
  C -->|2 export| S
  S -->|3 validate, review, merge| M
  M -->|4 install| A
  A -->|5 read pull method| D
  D -.->|6 query live| L
  A -->|7 publish| E
  A -.->|8 live fallback when stale| C
  A -->|9 report a gap, never edit| C
```

## 2. Consultancy pattern: hub and spoke with hard client boundaries

```mermaid
flowchart TB
  HQ[Consultancy HQ<br/>clients + portfolio views · standards<br/>agent + skill catalogs · internal only]
  HUB[Client delivery hub · one per client<br/>engagements, projects, work · approved client context<br/>client-scoped deployments · delivery team only]
  PORTAL[Client portal · one per client<br/>approved status + roadmap · shared actions + approvals<br/>published decisions · separate permission tree]
  AGENT[Agent layer · git<br/>reusable agents and skills · immutable releases + overlays<br/>no credentials or client data]
  LIVE[Live systems + stores<br/>CRM, billing, product, support · call database<br/>secret manager for credentials]

  HQ -->|links only| HUB
  HUB -->|publish gate| PORTAL
  AGENT -->|deploy by client| HUB
  LIVE -->|query live| HUB
  AGENT -->|scoped tools| LIVE
```

Repeat the hub and the portal for every client. Use a separate or client-owned workspace when a contract, regulation or security review requires it.

## 3. Project tracking is the operating spine

```mermaid
flowchart TB
  CL[Client<br/>owner · sensitivity · portal · access review] --> EN[Engagement<br/>scope and success · commercial terms · cadence · capacity]
  EN --> PR[Project<br/>objective · health and phase · milestones · context manifest]
  PR --> PO[Portal<br/>published views · approvals · deliverables]
  PR --> WI[Work items<br/>status and owner · due date · dependency · acceptance evidence]
  PR --> SU[Status updates<br/>completed and next · blockers and risks · hours · client decisions]
  PR --> DR[Delivery records<br/>deliverables · meetings · decisions · risks and issues]
  PR --> AD[Agent deployments<br/>release and skills · integrations · permission scope · evaluations]
  GD[Global definitions in HQ<br/>agents · skills · integrations · releases] --> AD
```

Each operational record resolves to one client and one engagement. Only records approved for sharing are published into the portal.

## 4. Three write paths, by risk to company truth

```mermaid
flowchart LR
  R[1 · Report, never edit<br/>target: canon and Handbook pages<br/>insert a row in Canon Gaps · dedup first<br/>a human owner patches the page]
  P[2 · Propose, owner-gated<br/>target: depth databases<br/>mechanical layer auto-applies with dates and citations<br/>judgment layer is proposed only]
  U[3 · Publish, agent-owned surfaces<br/>target: briefs database, prep pages, mirrors<br/>provenance footer · comments harvested back<br/>nothing here is canon]
  R --- P --- U
```

Lower risk to company truth on the left; higher agent autonomy on the right. The one hard rule: the agent proposes; the owner verifies.

## 5. Publishing gate (consultancy)

```mermaid
stateDiagram-v2
  [*] --> InternalDraft
  InternalDraft --> ApprovedToShare: named approver · checklist passes
  ApprovedToShare --> Published: portal projection created · date + supersession link
  Published --> Superseded: a newer record is published
  ApprovedToShare --> Withdrawn
  Published --> Withdrawn
```
