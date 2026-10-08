"""Shared fixtures: a throwaway copy of templates/ and a helper that runs the CLIs."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"

# Let the tests import the scripts as plain modules (import canon_sync, ...),
# exactly the way the scripts import each other.
for entry in (str(REPO_ROOT), str(SCRIPTS_DIR)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """A private copy of templates/ so a test can delete or edit pages freely.

    The sample contract uses paths relative to the repo root (templates/canon,
    templates/databases/canon-gaps.csv); running the CLI with cwd=workspace makes
    them resolve against the copy.
    """
    shutil.copytree(REPO_ROOT / "templates", tmp_path / "templates")
    return tmp_path


def run_cli(script: str, *args: str, cwd: Path | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run scripts/<script> with the current interpreter and capture its output."""
    command = [sys.executable, str(SCRIPTS_DIR / script), *args]
    return subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True)


@pytest.fixture
def run_sync(workspace: Path):
    """run_sync(*extra_args) runs canon_sync.py against the workspace copy."""

    def _run(*extra: str, out: str = "export") -> subprocess.CompletedProcess:
        return run_cli(
            "canon_sync.py",
            "--contract",
            "templates/contracts/context-contract.yaml",
            "--out",
            out,
            *extra,
            cwd=workspace,
        )

    return _run
