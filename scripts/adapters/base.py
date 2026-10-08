"""Common types shared by every adapter."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from typing import Any

import yaml


@dataclass
class SyncContext:
    """What every adapter needs to know about the run."""

    contract: dict[str, Any]  # the parsed contract
    source_root: str  # vault folder (markdown) or root page ID (notion)
    page_url_base: str  # prefix for citing pages
    today: dt.date  # the run's date, used for next_review warnings


@dataclass
class FetchedPage:
    """One canonical page after the adapter read it (or failed to)."""

    slug: str
    title: str
    status: str  # from the contract entry
    owner: str  # from the contract entry (a role)
    review: str  # from the contract entry
    url: str
    available: bool
    frontmatter: str = ""  # the YAML block verbatim, "---\n...\n---\n"; empty when unavailable
    body: str = ""  # markdown after the frontmatter; empty when unavailable
    next_review: dt.date | None = None
    problems: list[str] = field(default_factory=list)  # validation errors; any one fails the sync
    notes: list[str] = field(default_factory=list)  # informational, e.g. why a page is unavailable

    @property
    def document(self) -> str:
        """Frontmatter plus body: what goes under the generated header and into the bundle."""
        return self.frontmatter + self.body


def render_frontmatter(fields: dict[str, Any]) -> str:
    """Serialise the metadata block for a page whose source has no frontmatter (Notion).

    Keeps key order and emits dates as plain YAML dates, matching the hand-written
    markdown sources in templates/canon/.
    """
    text = yaml.safe_dump(fields, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return "---\n" + text + "---\n\n"
