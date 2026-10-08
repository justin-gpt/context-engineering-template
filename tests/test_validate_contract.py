"""Tests for validate_contract.py: the three templates pass; broken copies fail with readable messages."""

from __future__ import annotations

from pathlib import Path

import yaml

import validate_contract
from conftest import run_cli

TEMPLATES = [
    "templates/contracts/context-contract.yaml",
    "templates/contracts/context-contract.notion.yaml",
    "templates/contracts/client-context-contract.yaml",
    "templates/contracts/project-manifest.yaml",
]


def load(repo_root: Path, name: str) -> dict:
    return yaml.safe_load((repo_root / name).read_text(encoding="utf-8"))


def test_template_contracts_pass(repo_root: Path):
    result = run_cli("validate_contract.py", *TEMPLATES, cwd=repo_root)
    assert result.returncode == 0, result.stdout + result.stderr
    for name in TEMPLATES:
        assert f"OK   {name}" in result.stdout


def test_kind_detection(repo_root: Path):
    assert validate_contract.detect_kind(load(repo_root, TEMPLATES[0])) == validate_contract.KIND_BUSINESS
    assert validate_contract.detect_kind(load(repo_root, TEMPLATES[2])) == validate_contract.KIND_CLIENT
    assert validate_contract.detect_kind(load(repo_root, TEMPLATES[3])) == validate_contract.KIND_MANIFEST
    assert validate_contract.detect_kind({"hello": 1}) is None


def test_unknown_status_fails(repo_root: Path, tmp_path: Path):
    text = (repo_root / TEMPLATES[0]).read_text(encoding="utf-8").replace("status: grounded", "status: verified", 1)
    broken = tmp_path / "contract.yaml"
    broken.write_text(text, encoding="utf-8")
    result = run_cli("validate_contract.py", str(broken))
    assert result.returncode == 1
    assert "FAIL" in result.stdout
    assert "verified" in result.stdout and "status" in result.stdout


def test_secret_looking_value_fails(repo_root: Path):
    contract = load(repo_root, TEMPLATES[0])
    contract["rules"]["gap_tracker"] = "secret_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    errors, _ = validate_contract.validate_data(contract, validate_contract.KIND_BUSINESS)
    assert any("looks like a secret" in error and "rules.gap_tracker" in error for error in errors), errors
    # The finding is masked: the full value never appears in the message.
    assert all("A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8" not in error for error in errors)

    manifest = load(repo_root, TEMPLATES[3])
    manifest["integrations"][0]["credential_reference"] = "AKIA" + "IOSFODNN7EXAMPLE"
    errors, _ = validate_contract.validate_data(manifest, validate_contract.KIND_MANIFEST)
    assert any("looks like a secret" in error for error in errors), errors


def test_reference_strings_are_not_secrets(repo_root: Path):
    # "secret-manager://..." is a reference and must pass; it is in the shipped manifest.
    manifest = load(repo_root, TEMPLATES[3])
    assert "secret-manager://" in manifest["integrations"][0]["credential_reference"]
    errors, _ = validate_contract.validate_data(manifest, validate_contract.KIND_MANIFEST)
    assert errors == []


def test_structural_checks_catch_common_mistakes(repo_root: Path):
    contract = load(repo_root, TEMPLATES[0])
    contract["next_review"] = contract["last_reviewed"]  # not after last_reviewed
    contract["canonical_pages"]["company_readme"]["owner"] = ""  # empty owner
    contract["canonical_pages"]["glossary"]["review"] = "yearly"  # bad enum
    contract["instruction_authority"]["control_pages"] = ["no_such_page"]
    contract["mirror_policy"] = "editable"
    errors, _ = validate_contract.validate_data(contract, validate_contract.KIND_BUSINESS)
    joined = "\n".join(errors)
    assert "next_review" in joined
    assert "canonical_pages.company_readme" in joined and "owner" in joined
    assert "canonical_pages.glossary.review" in joined
    assert "no_such_page" in joined
    assert "mirror_policy" in joined


def test_too_many_pages_fails(repo_root: Path):
    contract = load(repo_root, TEMPLATES[0])
    template_page = dict(contract["canonical_pages"]["company_readme"])
    for index in range(13):
        contract["canonical_pages"][f"extra_{index}"] = dict(template_page, id=f"extra_{index}.md")
    errors, _ = validate_contract.validate_data(contract, validate_contract.KIND_BUSINESS)
    assert any("1 to 12" in error or "maxProperties" in error or "12" in error for error in errors), errors


def test_client_contract_requires_no_cross_client_sources(repo_root: Path):
    contract = load(repo_root, TEMPLATES[2])
    contract["rules"]["cross_client_sources_allowed"] = True
    errors, _ = validate_contract.validate_data(contract, validate_contract.KIND_CLIENT)
    assert any("cross_client_sources_allowed" in error for error in errors), errors


def test_manifest_risk_class_enum(repo_root: Path):
    manifest = load(repo_root, TEMPLATES[3])
    manifest["risk_class"] = "yolo"
    manifest["evaluation"]["minimum_score"] = 1.5
    errors, _ = validate_contract.validate_data(manifest, validate_contract.KIND_MANIFEST)
    joined = "\n".join(errors)
    assert "risk_class" in joined and "minimum_score" in joined


def test_unreadable_file_reports_cleanly(tmp_path: Path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("just: [unclosed", encoding="utf-8")
    result = run_cli("validate_contract.py", str(bad), str(tmp_path / "missing.yaml"))
    assert result.returncode == 1
    assert "not valid YAML" in result.stdout
    assert "file not found" in result.stdout
