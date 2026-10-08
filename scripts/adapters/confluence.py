"""Confluence adapter: a documented stub.

`source_of_truth: confluence` is an allowed contract value because many teams
keep their handbook there, but this repository does not ship a working
Confluence client: the authors could not test one against a live instance, and
an untested exporter of company truth is worse than none.

Two ways forward:

1. Export to markdown and use the markdown adapter. Confluence Cloud and Server
   both have exporters (built-in exports, marketplace apps, or the REST API's
   `body.storage` plus a storage-format-to-markdown converter). Point a contract
   with `source_of_truth: markdown` at the exported folder, add the frontmatter
   from docs/formats.md section 4 to each page, and run canon_sync.py. This
   keeps the pull-request gate and the two clocks exactly as they are.

2. Implement this adapter. Copy scripts/adapters/markdown.py, keep the class
   shape (`__init__(ctx)` and `fetch_page(slug, entry) -> FetchedPage`), fetch
   each page by its Confluence content ID, convert the storage format to
   markdown, synthesize the frontmatter the way notion.py does, and register the
   class in canon_sync.ADAPTERS. Read the token from an environment variable
   and never print it.
"""

from __future__ import annotations

from typing import Any

from adapters.base import FetchedPage, SyncContext

MESSAGE = (
    "The Confluence adapter is a stub. Either export your Confluence pages to markdown and use "
    "`source_of_truth: markdown` (see scripts/adapters/markdown.py), or implement "
    "ConfluenceAdapter.fetch_page following the notes in scripts/adapters/confluence.py."
)


class ConfluenceAdapter:
    """Raises NotImplementedError with a pointer to the markdown adapter."""

    def __init__(self, ctx: SyncContext):
        self.ctx = ctx
        raise NotImplementedError(MESSAGE)

    def fetch_page(self, slug: str, entry: dict[str, Any]) -> FetchedPage:  # pragma: no cover - unreachable
        raise NotImplementedError(MESSAGE)
