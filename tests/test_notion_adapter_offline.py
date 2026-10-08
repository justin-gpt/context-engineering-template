"""Offline tests for the Notion adapter.

No network, no token: the block-to-markdown conversion is exercised with
hand-written block dicts, and the HTTP behaviour (404 placeholder, 429 retry)
with a fake session object. Running the adapter against a real workspace is a
manual step; see the module docstring in scripts/adapters/notion.py.
"""

from __future__ import annotations

import datetime as dt

import pytest

from adapters import notion
from adapters.base import SyncContext

PAGE_ID = "0123456789abcdef0123456789abcdef"


def rt(text: str, **annotations) -> dict:
    """Build one rich-text segment."""
    base = {"bold": False, "italic": False, "strikethrough": False, "underline": False, "code": False}
    base.update(annotations)
    href = annotations.pop("href", None)
    return {"type": "text", "plain_text": text, "annotations": base, "href": href}


def block(block_type: str, block_id: str = "b1", children: bool = False, **data) -> dict:
    return {"id": block_id, "type": block_type, "has_children": children, block_type: data}


def test_rich_text_annotations_and_links():
    segments = [
        rt("plain "),
        rt("bold", bold=True),
        rt(" and "),
        rt("code", code=True),
        rt(" then "),
        rt("a link ", href="https://example.com/x"),
        rt("gone", strikethrough=True),
        rt(" ", italic=True),  # whitespace-only styled text must not produce "* *"
    ]
    assert notion.rich_text_to_markdown(segments) == "plain **bold** and `code` then [a link](https://example.com/x) ~~gone~~ "


def test_blocks_to_markdown_covers_the_supported_types():
    children = {
        "list1": [block("bulleted_list_item", "nested", rich_text=[rt("nested item")])],
        "tbl": [
            {"id": "r1", "type": "table_row", "has_children": False, "table_row": {"cells": [[rt("Term")], [rt("Definition")]]}},
            {"id": "r2", "type": "table_row", "has_children": False, "table_row": {"cells": [[rt("Customer")], [rt("Paying | active")]]}},
        ],
        "tog": [block("paragraph", "togp", rich_text=[rt("hidden text")])],
        "col": [block("paragraph", "colp", rich_text=[rt("inside a column")])],
    }
    blocks = [
        block("heading_1", rich_text=[rt("Title")]),
        block("paragraph", rich_text=[rt("Intro paragraph.")]),
        block("heading_2", rich_text=[rt("Section")]),
        block("bulleted_list_item", "list1", children=True, rich_text=[rt("first")]),
        block("bulleted_list_item", rich_text=[rt("second")]),
        block("numbered_list_item", rich_text=[rt("one")]),
        block("numbered_list_item", rich_text=[rt("two")]),
        block("to_do", rich_text=[rt("done")], checked=True),
        block("to_do", rich_text=[rt("open")], checked=False),
        block("quote", rich_text=[rt("a quote")]),
        block("callout", rich_text=[rt("note this")], icon={"type": "emoji", "emoji": "!"}),
        block("code", rich_text=[rt("print('hi')")], language="python"),
        block("divider"),
        block("table", "tbl", children=True, table_width=2, has_column_header=True),
        block("toggle", "tog", children=True, rich_text=[rt("Details")]),
        block("child_page", "cp", title="Deeper page"),
        block("child_database", "cd", title="Cards"),
        block("column_list", "col", children=True),
        block("embed", "em", url="https://example.com/embed"),
    ]
    text = "\n".join(notion.blocks_to_markdown(blocks, lambda block_id: children.get(block_id, [])))

    assert "# Title\n\nIntro paragraph.\n\n## Section\n" in text
    assert "- first\n    - nested item\n- second\n" in text
    assert "1. one\n2. two\n" in text
    assert "- [x] done\n- [ ] open\n" in text
    assert "> a quote\n" in text
    assert "> ! note this\n" in text
    assert "```python\nprint('hi')\n```" in text
    assert "\n---\n" in text
    assert "| Term | Definition |\n| --- | --- |\n| Customer | Paying \\| active |\n" in text
    assert "- Details\n    hidden text\n" in text
    assert "*Child page: Deeper page (Notion ID cp; not exported inline)*" in text
    assert "*Child database: Cards (Notion ID cd; not exported inline)*" in text
    assert "<!-- unsupported block: column_list -->\n\ninside a column" in text
    assert "<!-- unsupported block: embed -->" in text
    assert "\n\n\n" not in text, "no runs of blank lines"


