# Checklists

## Pilot gates (pass all before scaling)

| Gate | Pass condition |
| --- | --- |
| Boundary | Representative client, staff, integration and agent identities cannot retrieve content outside their authorized scope |
| Context | The agent answers the agreed evaluation questions from approved sources, cites them, and fails safely on missing or draft context |
| Project truth | Tasks, milestones, status, decisions, risks, deliverables, hours and next actions reconcile on the project page and the weekly update |
| Write control | The agent writes only to designated draft or narrow controlled fields and cannot overwrite canon |
| Portal | Only records in Approved to Share or Published state appear, with no hidden internal fields, relations, comments or attachments |
| Rollback | The prior release, credentials, triggers and portal state can be restored or disabled within the documented response target |
| Offboarding | A rehearsal revokes guest, agent, integration, schedule, webhook and credential access without losing the agreed final record |

## Permission test (before launch and after any structural change)

- A team member assigned to one client cannot search, relate, mention or open another client's content.
- A client guest sees only the portal and assigned actions, including through backlinks, relations, comments, attachments and search.
- A client-scoped integration cannot fetch pages outside the approved client tree.
- A client-scoped agent cannot answer questions from another client's canon, projects or data sources.
- A portal view does not reveal hidden internal properties or allow navigation to the source database.
- A moved or duplicated page retains the expected permissions and does not inherit broader access.
- An external action requires the expected confirmation and records the actor, scope, result and remediation path.

## Publishing checklist (every record that crosses into a portal)

- [ ] The record resolves to the intended client, engagement and project.
- [ ] Publishing state is Approved to Share and the named approver is recorded.
- [ ] The content is current, fact-checked and linked to its source or evidence.
- [ ] No other client's name, data, example, URL, relation, attachment, comment or backlink is present.
- [ ] No internal commercial, staffing, security, evaluation, prompt, debug or incident information is present.
- [ ] No secret, token, account identifier or credential hint is present.
- [ ] The client can open every intended link and cannot navigate to the internal source database.
- [ ] Only approved properties are visible in the portal view.
- [ ] The current version and the superseded version relationship are clear.
- [ ] The item names the owner, publication date, review date and next client action when applicable.
- [ ] A representative guest account and client-scoped integration pass the access test after any structural change.
- [ ] The published result is logged on the project and included in the next status update.

## Offboarding (client close)

1. Finalize and approve deliverables and the closing status update.
2. Resolve or document open work, decisions, risks and known defects.
3. Create the agreed client export or transfer and confirm receipt.
4. Freeze project records and mark the final canonical versions.
5. Disable schedules, triggers, webhooks, agents and integrations.
6. Revoke guests, service accounts, OAuth grants and client-specific credentials.
7. Archive deployments and remove them from active portfolio views.
8. Start the contract-specific retention or deletion schedule and assign its owner.
9. Move only authorized, anonymized learning into the global library.
10. Retain a minimal registry record showing disposition, access closure and remaining obligations.

## Operating cadence

| Cadence | Review |
| --- | --- |
| Every agent run | Confirm tenant and deployment; load the manifest; record source versions; enforce write authority; capture result and exceptions |
| Weekly | Update project health, completed work, next work, blockers, decisions needed, milestones, deliverables, capacity, and the portal |
| Monthly | Triage context gaps; review active deployments and failures; reconcile hours and value; rotate integrations due; retire duplicate or stale records |
| Quarterly | Re-verify canon; review permissions and guest access; evaluate agent releases; confirm portfolio priorities; review retention and reuse |
| On change | Impact assessment, tests, approval, canary, release, documentation, rollback readiness |
| On project close | Accept deliverables, complete handoff, freeze final status, archive work, revoke unnecessary access, start retention |
| On client close | Export or transfer agreed materials; disable everything client-scoped; preserve only authorized anonymized learning |

## Release lifecycle for an agent, skill or plugin

1. Propose the change; identify affected tenants, deployments, data classes, permissions and external side effects.
2. Assign a risk class and the required test and approval evidence.
3. Test retrieval boundaries, expected outputs, failure handling, instruction isolation, write controls and prompt-injection resistance.
4. Record the immutable release, source versions, evaluation result and rollback target.
5. Deploy to a sandbox or one low-risk canary tenant.
6. Monitor output quality, permission behaviour, latency, cost and failures.
7. Promote only after the canary gate passes; otherwise roll back.
8. Update the deployment matrix, change log, review date and affected documentation.
