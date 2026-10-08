"""Markdown adapter: the canon lives in a folder of .md files (a git vault, Obsidian, ...).

Each contract entry's `id` is a path relative to `source_root`. Every file carries
the YAML frontmatter from docs/formats.md section 4; this adapter parses it and
checks that `slug`, `status` and `owner` agree with the contract entry. A mismatch
is a validation error (the sync fails) because two sources of metadata that
disagree is exactly the drift the contract exists to prevent.

A file that does not exist is reported as "page not available": the sync writes a
placeholder and lists the slug in meta.json.pages_missing.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from adapters.base import FetchedPage, SyncContext
from common import to_date

# "---" on its own line, the YAML block, "---" on its own line, then the body.
FRONTMATTER_RE = re.compile(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n", re.DOTALL)

# Frontmatter fields that must agree with the contract entry.
CHECKED_FIELDS = ("slug", "status", "owner")


def split_frontmatter(text: str) -> tuple[str, dict[str, Any] | None, str, str | None]:
    """Return (frontmatter_block_verbatim, parsed_dict, body, error).

    The block is returned verbatim (including the closing '---' line) so the
    export does not reformat what the author wrote.
    """
    match = FRONTMATTER_RE.match(text)
    if not match:
        return "", None, text, "missing YAML frontmatter (the file must start with a --- block)"
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        return "", None, text, f"frontmatter is not valid YAML: {exc}"
    if not isinstance(parsed, dict):
        return "", None, text, "frontmatter must be a YAML mapping"
    return match.group(0), parsed, text[match.end():], None


class MarkdownAdapter:
    """Reads pages from `source_root/<id>`."""

    def __init__(self, ctx: SyncContext):
        self.ctx = ctx
        self.root = Path(ctx.source_root)

    def fetch_page(self, slug: str, entry: dict[str, Any]) -> FetchedPage:
        page_id = str(entry.get("id", "")).strip()
        page = FetchedPage(
            slug=slug,
            title=slug,
            status=str(entry.get("status", "")),
            owner=str(entry.get("owner") or entry.get("owner_role") or ""),
            review=str(entry.get("review", "")),
            url=self.ctx.page_url_base + page_id,
            available=False,
        )
        path = self.root / page_id
        if not path.is_file():
            page.notes.append(f"page not available: {path} does not exist")
            return page

        text = path.read_text(encoding="utf-8")
        block, meta, body, error = split_frontmatter(text)
        if error:
            page.problems.append(f"{slug}: {error} ({path})")
            return page

        # The frontmatter and the contract must tell the same story.
        for field_name in CHECKED_FIELDS:
            expected = slug if field_name == "slug" else getattr(page, field_name)
            actual = meta.get(field_name)
            if actual is None:
                page.problems.append(f"{slug}: frontmatter is missing '{field_name}' (contract says {expected!r})")
            elif str(actual).strip() != str(expected).strip():
                page.problems.append(
                    f"{slug}: frontmatter {field_name}={actual!r} does not match the contract ({expected!r})"
                )

        page.available = True
        page.title = str(meta.get("title") or slug)
        page.frontmatter = block
        page.body = body
        if "next_review" in meta:
            page.next_review = to_date(meta.get("next_review"))
            if page.next_review is None:
                page.notes.append(f"{slug}: frontmatter next_review is not an ISO date; using the contract's")
        return page
