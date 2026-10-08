#!/usr/bin/env python3
"""scan_sensitive: find strings that must never be committed to a public context repo.

    python scripts/scan_sensitive.py [PATH] [--denylist FILE] [--allow FILE]

Scans every text file under PATH (default: the current directory) and reports,
as path:line: kind: text,

  - secret-looking strings: Notion secret_/ntn_ tokens, OpenAI-style sk- keys,
    Stripe sk_live/rk_live keys, GitHub gh*_ tokens, Slack xox* tokens, AWS
    AKIA access keys, Google AIza API keys, PEM private-key blocks, JWTs
    (the matched text is masked in the output)
  - email addresses, except *@example.com/.org/.net, noreply/no-reply senders,
    and addresses listed in the allow file
  - phone-number-like strings, conservatively: +1 forms and (ddd) ddd-dddd forms
  - public IPv4 addresses (RFC 1918, loopback, link-local, documentation and
    other reserved ranges are ignored)
  - every term in the denylist file, case-insensitively

Skipped: .git, node_modules, virtual environments, caches, binary files, and the
generated export/ folder directly under PATH (it is produced from sources that
are scanned anyway). The denylist and allow files themselves are never scanned.

The denylist is where a team puts the real names it must keep out of a public
repo: people, clients, internal project code names, hostnames. This repository
ships NO denylist, because the file would itself be the leak. Keep your own as
`.sensitive-denylist` next to the repo root (it is gitignored and picked up
automatically) and, for CI, store the same lines in a repository secret that the
workflow writes to a temporary file outside the checkout.

Exit codes: 0 nothing found, 1 findings, 2 bad command line.
"""

from __future__ import annotations

import argparse
import ipaddress
import os
import re
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import SECRET_PATTERNS, mask  # noqa: E402

DEFAULT_DENYLIST_NAME = ".sensitive-denylist"
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".tox"}
SKIP_TOP_LEVEL_DIRS = {"export"}
BINARY_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".gz", ".tar", ".pyc", ".woff", ".woff2", ".ttf", ".mp4", ".mp3", ".docx", ".xlsx", ".pptx"}
MAX_FILE_BYTES = 10 * 1024 * 1024

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
EXAMPLE_DOMAINS = ("example.com", "example.org", "example.net")
NOREPLY_PREFIXES = ("noreply", "no-reply", "no_reply", "donotreply", "do-not-reply")

PHONE_PATTERNS = [
    re.compile(r"\+1[ .-]?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b"),  # "+1", then area code (optionally in parentheses), then 3 + 4 digits
    re.compile(r"\(\d{3}\)[ .-]?\d{3}[ .-]\d{4}\b"),  # area code in parentheses, then 3 digits, a separator, 4 digits
]

IPV4_RE = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
IGNORED_NETWORKS = [
    ipaddress.ip_network(net)
    for net in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",  # RFC 1918
        "127.0.0.0/8",  # loopback
        "169.254.0.0/16",  # link-local
        "0.0.0.0/8",
        "192.0.2.0/24",
        "198.51.100.0/24",
        "203.0.113.0/24",  # documentation (RFC 5737)
        "224.0.0.0/4",  # multicast
        "240.0.0.0/4",  # reserved, includes 255.255.255.255
    )
]


def read_terms(path: Path | None) -> list[str]:
    """One term per line; blank lines and lines starting with # are ignored."""
    if path is None or not path.is_file():
        return []
    terms = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        term = line.strip()
        if term and not term.startswith("#"):
            terms.append(term)
    return terms


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
        with open(path, "rb") as handle:
            sample = handle.read(8192)
    except OSError:
        return False
    return b"\x00" not in sample


def iter_files(root: Path, excluded: set[Path]):
    """Yield text files under root, pruning skipped directories."""
    root = root.resolve()
    if root.is_file():
        if root not in excluded and is_text_file(root):
            yield root
        return
    for current, dirnames, filenames in os.walk(root):
        current_path = Path(current)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if name not in SKIP_DIRS and not (current_path == root and name in SKIP_TOP_LEVEL_DIRS)
        )
        for name in sorted(filenames):
            path = current_path / name
            if path in excluded or path.is_symlink():
                continue
            if is_text_file(path):
                yield path


