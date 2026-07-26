"""
Re-runs every scenario defined in tests/parity/generate_fixtures.py and
verifies the engine still reproduces the committed fixture exactly (modulo
the wall-clock bootstrap timestamp, see tests/parity/README.md). This is the
regression guard for the Python side of the parity contract; the
TypeScript engine has its own copy of this test in web/tests/unit/parity.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tests" / "parity"))

from generate_fixtures import FIXTURES_DIR, build_scenarios  # noqa: E402

FIXTURE_NAMES = sorted(p.stem for p in FIXTURES_DIR.glob("*.json"))


def _bootstrap_ts(fixture: dict) -> str:
    return fixture["expectedEvents"][0]["ts"]


def _normalize(fixture: dict) -> dict:
    bootstrap_ts = _bootstrap_ts(fixture)
    text = json.dumps(fixture, sort_keys=True)
    text = text.replace(bootstrap_ts, "BOOTSTRAP_TS")
    return json.loads(text)


@pytest.fixture(scope="module")
def fresh_scenarios() -> dict:
    return build_scenarios()


@pytest.mark.parametrize("name", FIXTURE_NAMES)
def test_fixture_matches_freshly_generated_run(name, fresh_scenarios):
    committed = json.loads((FIXTURES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    fresh = fresh_scenarios[name]

    assert _normalize(committed) == _normalize(fresh)


def test_all_fixture_names_covered_by_scenarios(fresh_scenarios):
    assert set(FIXTURE_NAMES) == set(fresh_scenarios.keys())
