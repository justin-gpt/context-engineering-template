---
name: report-gap
description: Record something missing, stale or contradictory in the company canon as one row in the Canon Gaps tracker, instead of editing the page. Use when a task hit a gap, two pages disagree, a term has no definition, a number cannot be grounded, or a user says "log a gap" or "the canon is wrong about X".
---

# Report a gap

Agents never edit canon. A gap row is how a finding survives the end of a session without corrupting truth. The tracker's location is `rules.gap_tracker` in the context contract.

## Procedure

1. **Dedup-check first.** Query open rows (`Status` in `new`, `accepted`) for the same term, fact or page. If one exists, add the new detail to it as a comment or appended text rather than creating a twin. Tell the user which row you updated.
2. **One row per gap.** Never batch unrelated findings into one row.
3. **Write the row** with exactly the tracker's properties:
   - `Gap` — one line; lead with the term or fact ("Activation has no canonical definition; three teams use three").
   - `Where it hurt` — the task that failed or degraded, with a date; one or two concrete sentences.
   - `Suggested page` — the canonical slug that should own the fix; definitional failures go to `glossary` even when they surfaced elsewhere; `new_page`, `decision_log` or `unsure` when no page fits.
   - `Status` — `new`. Humans move it to `accepted`, `patched` or `rejected`.
   - `Reporter` — the person's name if they asked you to log it on their behalf, otherwise `Claude (<task>)` for an autonomous run.
   - `Context link` — the canon page with the problem, or the artifact where it surfaced.
4. **Confirm to the user with the row URL**, so the finding is verifiably on record.
5. If the tracker is unreachable, write the gap into your output under a "Gaps to log" heading and say it was not recorded.

## What is not a gap

- A draft page being draft. That is the owner's queue, not a gap.
- A disagreement between a working document and canon. Canon wins; the working document is wrong.
- A metric value. Values are never on pages; a missing pull method is a catalog gap, which you log here with `Suggested page: glossary` or the catalog row's slug.
