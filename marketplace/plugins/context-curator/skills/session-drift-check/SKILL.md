---
name: session-drift-check
description: At the end of a working session, review the conversation for durable changes (a process defined, an owner changed, a cadence moved, a tool introduced, a documented fact corrected) and report where the Handbook or canon now lags or contradicts, without writing any page. Use when asked to "wrap up", "check for drift", or "what in the Handbook is now out of date".
---

# Session drift check

Conclusions that land only in a working document, a chat transcript or a markdown file are invisible to agents and to the mirror. That is how truth forks. This skill closes the loop without touching a page.

## Procedure

1. **Scan the session for durable changes.** Ignore ephemeral detail (today's numbers, one-off tasks). Keep: processes defined or changed, owners changed, cadences moved, tools or systems introduced or retired, facts corrected, decisions made.
2. **Fetch the pages in scope by ID** (canon slugs from the contract; Handbook pages the user names). Never by title search.
3. **Report drift in four buckets per page:** missing from the page; the page now contradicts; only partially reflected; verification lapsed (`next_review` passed).
4. **Flag any live metric that has crept onto a page**, as a gap with `Suggested page` set to the page's slug.
5. **Hand the summary to the authoring path**, one page per run: canon pages go to `populate-canon-page` as a draft refresh; Handbook pages go to their owner; decisions go to the decision log. Offer to log gaps for each item.

## Output

A short table: page · bucket · the line that should change · evidence from the session · owner role. Nothing is written to any page by this skill.
