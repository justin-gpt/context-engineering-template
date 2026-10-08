"""Notion adapter: the canon lives in Notion pages fetched by ID over the REST API.

THIS ADAPTER NEEDS A TOKEN AND A LIVE WORKSPACE TO EXERCISE. The repository's
tests only cover the pure conversion functions (blocks -> markdown) with
hand-written block dicts and a fake HTTP session; nothing here is run against
Notion in CI. Before relying on it, run one sync by hand against your own
workspace and read the exported markdown.

Setup
- Create an internal integration in Notion, copy its token, and export it as
  NOTION_TOKEN (see .env.example). The token is read from the environment only
  and is never printed, not even in error messages.
- Share every canonical page with the integration (Notion pages are invisible
  to an integration until they are shared with it). An unshared page comes back
  as 404 and is exported as a placeholder with `available: false`.
- Put the 32-hex page IDs in the contract's canonical_pages entries. The sync
  fetches by ID, never by title search.

What is fetched
- GET /v1/pages/{id}            -> the page title (the property of type "title")
- GET /v1/blocks/{id}/children  -> the content, paginated 100 at a time,
                                   recursing into blocks with has_children

Block types converted: paragraph, heading_1/2/3, bulleted_list_item,
numbered_list_item, to_do, quote, callout, code (fenced with its language),
divider, table + table_row (markdown table), toggle (as a bullet), child_page
and child_database (a one-line note). Any other type becomes
`<!-- unsupported block: TYPE -->`; if it has children (columns, synced blocks)
the children are still rendered after the comment so no text is lost.

Rich text keeps bold, italic, code, strikethrough and links.

Errors
- 404 and 403: "page not available" -> placeholder + meta.json.pages_missing.
- 429 (rate limit) and 5xx: retried with backoff, honouring Retry-After,
  at most MAX_RETRIES times, then reported as an error.
- Anything else: NotionError with the status code and the request path.

Frontmatter: Notion pages carry no YAML frontmatter, so the exporter writes one
from the contract entry (slug, owner, status, review, visibility) plus the
contract-level last_reviewed / next_review dates and the page title from Notion.
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Callable

import requests

from adapters.base import FetchedPage, SyncContext, render_frontmatter
from common import to_date

API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"
MAX_RETRIES = 5
TIMEOUT_SECONDS = 30
PAGE_SIZE = 100

# A Notion ID is 32 hex characters, usually written with dashes as a UUID.
NOTION_ID_RE = re.compile(r"\A[0-9a-fA-F]{8}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{4}-?[0-9a-fA-F]{12}\Z")


class NotionError(Exception):
    """A request failed in a way the sync cannot recover from."""


class PageNotAvailable(Exception):
    """The page does not exist or is not shared with the integration (404/403)."""


def normalize_id(value: str) -> str:
    """Notion page URLs use the ID without dashes."""
    return value.strip().replace("-", "")


def make_session(token: str | None = None) -> requests.Session:
    """Build a session with the auth and version headers. The token comes from NOTION_TOKEN."""
    token = token if token is not None else os.environ.get("NOTION_TOKEN", "").strip()
    if not token:
        raise NotionError(
            "NOTION_TOKEN is not set. Export the integration token in the environment "
            "(see .env.example) or switch the contract to source_of_truth: markdown."
        )
    session = requests.Session()
    session.headers.update(
        {
            "Authorization": f"Bearer {token}",
            "Notion-Version": NOTION_VERSION,
            "Accept": "application/json",
        }
    )
    return session


def api_get(session: requests.Session, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """GET one API path with retry/backoff on 429 and 5xx. Never logs headers."""
    url = f"{API_BASE}{path}"
    attempt = 0
    while True:
        try:
            response = session.get(url, params=params, timeout=TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            # Network-level failure: retry like a 5xx, then give up.
            if attempt >= MAX_RETRIES:
                raise NotionError(f"request failed for {path}: {exc.__class__.__name__}") from None
            time.sleep(2**attempt)
            attempt += 1
            continue

        if response.status_code in (404, 403):
            raise PageNotAvailable(f"HTTP {response.status_code} for {path}")

        if response.status_code == 429 or response.status_code >= 500:
            if attempt >= MAX_RETRIES:
                raise NotionError(f"HTTP {response.status_code} for {path} after {MAX_RETRIES} retries")
            retry_after = response.headers.get("Retry-After")
            try:
                wait = float(retry_after) if retry_after else float(2**attempt)
            except ValueError:
                wait = float(2**attempt)
            time.sleep(min(wait, 60.0))
            attempt += 1
            continue

        if response.status_code >= 400:
            # Notion's error body has "code" and "message"; neither echoes the token.
            detail = ""
            try:
                payload = response.json()
                detail = f": {payload.get('code', '')} {payload.get('message', '')}".rstrip()
            except ValueError:
                pass
            raise NotionError(f"HTTP {response.status_code} for {path}{detail}")

        return response.json()


# --- Fetching -------------------------------------------------------------------------


def fetch_title(session: requests.Session, page_id: str) -> str:
    """The page title is the property whose type is "title"."""
    page = api_get(session, f"/pages/{page_id}")
    for prop in (page.get("properties") or {}).values():
        if prop.get("type") == "title":
            return "".join(part.get("plain_text", "") for part in prop.get("title", [])).strip()
    return ""


def fetch_children(session: requests.Session, block_id: str) -> list[dict[str, Any]]:
    """All child blocks of a block or page, following pagination."""
    blocks: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"page_size": PAGE_SIZE}
        if cursor:
            params["start_cursor"] = cursor
        payload = api_get(session, f"/blocks/{block_id}/children", params)
        blocks.extend(payload.get("results", []))
        if not payload.get("has_more"):
            return blocks
        cursor = payload.get("next_cursor")
        if not cursor:
            return blocks


# --- Conversion to markdown ------------------------------------------------------------


def rich_text_to_markdown(rich_text: list[dict[str, Any]] | None) -> str:
    """Join Notion rich-text segments into inline markdown."""
    parts: list[str] = []
    for segment in rich_text or []:
        text = segment.get("plain_text", "")
        if not text:
            continue
        annotations = segment.get("annotations") or {}
        href = segment.get("href")

        # Markdown markers must hug the text, so keep surrounding whitespace outside them.
        core = text.strip()
        if not core:
            parts.append(text)  # whitespace-only segment: nothing to style
            continue
        leading = text[: len(text) - len(text.lstrip())]
        trailing = text[len(text.rstrip()):]
        if annotations.get("code"):
            core = f"`{core}`"
        if annotations.get("bold"):
            core = f"**{core}**"
        if annotations.get("italic"):
            core = f"*{core}*"
        if annotations.get("strikethrough"):
            core = f"~~{core}~~"
        if href:
            core = f"[{core}]({href})"
        parts.append(leading + core + trailing)
    return "".join(parts)


def plain_text(rich_text: list[dict[str, Any]] | None) -> str:
    """Rich text without any styling (used inside code blocks)."""
    return "".join(segment.get("plain_text", "") for segment in rich_text or [])


def _table_cell(rich_text: list[dict[str, Any]]) -> str:
    return rich_text_to_markdown(rich_text).replace("\n", " ").replace("|", "\\|").strip()


def _render_table(block: dict[str, Any], rows: list[dict[str, Any]]) -> list[str]:
    table = block.get("table") or {}
    cells = [[_table_cell(cell) for cell in row.get("table_row", {}).get("cells", [])] for row in rows if row.get("type") == "table_row"]
    width = int(table.get("table_width") or max((len(row) for row in cells), default=0))
    if width == 0:
        return ["<!-- empty table -->", ""]

    def pad(row: list[str]) -> list[str]:
        return (row + [""] * width)[:width]

    if table.get("has_column_header") and cells:
        header, body = pad(cells[0]), cells[1:]
    else:
        header, body = [""] * width, cells  # markdown needs a header row; Notion did not have one
    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * width) + " |"]
    for row in body:
        lines.append("| " + " | ".join(pad(row)) + " |")
    lines.append("")
    return lines


def _prefix_lines(lines: list[str], prefix: str) -> list[str]:
    return [(prefix + line) if line else line.rstrip() for line in lines]


# Block types whose children are nested *inside* them in markdown.
LIST_LIKE = {"bulleted_list_item", "numbered_list_item", "to_do", "toggle"}
QUOTE_LIKE = {"quote", "callout"}


def blocks_to_markdown(blocks: list[dict[str, Any]], get_children: Callable[[str], list[dict[str, Any]]]) -> list[str]:
    """Convert a list of sibling blocks to markdown lines.

    `get_children(block_id)` is called for blocks that have children, so the
    function can be exercised offline with a dict-backed callable.
    """
    lines: list[str] = []
    number = 0  # running counter for numbered_list_item siblings
    for index, block in enumerate(blocks):
        block_type = block.get("type", "unknown")
        data = block.get(block_type) or {}
        text = rich_text_to_markdown(data.get("rich_text"))
        has_children = bool(block.get("has_children"))

        if block_type == "numbered_list_item":
            number += 1
        else:
            number = 0

        children: list[str] = []
        if has_children and block_type not in ("child_page", "child_database", "table"):
            children = blocks_to_markdown(get_children(block["id"]), get_children)

        if block_type == "paragraph":
            lines += [text, ""]
        elif block_type in ("heading_1", "heading_2", "heading_3"):
            level = int(block_type[-1])
            lines += ["#" * level + " " + text, ""]
        elif block_type == "bulleted_list_item":
            lines.append("- " + text)
        elif block_type == "numbered_list_item":
            lines.append(f"{number}. " + text)
        elif block_type == "to_do":
            box = "[x]" if data.get("checked") else "[ ]"
            lines.append(f"- {box} " + text)
        elif block_type == "toggle":
            lines.append("- " + text)
        elif block_type == "quote":
            lines += _prefix_lines(text.split("\n"), "> ")
        elif block_type == "callout":
            icon = data.get("icon") or {}
            emoji = icon.get("emoji", "") if icon.get("type") == "emoji" else ""
            first = f"{emoji} {text}".strip()
            lines += _prefix_lines(first.split("\n"), "> ")
        elif block_type == "code":
            language = str(data.get("language") or "").replace("plain text", "").strip()
            lines += [f"```{language}", plain_text(data.get("rich_text")), "```", ""]
        elif block_type == "divider":
            lines += ["---", ""]
        elif block_type == "table":
            rows = get_children(block["id"]) if has_children else []
            lines += _render_table(block, rows)
        elif block_type == "child_page":
            title = data.get("title", "")
            lines += [f"*Child page: {title} (Notion ID {normalize_id(block.get('id', ''))}; not exported inline)*", ""]
        elif block_type == "child_database":
            title = data.get("title", "")
            lines += [f"*Child database: {title} (Notion ID {normalize_id(block.get('id', ''))}; not exported inline)*", ""]
        else:
            lines += [f"<!-- unsupported block: {block_type} -->", ""]

        # Nest children under list items and quotes; render them flat elsewhere.
        if children:
            while children and children[-1] == "":
                children.pop()  # the parent decides where the blank line goes
            if block_type in LIST_LIKE:
                lines += _prefix_lines(children, "    ")
            elif block_type in QUOTE_LIKE:
                lines += _prefix_lines(children, "> ")
            else:
                lines += children + [""]

        # Quotes always end with a blank line; a list ends with one when the next
        # sibling is a different kind of block (so "- a" and "1. b" do not merge).
        if block_type in QUOTE_LIKE:
            lines.append("")
        elif block_type in LIST_LIKE:
            next_type = blocks[index + 1].get("type") if index + 1 < len(blocks) else None
            if next_type != block_type:
                lines.append("")

    # Collapse runs of blank lines so the export stays tidy.
    tidy: list[str] = []
    for line in lines:
        if line == "" and tidy and tidy[-1] == "":
            continue
        tidy.append(line)
    return tidy


def fetch_page_markdown(session: requests.Session, page_id: str) -> str:
    """Download and convert the whole page body."""
    blocks = fetch_children(session, page_id)
    lines = blocks_to_markdown(blocks, lambda block_id: fetch_children(session, block_id))
    return "\n".join(lines).strip() + "\n"


# --- Adapter class --------------------------------------------------------------------------


class NotionAdapter:
    """Reads pages by ID from the Notion API."""

    def __init__(self, ctx: SyncContext, session: requests.Session | None = None):
        self.ctx = ctx
        self.session = session if session is not None else make_session()

    def fetch_page(self, slug: str, entry: dict[str, Any]) -> FetchedPage:
        raw_id = str(entry.get("id", "")).strip()
        page_id = normalize_id(raw_id)
        page = FetchedPage(
            slug=slug,
            title=slug,
            status=str(entry.get("status", "")),
            owner=str(entry.get("owner") or entry.get("owner_role") or ""),
            review=str(entry.get("review", "")),
            url=self.ctx.page_url_base + page_id,
            available=False,
        )
        if not NOTION_ID_RE.match(raw_id):
            page.problems.append(f"{slug}: id {raw_id!r} is not a Notion page ID (32 hex characters)")
            return page
        try:
            title = fetch_title(self.session, page_id) or slug
            body = fetch_page_markdown(self.session, page_id)
        except PageNotAvailable as exc:
            page.notes.append(f"page not available: {exc}")
            return page
        except NotionError as exc:
            page.problems.append(f"{slug}: {exc}")
            return page

        contract = self.ctx.contract
        fields: dict[str, Any] = {
            "slug": slug,
            "title": title,
            "owner": page.owner,
            "status": page.status,
            "review": page.review,
            "last_reviewed": to_date(contract.get("last_reviewed")) or str(contract.get("last_reviewed", "")),
            "next_review": to_date(contract.get("next_review")) or str(contract.get("next_review", "")),
            "visibility": entry.get("visibility") or contract.get("visibility") or contract.get("default_visibility", ""),
        }
        page.available = True
        page.title = title
        page.frontmatter = render_frontmatter(fields)
        page.body = body
        page.next_review = to_date(contract.get("next_review"))
        return page
