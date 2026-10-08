"""Tests for check_freshness.py: fresh vs stale meta, threshold sources, webhook payload."""

from __future__ import annotations

import json
from pathlib import Path

import requests

import check_freshness
from conftest import run_cli

CONTRACT = "templates/contracts/context-contract.yaml"  # stale_after_days: 7


def write_meta(path: Path, generated_at: str, last_synced_at: str) -> Path:
    meta = {
        "generated_at": generated_at,
        "last_synced_at": last_synced_at,
        "contract_version": 2,
        "source_of_truth": "markdown",
        "pages_synced": ["company_readme"],
        "pages_missing": [],
        "bundle_bytes": 1234,
        "validation": "passed",
        "warnings": [],
    }
    path.write_text(json.dumps(meta), encoding="utf-8")
    return path


def test_fresh_meta_is_ok(repo_root: Path, tmp_path: Path):
    meta = write_meta(tmp_path / "meta.json", "2026-10-01T02:00:00Z", "2026-10-08T02:00:00Z")
    result = run_cli("check_freshness.py", str(meta), "--contract", CONTRACT, "--now", "2026-10-09T08:00:00Z", cwd=repo_root)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.startswith("OK:")
    assert "1.2 days old; stale after 7" in result.stdout
    assert "8.2 days since content changed" in result.stdout


def test_stale_meta_exits_2(repo_root: Path, tmp_path: Path):
    meta = write_meta(tmp_path / "meta.json", "2026-10-01T02:00:00Z", "2026-10-01T02:00:00Z")
    result = run_cli("check_freshness.py", str(meta), "--contract", CONTRACT, "--now", "2026-10-09T08:00:00Z", cwd=repo_root)
    assert result.returncode == 2
    assert result.stdout.startswith("STALE:")
    assert "8.2 days old; stale after 7" in result.stdout


def test_threshold_override_and_default(tmp_path: Path):
    meta = write_meta(tmp_path / "meta.json", "2026-10-01T02:00:00Z", "2026-10-01T02:00:00Z")
    # 8.2 days old: stale at the default 7, fine with --stale-after-days 10.
    assert run_cli("check_freshness.py", str(meta), "--now", "2026-10-09T08:00:00Z").returncode == 2
    assert run_cli("check_freshness.py", str(meta), "--now", "2026-10-09T08:00:00Z", "--stale-after-days", "10").returncode == 0


def test_webhook_receives_small_payload(tmp_path: Path, monkeypatch, capsys):
    meta = write_meta(tmp_path / "meta.json", "2026-10-01T02:00:00Z", "2026-10-01T02:00:00Z")
    captured: dict = {}

    class FakeResponse:
        status_code = 204

    def fake_post(url, json=None, timeout=None):
        captured["url"] = url
        captured["payload"] = json
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example.com/services/T000/B000/XXXX")

    code = check_freshness.main([str(meta), "--now", "2026-10-09T08:00:00Z", "--webhook-env", "ALERT_WEBHOOK_URL"])
    assert code == 2
    assert captured["url"] == "https://hooks.example.com/services/T000/B000/XXXX"
    assert captured["payload"] == {
        "status": "STALE",
        "last_synced_at": "2026-10-01T02:00:00Z",
        "age_days": 8.2,
        "threshold_days": 7,
    }
    out = capsys.readouterr().out
    assert "alert posted (HTTP 204)" in out
    assert "hooks.example.com" not in out, "the webhook URL is never printed"


def test_webhook_not_called_when_fresh(tmp_path: Path, monkeypatch):
    meta = write_meta(tmp_path / "meta.json", "2026-10-08T02:00:00Z", "2026-10-08T02:00:00Z")

    def must_not_post(*args, **kwargs):
        raise AssertionError("a fresh mirror must not trigger an alert")

    monkeypatch.setattr(requests, "post", must_not_post)
    monkeypatch.setenv("ALERT_WEBHOOK_URL", "https://hooks.example.com/x")
    assert check_freshness.main([str(meta), "--now", "2026-10-09T08:00:00Z", "--webhook-env", "ALERT_WEBHOOK_URL"]) == 0


def test_unreadable_meta_exits_1(tmp_path: Path):
    assert run_cli("check_freshness.py", str(tmp_path / "missing.json")).returncode == 1
    broken = tmp_path / "meta.json"
    broken.write_text('{"generated_at": "2026-10-08T02:00:00Z"}', encoding="utf-8")  # no last_synced_at
    assert run_cli("check_freshness.py", str(broken)).returncode == 1
