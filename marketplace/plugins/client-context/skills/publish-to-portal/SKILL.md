---
name: publish-to-portal
description: Move an approved record (status update, deliverable, decision, meeting summary, risk) from a client's delivery hub into that client's portal as a projection, after running the full publishing checklist. Use when an engagement lead says "publish this to the client", "share the status", or "move this to Approved to Share / Published". Refuses when any checklist item fails.
---

# Publish to the client portal

Client sharing is a state transition, not a copy-and-paste habit. The portal is a publication surface, not a window into the hub.

## Preconditions

- `client-context` has run for this client.
- The record's Publishing state is `Approved to Share` with a named approver, or the directing user is the approver and says so in this session.
- You are acting under a manifest whose `approval_required` includes `publish_to_client`; publication therefore needs the human's explicit go in this session, once per record.

## Checklist (all must pass; stop on the first failure and say which)

1. The record resolves to the intended client, engagement and project.
2. Publishing state is Approved to Share and the named approver is recorded.
3. The content is current, fact-checked and linked to its source or evidence; every number traces to a catalog row or a dated live pull.
4. No other client's name, data, example, URL, relation, attachment, comment or backlink is present.
5. No internal commercial, staffing, security, evaluation, prompt, debug or incident information is present.
6. No secret, token, account identifier or credential hint is present.
7. The client can open every intended link and cannot navigate to the internal source database.
8. Only approved properties are visible in the portal view.
9. The current version and the superseded version relationship are clear.
10. The item names the owner, publication date, review date and next client action when applicable.

## Procedure

1. Run the checklist and show the result as a table.
2. Create the **portal projection** as a separate record or page in the portal tree (never expose the internal record): the approved fields only, a publication date, and a supersession link to the record it replaces.
3. Mark the superseded portal item `Superseded`; set the internal record to `Published` with the published link.
4. Log the publication on the project and queue it for the next status update.
5. Confirm with the portal link and the list of fields that were deliberately left behind.

## Never

- Never share the internal record itself, change its permissions, or add a client guest to the hub.
- Never publish from a filtered view and call it safe. A filter is presentation, not a boundary.
- Never publish a record whose evidence links point into another client's space or into Consultancy HQ.