def public_ip(text: str) -> bool:
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    return not any(address in network for network in IGNORED_NETWORKS)


def email_is_ignored(address: str, allow: set[str]) -> bool:
    lowered = address.lower()
    local, _, domain = lowered.partition("@")
    if lowered in allow:
        return True
    if domain in EXAMPLE_DOMAINS or any(domain.endswith("." + d) for d in EXAMPLE_DOMAINS):
        return True
    return local.startswith(NOREPLY_PREFIXES)


def scan_line(line: str, denylist: list[tuple[str, re.Pattern[str]]], allow: set[str]) -> list[tuple[str, str]]:
    """Return (kind, display_text) findings for one line."""
    findings: list[tuple[str, str]] = []
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(line):
            findings.append((f"secret ({label})", mask(match.group(0))))
    for match in EMAIL_RE.finditer(line):
        if not email_is_ignored(match.group(0), allow):
            findings.append(("email", match.group(0)))
    phone_spans: list[tuple[int, int]] = []  # the two phone patterns can overlap; report each number once
    for pattern in PHONE_PATTERNS:
        for match in pattern.finditer(line):
            if any(start < match.end() and match.start() < end for start, end in phone_spans):
                continue
            phone_spans.append(match.span())
            if match.group(0).lower() not in allow:
                findings.append(("phone", match.group(0)))
    for match in IPV4_RE.finditer(line):
        if public_ip(match.group(0)) and match.group(0) not in allow:
            findings.append(("public IPv4", match.group(0)))
    for term, pattern in denylist:
        if pattern.search(line):
            findings.append(("denylist term", term))
    return findings


def compile_denylist(terms: list[str]) -> list[tuple[str, re.Pattern[str]]]:
    """(term, case-insensitive literal pattern) for every denylist line."""
    return [(term, re.compile(re.escape(term), re.IGNORECASE)) for term in terms]


def scan(root: Path, denylist_path: Path | None, allow_path: Path | None) -> tuple[list[str], int]:
    """Scan root; return (finding lines, files scanned)."""
    denylist = compile_denylist(read_terms(denylist_path))
    allow = {term.lower() for term in read_terms(allow_path)}
    excluded = {path.resolve() for path in (denylist_path, allow_path) if path is not None}

    findings: list[str] = []
    scanned = 0
    for path in iter_files(root, excluded):
        scanned += 1
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            shown = path.relative_to(Path.cwd())
        except ValueError:
            shown = path
        for number, line in enumerate(text.splitlines(), start=1):
            for kind, display in scan_line(line, denylist, allow):
                findings.append(f"{shown}:{number}: {kind}: {display}")
    return findings, scanned


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=".", help="file or directory to scan (default: .)")
    parser.add_argument("--denylist", help=f"terms to flag, one per line (default: {DEFAULT_DENYLIST_NAME} under PATH when present)")
    parser.add_argument("--allow", help="emails/phones/IPs to ignore, one per line")
    parser.add_argument("-q", "--quiet", action="store_true", help="print findings only, no summary")
    args = parser.parse_args(argv)

    root = Path(args.path)
    if not root.exists():
        print(f"ERROR: {root} does not exist", file=sys.stderr)
        return 2
    denylist_path = Path(args.denylist) if args.denylist else None
    if denylist_path is None:
        candidate = (root if root.is_dir() else root.parent) / DEFAULT_DENYLIST_NAME
        denylist_path = candidate if candidate.is_file() else None
    elif not denylist_path.is_file():
        print(f"ERROR: denylist {denylist_path} does not exist", file=sys.stderr)
        return 2
    allow_path = Path(args.allow) if args.allow else None
    if allow_path is not None and not allow_path.is_file():
        print(f"ERROR: allow file {allow_path} does not exist", file=sys.stderr)
        return 2

    findings, scanned = scan(root, denylist_path, allow_path)
    for finding in findings:
        print(finding)
    if not args.quiet:
        terms = len(read_terms(denylist_path))
        denylist_note = f"{terms} denylist term(s)" if denylist_path else "no denylist"
        print(f"scan_sensitive: {len(findings)} finding(s) in {scanned} file(s); {denylist_note}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
