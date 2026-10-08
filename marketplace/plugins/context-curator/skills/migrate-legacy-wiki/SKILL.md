---
name: migrate-legacy-wiki
description: Move content from a legacy wiki (Confluence, SharePoint, an old Notion, Google Docs) into the canon and Handbook structure by inventory and disposition table, stopping for the owner's confirmation before anything moves. Use when asked to "migrate the wiki", "consolidate our docs into Notion", or "retire the old handbook".
---

# Migrate a legacy wiki

Most teams arrive with years of pages that disagree with each other. Migration is triage, not transport.

## Procedure

1. **Inventory before moving anything.** List related pages with title, owner if known, last edited, link count, and whether a current canonical destination exists.
2. **Produce a disposition table**, one row per page, with one of: `move and improve`, `split`, `move as-is`, `merge into <destination>`, `archive`, `defer`. Add a one-line reason and the destination (a canonical slug, a Handbook page, a teamspace register, or none).
3. **Stop for the owner's confirmation of the batch.** Do not move a page without it.
4. **Find the canonical destination first and update it** rather than creating a duplicate. If a destination is canon, hand the content to `populate-canon-page` so it arrives as a draft with markers; it never lands directly as grounded truth.
5. **Treat legacy content as claims to verify** against current practice. Restated numbers are stripped and pointed at the metrics catalog.
6. **Leave the originals untouched** until a single, deliberate freeze date the owner sets. Then mark the legacy source read-only with a banner naming the new home.
7. **Post-migration check:** images and attachments do not port automatically and complex macros degrade; list what needs manual attention. Run a link check from every migrated page.

## Output

The disposition table, the list of pages moved with old and new links, the markers raised for owners, and the freeze proposal.

## Never

- Never move a page into a shared space with a broader audience than the original without the owner saying so.
- Never delete the originals.
- Never merge two clients' material into one page, however similar.
