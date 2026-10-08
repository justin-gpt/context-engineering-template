"""Shared helpers for the scripts in this folder.

Everything here is deliberately small and boring so that a team copying one
script into their own repo can also copy this file and read it in a minute.

Contents
- repo paths and JSON Schema loading (schemas/json/*.json, optional)
- the allowed enum values from docs/formats.md
- date and JSON helpers (YAML gives us datetime.date objects; JSON wants strings)
- the secret-looking patterns shared by validate_contract.py and scan_sensitive.py
"""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Iterator

import yaml

# scripts/common.py -> parents[0] is scripts/, parents[1] is the repo root.
REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = REPO_ROOT / "schemas" / "json"

# --- Allowed values (docs/formats.md sections 1 to 3) -------------------------

STATUS_VALUES = ("grounded", "draft", "stub", "deprecated")
REVIEW_VALUES = ("monthly", "quarterly", "on_change")
VISIBILITY_VALUES = ("company_internal", "client_private", "client_shared", "public")
RISK_CLASS_VALUES = ("read_only", "draft_write", "controlled_write", "external_action")
MIRROR_POLICY_VALUES = ("generated_read_only",)
SOURCE_OF_TRUTH_VALUES = ("notion", "markdown", "confluence")
SYNC_VALUES = ("nightly", "six_hourly", "weekly", "manual")

# Caveat strings that travel in the generated header (docs/formats.md section 5).
CAVEATS = {
    "grounded": "grounded: may be asserted and cited",
    "draft": "draft: use only when labeled unconfirmed",
    "stub": "stub: do not load as truth; report the coverage gap",
    "deprecated": "deprecated: do not use; follow the replacement link",
}

# --- Secret-looking strings ----------------------------------------------------
# Each entry: (label, compiled regex). Shared by validate_contract.py (no value
# in a contract may look like a credential) and scan_sensitive.py (whole repo).
# Patterns are anchored on word boundaries so that prose like "risk-class" or
# "secret-manager://..." (a reference, not a secret) does not trip them.
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Notion token (secret_/ntn_)", re.compile(r"\b(?:secret|ntn)_[A-Za-z0-9]{20,}")),
    ("OpenAI-style key (sk-)", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}")),
    ("Stripe live key (sk_live/rk_live)", re.compile(r"\b[sr]k_live_[A-Za-z0-9]{8,}")),
    ("GitHub token (ghp_/gho_/ghu_/ghs_/ghr_)", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("Slack token (xox*)", re.compile(r"\bxox[abprse]-[A-Za-z0-9-]{10,}")),
    ("AWS access key id (AKIA)", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Google API key (AIza)", re.compile(r"\bAIza[0-9A-Za-z_-]{35}")),
    ("PEM block (private key or certificate)", re.compile(r"-----BEGIN [A-Z ]+-----")),
    ("JWT", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
]


def find_secret_like(text: str) -> list[tuple[str, str]]:
    """Return (label, matched_text) for every secret-looking substring in text."""
    found: list[tuple[str, str]] = []
    for label, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            found.append((label, match.group(0)))
    return found


def mask(value: str) -> str:
    """Show the first few characters only, so a finding never reprints a secret."""
    if len(value) <= 6:
        return value[:2] + "..."
    return value[:6] + "..." + f"({len(value)} chars)"


# --- Dates and times -----------------------------------------------------------


def utc_now() -> dt.datetime:
    """Current time in UTC with second precision (the clocks are second-granular)."""
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


def iso_z(moment: dt.datetime) -> str:
    """Format a datetime the way meta.json wants it: 2026-10-08T02:00:14Z."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=dt.timezone.utc)
    return moment.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso_z(value: str) -> dt.datetime:
    """Parse 2026-10-08T02:00:14Z (or any ISO 8601 string) into an aware datetime."""
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    parsed = dt.datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def to_date(value: Any) -> dt.date | None:
    """Coerce a YAML value into a date, or None when it is not an ISO date.

    PyYAML already turns an unquoted 2026-10-08 into datetime.date; a quoted
    "2026-10-08" arrives as a string and is parsed here.
    """
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
            try:
                return dt.date.fromisoformat(text)
            except ValueError:
                return None
    return None


# --- YAML / JSON -----------------------------------------------------------------


def load_yaml(path: Path) -> Any:
    """Load one YAML document with the safe loader."""
    with open(path, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def json_ready(obj: Any) -> Any:
    """Recursively convert YAML-loaded data into JSON-serialisable data.

    Dates become ISO strings; everything else JSON already understands.
    """
    if isinstance(obj, dict):
        return {str(key): json_ready(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [json_ready(item) for item in obj]
    if isinstance(obj, dt.datetime):
        return iso_z(obj)
    if isinstance(obj, dt.date):
        return obj.isoformat()
    return obj


def iter_strings(obj: Any, path: str = "") -> Iterator[tuple[str, str]]:
    """Yield (dotted.path, value) for every string inside nested YAML data."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_strings(value, f"{path}.{key}" if path else str(key))
    elif isinstance(obj, (list, tuple)):
        for index, value in enumerate(obj):
            yield from iter_strings(value, f"{path}[{index}]")
    elif isinstance(obj, str):
        yield path or "<root>", obj


# --- JSON Schema (optional) ---------------------------------------------------------


def load_schema(name: str) -> dict | None:
    """Return schemas/json/<name> as a dict, or None when the file does not exist yet.

    The schemas are maintained separately from the scripts. When a schema is
    missing the callers fall back to their built-in structural checks.
    """
    path = SCHEMA_DIR / name
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def schema_errors(instance: Any, schema: dict, label: str = "schema") -> list[str]:
    """Validate instance against a JSON Schema and return readable error strings."""
    import jsonschema  # imported here so the other helpers work without it

    validator_class = jsonschema.validators.validator_for(schema)
    validator_class.check_schema(schema)
    validator = validator_class(schema, format_checker=validator_class.FORMAT_CHECKER)
    problems = []
    for error in sorted(validator.iter_errors(json_ready(instance)), key=lambda e: list(e.absolute_path)):
        where = "/".join(str(part) for part in error.absolute_path) or "<root>"
        problems.append(f"{label}: {where}: {error.message}")
    return problems


# --- Paths ---------------------------------------------------------------------------


def resolve_relative(value: str, base_dirs: list[Path]) -> Path:
    """Resolve a path from a contract: absolute as-is, otherwise the first base dir where it exists.

    The sample contract says `source_root: templates/canon`, which is relative to
    the repo root. We try the current working directory first, then each base
    dir given (normally the repo root), and fall back to the first candidate so
    the caller can report a clear "not found" message.
    """
    candidate = Path(value).expanduser()
    if candidate.is_absolute():
        return candidate
    tried = [Path.cwd() / candidate] + [base / candidate for base in base_dirs]
    for option in tried:
        if option.exists():
            return option
    return tried[0]
