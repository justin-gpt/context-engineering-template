# Bundled canon lands here

The nightly sync copies `export/` from the mirror repository into this folder: `contract.yaml`, `canon/<slug>.md`, `meta.json` and `bundle.json`. The `company-context` skill reads these first and goes to the live knowledge base only when the heartbeat is stale, a status matters for an outward deliverable, the user asks for the latest, or a page is missing.

Nothing in this folder is edited by hand. If it disagrees with the knowledge base, the knowledge base wins and the next sync overwrites it.

Until the first sync runs, this folder holds only this file, and the skill reports "no bundled canon; using live source" or, with no connector, "canon unavailable" rather than inventing company facts.