class FakeResponse:
    def __init__(self, status_code: int, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._payload


class FakeSession:
    """Serves scripted responses per path; records what was requested."""

    def __init__(self, script: dict[str, list[FakeResponse]]):
        self.script = {path: list(responses) for path, responses in script.items()}
        self.calls: list[str] = []
        self.headers: dict[str, str] = {}

    def get(self, url, params=None, timeout=None):
        path = url.replace(notion.API_BASE, "")
        self.calls.append(path)
        responses = self.script[path]
        return responses.pop(0) if len(responses) > 1 else responses[0]


def make_ctx() -> SyncContext:
    contract = {
        "last_reviewed": dt.date(2026, 10, 8),
        "next_review": dt.date(2027, 1, 8),
        "visibility": "company_internal",
        "canonical_pages": {},
    }
    return SyncContext(contract=contract, source_root="root", page_url_base="https://www.notion.so/", today=dt.date(2026, 10, 8))


ENTRY = {"id": "01234567-89ab-cdef-0123-456789abcdef", "status": "draft", "owner": "PMM", "review": "quarterly", "visibility": "company_internal"}


def test_fetch_page_builds_frontmatter_and_url():
    session = FakeSession(
        {
            f"/pages/{PAGE_ID}": [FakeResponse(200, {"properties": {"Name": {"type": "title", "title": [rt("Messaging")]}}})],
            f"/blocks/{PAGE_ID}/children": [
                FakeResponse(200, {"results": [block("paragraph", rich_text=[rt("Hello.")])], "has_more": False}),
            ],
        }
    )
    page = notion.NotionAdapter(make_ctx(), session=session).fetch_page("messaging", ENTRY)
    assert page.available and page.problems == []
    assert page.title == "Messaging"
    assert page.url == "https://www.notion.so/" + PAGE_ID  # dashes removed
    assert page.frontmatter.startswith("---\nslug: messaging\ntitle: Messaging\nowner: PMM\nstatus: draft\n")
    assert "next_review: 2027-01-08" in page.frontmatter
    assert page.body == "Hello.\n"
    assert page.next_review == dt.date(2027, 1, 8)


def test_404_becomes_placeholder_and_429_is_retried(monkeypatch):
    monkeypatch.setattr(notion.time, "sleep", lambda seconds: None)
    session = FakeSession(
        {
            f"/pages/{PAGE_ID}": [
                FakeResponse(429, headers={"Retry-After": "1"}),
                FakeResponse(200, {"properties": {"T": {"type": "title", "title": [rt("Glossary")]}}}),
            ],
            f"/blocks/{PAGE_ID}/children": [FakeResponse(404, {"code": "object_not_found", "message": "Could not find block"})],
        }
    )
    page = notion.NotionAdapter(make_ctx(), session=session).fetch_page("glossary", ENTRY)
    assert page.available is False
    assert page.problems == []
    assert any("page not available" in note and "404" in note for note in page.notes)
    assert session.calls.count(f"/pages/{PAGE_ID}") == 2, "the 429 was retried once"


def test_bad_page_id_is_a_validation_problem():
    session = FakeSession({})
    page = notion.NotionAdapter(make_ctx(), session=session).fetch_page("company_readme", dict(ENTRY, id="<page-id>"))
    assert page.available is False
    assert page.problems and "not a Notion page ID" in page.problems[0]
    assert session.calls == []


def test_missing_token_is_a_clear_error(monkeypatch):
    monkeypatch.delenv("NOTION_TOKEN", raising=False)
    with pytest.raises(notion.NotionError, match="NOTION_TOKEN is not set"):
        notion.NotionAdapter(make_ctx())
