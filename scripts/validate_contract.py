#!/usr/bin/env python3
"""Validate context contracts and project manifests.

Usage:
    python scripts/validate_contract.py PATH [PATH ...]

The kind of each file is detected from its keys:
    business contract  -> has canonical_pages and no client_id   (docs/formats.md section 1)
    client contract    -> has client_id                          (section 2)
    project manifest   -> has deployment_id                      (section 3)

Two layers of checks run on every file:
1. The matching JSON Schema in schemas/json/, when that file exists. The schemas
   are maintained separately; when one is missing this script says so and relies
   on layer 2 alone.
2. Built-in structural checks that always run: required keys, allowed enum values
   (status, review, visibility, risk_class, mirror_policy, source_of_truth),
   owners present, ISO dates, next_review after last_reviewed, 1 to 12 canonical
   pages, and no value anywhere in the file that looks like a secret.

Exit codes: 0 all files valid, 1 at least one problem (or a file could not be read),
2 bad command line.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

# Make the sibling modules importable whether this file is run as a script
# (python scripts/validate_contract.py) or imported by the tests.
SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import (  # noqa: E402
    MIRROR_POLICY_VALUES,
    REVIEW_VALUES,
    RISK_CLASS_VALUES,
    SOURCE_OF_TRUTH_VALUES,
    STATUS_VALUES,
    SYNC_VALUES,
    VISIBILITY_VALUES,
    find_secret_like,
    iter_strings,
    load_schema,
    mask,
    schema_errors,
    to_date,
)

KIND_BUSINESS = "business contract"
KIND_CLIENT = "client contract"
KIND_MANIFEST = "project manifest"

SCHEMA_FILES = {
    KIND_BUSINESS: "context-contract.schema.json",
    KIND_CLIENT: "client-context-contract.schema.json",
    KIND_MANIFEST: "project-manifest.schema.json",
}

MAX_CANONICAL_PAGES = 12


# --- Small check helpers -----------------------------------------------------------------


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and value.strip() != ""


def _require(data: dict, key: str, errors: list[str], where: str = "") -> Any:
    """Report a missing or empty key; return the value (or None)."""
    label = f"{where}.{key}" if where else key
    if key not in data:
        errors.append(f"missing required key: {label}")
        return None
    value = data[key]
    if value is None or (isinstance(value, (str, list, dict)) and len(value) == 0):
        errors.append(f"{label} must not be empty")
        return None
    return value


def _check_enum(value: Any, allowed: tuple[str, ...], label: str, errors: list[str]) -> None:
    if value is None:
        return
    if value not in allowed:
        errors.append(f"{label} is {value!r}; allowed values: {', '.join(allowed)}")


def _check_date(value: Any, label: str, errors: list[str]):
    if value is None:
        return None
    parsed = to_date(value)
    if parsed is None:
        errors.append(f"{label} must be an ISO date (YYYY-MM-DD), got {value!r}")
    return parsed


def _check_review_dates(data: dict, errors: list[str]) -> None:
    last = _check_date(_require(data, "last_reviewed", errors), "last_reviewed", errors)
    nxt = _check_date(_require(data, "next_review", errors), "next_review", errors)
    if last and nxt and nxt <= last:
        errors.append(f"next_review ({nxt}) must be after last_reviewed ({last})")


def _check_list_of_str(value: Any, label: str, errors: list[str]) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(_is_nonempty_str(item) for item in value):
        errors.append(f"{label} must be a list of non-empty strings")


def _check_canonical_pages(data: dict, errors: list[str], owner_keys: tuple[str, ...]) -> dict:
    """Shared by the business and client contracts. Returns the pages dict (or {})."""
    pages = _require(data, "canonical_pages", errors)
    if pages is None:
        return {}
    if not isinstance(pages, dict):
        errors.append("canonical_pages must be a mapping of slug -> page entry")
        return {}
    if not 1 <= len(pages) <= MAX_CANONICAL_PAGES:
        errors.append(f"canonical_pages must have 1 to {MAX_CANONICAL_PAGES} entries, found {len(pages)}")
    for slug, entry in pages.items():
        where = f"canonical_pages.{slug}"
        if not isinstance(entry, dict):
            errors.append(f"{where} must be a mapping")
            continue
        if not _is_nonempty_str(entry.get("id")):
            errors.append(f"{where}.id must be a non-empty string (page ID or relative path)")
        _check_enum(_require(entry, "status", errors, where), STATUS_VALUES, f"{where}.status", errors)
        _check_enum(_require(entry, "review", errors, where), REVIEW_VALUES, f"{where}.review", errors)
        _check_enum(_require(entry, "visibility", errors, where), VISIBILITY_VALUES, f"{where}.visibility", errors)
        owner = next((entry.get(key) for key in owner_keys if key in entry), None)
        if not _is_nonempty_str(owner):
            errors.append(f"{where} needs a non-empty owner role ({' or '.join(owner_keys)})")
    return pages


def _check_control_pages(slugs: list[Any], pages: dict, label: str, errors: list[str]) -> None:
    for slug in slugs:
        if slug not in pages:
            errors.append(f"{label} names {slug!r}, which is not a canonical page")


# --- Structural checks per kind -----------------------------------------------------------


def structural_business(data: dict) -> list[str]:
    errors: list[str] = []
    version = _require(data, "contract_version", errors)
    if version is not None and not isinstance(version, int):
        errors.append("contract_version must be an integer")
    _check_review_dates(data, errors)
    _check_enum(_require(data, "source_of_truth", errors), SOURCE_OF_TRUTH_VALUES, "source_of_truth", errors)
    _require(data, "source_root", errors)
    _check_enum(_require(data, "mirror_policy", errors), MIRROR_POLICY_VALUES, "mirror_policy", errors)
    _check_enum(_require(data, "visibility", errors), VISIBILITY_VALUES, "visibility", errors)
    page_url_base = _require(data, "page_url_base", errors)
    if page_url_base is not None and not _is_nonempty_str(page_url_base):
        errors.append("page_url_base must be a string")

    pages = _check_canonical_pages(data, errors, owner_keys=("owner",))

    authority = _require(data, "instruction_authority", errors)
    if isinstance(authority, dict):
        control = _require(authority, "control_pages", errors, "instruction_authority")
        if isinstance(control, list):
            _check_control_pages(control, pages, "instruction_authority.control_pages", errors)
        elif control is not None:
            errors.append("instruction_authority.control_pages must be a list of slugs")
        if authority.get("retrieved_content_is_instruction") is not False:
            errors.append("instruction_authority.retrieved_content_is_instruction must be false")
        _require(authority, "conflict_action", errors, "instruction_authority")
    elif authority is not None:
        errors.append("instruction_authority must be a mapping")

    rules = _require(data, "rules", errors)
    if isinstance(rules, dict):
        for key in ("assert_only_status", "cite_page_urls", "canon_write_policy", "gap_tracker", "secrets_in_context_layer"):
            _require(rules, key, errors, "rules")
        _check_enum(rules.get("assert_only_status"), STATUS_VALUES, "rules.assert_only_status", errors)
        if rules.get("secrets_in_context_layer") not in (None, "prohibited"):
            errors.append("rules.secrets_in_context_layer must be 'prohibited'")
    elif rules is not None:
        errors.append("rules must be a mapping")

    for key in ("status_notes", "depth_not_exported"):
        if key in data and data[key] is not None and not isinstance(data[key], dict):
            errors.append(f"{key} must be a mapping when present")
    if isinstance(data.get("status_notes"), dict):
        for slug in data["status_notes"]:
            if slug not in pages:
                errors.append(f"status_notes names {slug!r}, which is not a canonical page")

    freshness = _require(data, "freshness", errors)
    if isinstance(freshness, dict):
        _check_enum(_require(freshness, "sync", errors, "freshness"), SYNC_VALUES, "freshness.sync", errors)
        days = _require(freshness, "stale_after_days", errors, "freshness")
        if days is not None and (not isinstance(days, int) or days <= 0):
            errors.append("freshness.stale_after_days must be a positive integer")
        _require(freshness, "on_stale", errors, "freshness")
    elif freshness is not None:
        errors.append("freshness must be a mapping")
    return errors


def structural_client(data: dict) -> list[str]:
    errors: list[str] = []
    version = _require(data, "contract_version", errors)
    if version is not None and not isinstance(version, int):
        errors.append("contract_version must be an integer")
    for key in ("client_id", "engagement_id", "source_root"):
        _require(data, key, errors)
    _check_enum(_require(data, "source_of_truth", errors), SOURCE_OF_TRUTH_VALUES, "source_of_truth", errors)
    _check_enum(_require(data, "mirror_policy", errors), MIRROR_POLICY_VALUES, "mirror_policy", errors)
    _check_enum(_require(data, "default_visibility", errors), VISIBILITY_VALUES, "default_visibility", errors)
    _check_review_dates(data, errors)

    # The template uses owner_role; formats.md section 1 uses owner. Accept either.
    pages = _check_canonical_pages(data, errors, owner_keys=("owner_role", "owner"))

    authority = _require(data, "instruction_authority", errors)
    if isinstance(authority, dict):
        _require(authority, "consultancy_controls", errors, "instruction_authority")
        controls = _require(authority, "client_controls", errors, "instruction_authority")
        if isinstance(controls, list):
            for index, control in enumerate(controls):
                where = f"instruction_authority.client_controls[{index}]"
                if not isinstance(control, dict):
                    errors.append(f"{where} must be a mapping with id and version")
                    continue
                _require(control, "id", errors, where)
                _require(control, "version", errors, where)
                if control.get("id") is not None:
                    _check_control_pages([control["id"]], pages, where + ".id", errors)
        elif controls is not None:
            errors.append("instruction_authority.client_controls must be a list")
        if authority.get("retrieved_content_is_instruction") is not False:
            errors.append("instruction_authority.retrieved_content_is_instruction must be false")
        _require(authority, "conflict_action", errors, "instruction_authority")
    elif authority is not None:
        errors.append("instruction_authority must be a mapping")

    rules = _require(data, "rules", errors)
    if isinstance(rules, dict):
        _check_enum(rules.get("assert_only_status"), STATUS_VALUES, "rules.assert_only_status", errors)
        if "cross_client_sources_allowed" not in rules:
            errors.append("rules.cross_client_sources_allowed is required (and must be false)")
        elif rules["cross_client_sources_allowed"] is not False:
            errors.append("rules.cross_client_sources_allowed must be false: it is the line that prevents contamination")
        if rules.get("secrets_in_context_layer") not in (None, "prohibited"):
            errors.append("rules.secrets_in_context_layer must be 'prohibited'")
    elif rules is not None:
        errors.append("rules must be a mapping")

    agents = data.get("approved_agents")
    if "approved_agents" not in data:
        errors.append("missing required key: approved_agents (use [] when no agent is approved yet)")
    elif isinstance(agents, list):
        for index, agent in enumerate(agents):
            where = f"approved_agents[{index}]"
            if not isinstance(agent, dict):
                errors.append(f"{where} must be a mapping")
                continue
            _require(agent, "deployment_id", errors, where)
            _require(agent, "purpose", errors, where)
            _check_list_of_str(_require(agent, "project_ids", errors, where), f"{where}.project_ids", errors)
            surfaces = _require(agent, "write_surfaces", errors, where)
            if surfaces is not None and not isinstance(surfaces, dict):
                errors.append(f"{where}.write_surfaces must be a mapping")
    elif agents is not None:
        errors.append("approved_agents must be a list")

    freshness = _require(data, "freshness", errors)
    if isinstance(freshness, dict):
        days = _require(freshness, "stale_after_days", errors, "freshness")
        if days is not None and (not isinstance(days, int) or days <= 0):
            errors.append("freshness.stale_after_days must be a positive integer")
        _require(freshness, "on_stale", errors, "freshness")
    elif freshness is not None:
        errors.append("freshness must be a mapping")
    return errors


def structural_manifest(data: dict) -> list[str]:
    errors: list[str] = []
    for key in ("deployment_id", "client_id", "engagement_id", "agent_id", "release", "owner", "backup_owner"):
        value = _require(data, key, errors)
        if value is not None and not _is_nonempty_str(str(value)):
            errors.append(f"{key} must be a non-empty string")
    if "release" in data and not isinstance(data["release"], str):
        errors.append("release must be a quoted string such as \"1.2.0\"")
    _check_list_of_str(_require(data, "project_ids", errors), "project_ids", errors)
    _check_enum(_require(data, "risk_class", errors), RISK_CLASS_VALUES, "risk_class", errors)

    context = _require(data, "context", errors)
    if isinstance(context, dict):
        for key in ("client_contract_version", "project_manifest_version"):
            value = _require(context, key, errors, "context")
            if value is not None and not isinstance(value, int):
                errors.append(f"context.{key} must be an integer")
        for key in ("allowed_page_ids", "allowed_data_sources", "prohibited_sources"):
            _check_list_of_str(_require(context, key, errors, "context"), f"context.{key}", errors)
    elif context is not None:
        errors.append("context must be a mapping")

    for key in ("skills", "plugins"):
        items = data.get(key)
        if key not in data:
            errors.append(f"missing required key: {key} (use [] when there are none)")
        elif not isinstance(items, list):
            errors.append(f"{key} must be a list")
        else:
            for index, item in enumerate(items):
                where = f"{key}[{index}]"
                if not isinstance(item, dict):
                    errors.append(f"{where} must be a mapping with id and version")
                    continue
                _require(item, "id", errors, where)
                version = _require(item, "version", errors, where)
                if version is not None and not isinstance(version, str):
                    errors.append(f"{where}.version must be a quoted string")

    integrations = data.get("integrations")
    if "integrations" not in data:
        errors.append("missing required key: integrations (use [] when there are none)")
    elif not isinstance(integrations, list):
        errors.append("integrations must be a list")
    else:
        for index, item in enumerate(integrations):
            where = f"integrations[{index}]"
            if not isinstance(item, dict):
                errors.append(f"{where} must be a mapping")
                continue
            _require(item, "id", errors, where)
            reference = _require(item, "credential_reference", errors, where)
            if _is_nonempty_str(reference) and "://" not in reference:
                errors.append(f"{where}.credential_reference must be a reference such as secret-manager://..., never a value")
            _require(item, "read_scope", errors, where)
            _require(item, "write_scope", errors, where)

    writes = _require(data, "writes", errors)
    if isinstance(writes, dict):
        for key in ("allowed_surfaces", "allowed_operations", "approval_required"):
            _check_list_of_str(_require(writes, key, errors, "writes"), f"writes.{key}", errors)
    elif writes is not None:
        errors.append("writes must be a mapping")

    evaluation = _require(data, "evaluation", errors)
    if isinstance(evaluation, dict):
        _require(evaluation, "suite", errors, "evaluation")
        score = _require(evaluation, "minimum_score", errors, "evaluation")
        if score is not None and (not isinstance(score, (int, float)) or not 0 <= float(score) <= 1):
            errors.append("evaluation.minimum_score must be a number between 0 and 1")
        _check_date(_require(evaluation, "last_passed", errors, "evaluation"), "evaluation.last_passed", errors)
    elif evaluation is not None:
        errors.append("evaluation must be a mapping")

    rollback = _require(data, "rollback", errors)
    if isinstance(rollback, dict):
        for key in ("previous_release", "kill_switch_owner", "disable_steps"):
            _require(rollback, key, errors, "rollback")
    elif rollback is not None:
        errors.append("rollback must be a mapping")
    return errors


def check_secrets(data: Any) -> list[str]:
    """No value anywhere in the file may look like a credential."""
    errors = []
    for path, value in iter_strings(data):
        for label, match in find_secret_like(value):
            errors.append(f"{path} looks like a secret ({label}): {mask(match)}")
    return errors


# --- Public API -----------------------------------------------------------------------------


def detect_kind(data: Any) -> str | None:
    if not isinstance(data, dict):
        return None
    if "deployment_id" in data:
        return KIND_MANIFEST
    if "client_id" in data:
        return KIND_CLIENT
    if "canonical_pages" in data:
        return KIND_BUSINESS
    return None


def validate_data(data: Any, kind: str) -> tuple[list[str], list[str]]:
    """Run the schema (if present) and the structural checks. Returns (errors, notes)."""
    errors: list[str] = []
    notes: list[str] = []
    schema_name = SCHEMA_FILES[kind]
    schema = load_schema(schema_name)
    if schema is None:
        notes.append(f"schemas/json/{schema_name} not present; structural checks only")
    else:
        notes.append(f"validated against schemas/json/{schema_name}")
        errors += schema_errors(data, schema, label=f"schema {schema_name}")

    if not isinstance(data, dict):
        errors.append("the file must contain a YAML mapping at the top level")
        return errors, notes

    if kind == KIND_BUSINESS:
        errors += structural_business(data)
    elif kind == KIND_CLIENT:
        errors += structural_client(data)
    else:
        errors += structural_manifest(data)
    errors += check_secrets(data)
    return errors, notes


def validate_file(path: Path) -> tuple[str | None, list[str], list[str]]:
    """Load, detect and validate one file. Returns (kind, errors, notes)."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except FileNotFoundError:
        return None, [f"file not found: {path}"], []
    except yaml.YAMLError as exc:
        return None, [f"not valid YAML: {exc}"], []
    kind = detect_kind(data)
    if kind is None:
        return None, ["cannot tell what this file is: expected canonical_pages (business), client_id (client) or deployment_id (manifest)"], []
    errors, notes = validate_data(data, kind)
    return kind, errors, notes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", metavar="PATH", help="contract or manifest YAML files")
    parser.add_argument("-q", "--quiet", action="store_true", help="print only problems")
    args = parser.parse_args(argv)

    failed = 0
    for raw in args.paths:
        path = Path(raw)
        kind, errors, notes = validate_file(path)
        label = f"{path} ({kind})" if kind else str(path)
        if errors:
            failed += 1
            print(f"FAIL {label}")
            for error in errors:
                print(f"  - {error}")
        elif not args.quiet:
            print(f"OK   {label}")
        if not args.quiet:
            for note in notes:
                print(f"     note: {note}")
    if failed:
        print(f"{failed} of {len(args.paths)} file(s) failed validation")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
