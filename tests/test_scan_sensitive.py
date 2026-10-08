"""Tests for scan_sensitive.py.

Every planted secret or address is assembled at runtime (string concatenation) so
that scanning this repository with scan_sensitive.py stays clean.
"""

from __future__ import annotations

from pathlib import Path

from conftest import run_cli

FAKE_AWS_KEY = "AKIA" + "IOSFODNN7EXAMPLE"  # the well-known documentation example key
PERSON_EMAIL = "ops" + "@" + "acme-analytics.test"
EXAMPLE_EMAIL = "support" + "@" + "example.com"
PUBLIC_IP = "8.8." + "4.4"
PHONE_PLUS_ONE = "+1 (" + "555) 010-0199"
PHONE_PARENS = "(" + "555) 010-0198"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_planted_key_and_email_are_found(tmp_path: Path):
    write(tmp_path / "notes.md", f"aws key {FAKE_AWS_KEY}\nmail {PERSON_EMAIL}\nfine {EXAMPLE_EMAIL}\n")
    result = run_cli("scan_sensitive.py", str(tmp_path))
    assert result.returncode == 1
    assert "notes.md:1: secret (AWS access key id (AKIA))" in result.stdout
    assert FAKE_AWS_KEY not in result.stdout, "secrets must be masked in the report"
    assert f"notes.md:2: email: {PERSON_EMAIL}" in result.stdout
    assert EXAMPLE_EMAIL not in result.stdout, "*@example.com is ignored"
    assert "2 finding(s)" in result.stdout


def test_clean_tree_passes(tmp_path: Path):
    write(tmp_path / "docs/readme.md", "Acme Analytics builds product analytics. Contact " + EXAMPLE_EMAIL + "\n")
    write(tmp_path / "docs/notice.md", "automated mail from no-reply" + "@" + "acme-analytics.test\n")
    write(tmp_path / "net.md", "listen on 127.0.0.1 and 10.1.2.3; docs use 192.0.2.10\n")
    result = run_cli("scan_sensitive.py", str(tmp_path))
    assert result.returncode == 0, result.stdout
    assert "0 finding(s)" in result.stdout


def test_denylist_allow_file_and_skips(tmp_path: Path):
    write(tmp_path / "plan.md", "Project Nightjar kickoff with " + PERSON_EMAIL + " at " + PUBLIC_IP + "\n")
    write(tmp_path / "export/canon/page.md", "Nightjar " + FAKE_AWS_KEY + "\n")  # export/ is skipped
    write(tmp_path / "node_modules/pkg/index.js", "const k = '" + FAKE_AWS_KEY + "';\n")  # skipped
    write(tmp_path / ".sensitive-denylist", "# local only, never committed\nnightjar\n")
    write(tmp_path / "allow.txt", PERSON_EMAIL + "\n")

    result = run_cli("scan_sensitive.py", str(tmp_path), "--allow", str(tmp_path / "allow.txt"))
    assert result.returncode == 1
    lines = [line for line in result.stdout.splitlines() if not line.startswith("scan_sensitive:")]
    assert len(lines) == 2, result.stdout
    joined = "\n".join(lines)
    assert f"plan.md:1: public IPv4: {PUBLIC_IP}" in joined
    assert "plan.md:1: denylist term: nightjar" in joined
    assert PERSON_EMAIL not in joined, "allow-listed email is ignored"
    assert "export/" not in joined and "node_modules" not in joined
    assert ".sensitive-denylist" not in joined, "the denylist file itself is never scanned"
    assert "1 denylist term(s)" in result.stdout


def test_phone_numbers_are_conservative(tmp_path: Path):
    write(tmp_path / "a.md", f"call {PHONE_PLUS_ONE} or {PHONE_PARENS}\n")
    write(tmp_path / "b.md", "ticket 555-0100 and version 2.4.1.9000 and 2026-10-08\n")
    result = run_cli("scan_sensitive.py", str(tmp_path))
    assert result.returncode == 1
    assert f"a.md:1: phone: {PHONE_PLUS_ONE}" in result.stdout
    assert f"a.md:1: phone: {PHONE_PARENS}" in result.stdout
    assert "b.md" not in result.stdout, "a bare 7-digit number is not reported"


def test_missing_path_is_a_usage_error(tmp_path: Path):
    result = run_cli("scan_sensitive.py", str(tmp_path / "nowhere"))
    assert result.returncode == 2
