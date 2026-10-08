## Is this a sane export?

This pull request updates the read-only mirror in `export/`. The content is **never edited
here**: every byte was generated from the source pages by `scripts/canon_sync.py`. If
something in the diff is wrong, fix the source page (or the contract) and let the next sync
regenerate the mirror. Approving this PR means "the export reflects the canon as its owners
intend", nothing more.

Review checklist:

- [ ] `export/meta.json` says `"validation": "passed"` and `pages_missing` is empty (or every missing page is expected and the owner knows).
- [ ] `warnings` in `export/meta.json` are understood: past `next_review` dates, a page that restates a metric value, a bundle growing past 150 KB.
- [ ] Every page whose status is `grounded` reads as verified truth. Anything that still needs an owner's answer belongs in `draft` with a `[CONFIRM]` or `[YOU DECIDE]` marker.
- [ ] No person's name, client name, credential, or metric value appears in the diff. Canon holds definitions and pull methods; values are pulled live.
- [ ] `generated_at` moved only because content moved. A heartbeat-only run should not have opened a PR.

If this PR was opened by the `canon-sync` workflow, the title carries the new `generated_at`; consumers cite the mirror as "canon as of" that timestamp.
