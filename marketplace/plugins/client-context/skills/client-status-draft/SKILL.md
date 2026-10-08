---
name: client-status-draft
description: Draft one client's weekly status update as a single Internal Draft row in the client hub's Status Updates database, built from that client's work items, decisions, risks and call summaries, for the engagement lead to edit and approve. Use when asked to "draft the Friday status", "prepare this week's update for CLIENT-xxx", or on the weekly schedule. Never publishes.
---

# Client status draft

One dated record per reporting period, written by the agent as a proposal, approved by a human, projected to the portal only after the publishing gate.

## Preconditions

Run `client-context` first. This skill acts as the status-drafter deployment named in the client contract's `approved_agents`; its only write surface is the Status Updates database, state `Internal Draft`.

## Procedure

1. **Gather, inside the client boundary only:** work items changed this period (status, due dates, blockers), decisions recorded, risks raised or changed, milestones hit or slipped, meeting summaries and call notes for this client (filtered by account ID), hours logged where the hub tracks them.
2. **Write the row** with the database's properties: Update (period ending date in the title), Period ending, Health (propose one and say why), Summary (three sentences at most), Completed, Next, Blockers, Decisions needed (each with the role who owns the decision and the date the project is affected if none arrives), Hours used, Author = `Agent (draft): <deployment_id>`, Approver empty, Publishing state = `Internal Draft`.
3. **Cite inside the row** which work items, decisions and meetings each statement came from, so the lead can check in seconds.
4. **Propose, do not decide.** A proposed change to project health, a new risk, or a new work item goes in as `Agent (draft)` rows or as a bulleted proposal in the row body.
5. **Confirm to the lead with the row URL** and the three things that most need their judgment.

## Never

- Never set Publishing state beyond `Internal Draft`; never write to the portal.
- Never include internal commercial, staffing or security commentary in fields that project to the client.
- Never reuse a sentence, number or example from another client's status, however similar the engagements.
