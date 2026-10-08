#!/usr/bin/env python3
"""check_freshness: is the mirror fresh enough to use?

    python scripts/check_freshness.py export/meta.json --contract templates/contracts/context-contract.yaml

Reads the two clocks from export/meta.json and the threshold from the contract's
freshness.stale_after_days (or --stale-after-days). Prints the age of both clocks:

    last_synced_at  the heartbeat: when the sync last ran successfully
    generated_at    when the exported content last changed (informational; old
                    content is fine, an old heartbeat is not)

Status is STALE when last_synced_at is older than the threshold.

Exit codes: 0 OK, 2 STALE, 1 the files could not be read.

Alerting: with --webhook-env NAME, when the status is STALE and the environment
variable NAME holds a URL, a small JSON payload is POSTed to it:
    {"status": "STALE", "last_synced_at": "...", "age_days": 9.3, "threshold_days": 7}
The URL itself is never printed. Any incoming-webhook endpoint that accepts JSON
works; map the fields in the receiving automation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from common import parse_iso_z, utc_now  # noqa: E402

DEFAULT_STALE_AFTER_DAYS = 7
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_STALE = 2


def age_days(timestamp: str, now: dt.datetime) -> float:
    """Days between an ISO timestamp and now, rounded to one decimal."""
    delta = now - parse_iso_z(timestamp)
    return round(delta.total_seconds() / 86400, 1)


def threshold_from_contract(path: Path) -> int | None:
    """freshness.stale_after_days from a contract, or None when it is not there."""
    with open(path, "r", encoding="utf-8") as handle:
        contract = yaml.safe_load(handle) or {}
    freshness = contract.get("freshness") or {}
    value = freshness.get("stale_after_days")
    return int(value) if isinstance(value, int) else None


def evaluate(meta: dict[str, Any], threshold_days: int, now: dt.datetime) -> dict[str, Any]:
    """Return a report dict: status, ages, threshold."""
    synced_age = age_days(meta["last_synced_at"], now)
    generated_age = age_days(meta["generated_at"], now)
    stale = synced_age > threshold_days
    return {
        "status": "STALE" if stale else "OK",
        "last_synced_at": meta["last_synced_at"],
        "generated_at": meta["generated_at"],
        "age_days": synced_age,
        "generated_age_days": generated_age,
        "threshold_days": threshold_days,
        "validation": meta.get("validation", "unknown"),
        "pages_missing": list(meta.get("pages_missing", [])),
    }


def post_alert(url: str, report: dict[str, Any]) -> str:
    """POST the small payload; return a one-line outcome without the URL."""
    import requests  # imported here so the check itself works without network libs

    payload = {
        "status": report["status"],
        "last_synced_at": report["last_synced_at"],
        "age_days": report["age_days"],
        "threshold_days": report["threshold_days"],
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
    except requests.RequestException as exc:
        return f"alert NOT delivered ({exc.__class__.__name__})"
    return f"alert posted (HTTP {response.status_code})"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("meta", help="path to export/meta.json")
    parser.add_argument("--contract", help="contract whose freshness.stale_after_days sets the threshold")
    parser.add_argument("--stale-after-days", type=int, help=f"override the threshold (default from the contract, else {DEFAULT_STALE_AFTER_DAYS})")
    parser.add_argument("--webhook-env", metavar="NAME", help="environment variable holding a webhook URL to POST to when STALE")
    parser.add_argument("--now", help="ISO 8601 timestamp to treat as the current time (tests)")
    args = parser.parse_args(argv)

    now = parse_iso_z(args.now) if args.now else utc_now()

    try:
        with open(args.meta, "r", encoding="utf-8") as handle:
            meta = json.load(handle)
        for key in ("last_synced_at", "generated_at"):
            parse_iso_z(str(meta[key]))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: cannot read the two clocks from {args.meta}: {exc.__class__.__name__}: {exc}", file=sys.stderr)
        return EXIT_ERROR

    threshold = args.stale_after_days
    if threshold is None and args.contract:
        try:
            threshold = threshold_from_contract(Path(args.contract))
        except (OSError, yaml.YAMLError) as exc:
            print(f"ERROR: cannot read {args.contract}: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return EXIT_ERROR
        if threshold is None:
            print(f"note: {args.contract} has no freshness.stale_after_days; using {DEFAULT_STALE_AFTER_DAYS}")
    if threshold is None:
        threshold = DEFAULT_STALE_AFTER_DAYS

    report = evaluate(meta, threshold, now)
    print(f"{report['status']}: mirror {args.meta}")
    print(f"  last_synced_at  {report['last_synced_at']}  ({report['age_days']} days old; stale after {threshold})")
    print(f"  generated_at    {report['generated_at']}  ({report['generated_age_days']} days since content changed)")
    print(f"  validation      {report['validation']}; pages_missing: {', '.join(report['pages_missing']) or 'none'}")

    if report["status"] == "STALE" and args.webhook_env:
        url = os.environ.get(args.webhook_env, "").strip()
        if url:
            print(f"  {post_alert(url, report)}")
        else:
            print(f"  no alert sent: environment variable {args.webhook_env} is not set")

    return EXIT_STALE if report["status"] == "STALE" else EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
