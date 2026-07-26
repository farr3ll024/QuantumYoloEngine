from __future__ import annotations

import datetime as dt

import pytest

from quantum_yolo_engine.cli import compute_replay_sleep


def _build_parser():
    # re-import lazily to build a parser identical to main()'s, without
    # running main() itself (which starts a live trading loop)
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--replay", dest="replay", action=argparse.BooleanOptionalAction, default=True)
    return parser


def test_replay_defaults_to_enabled():
    args = _build_parser().parse_args([])
    assert args.replay is True


def test_no_replay_flag_disables_replay():
    args = _build_parser().parse_args(["--no-replay"])
    assert args.replay is False


def test_explicit_replay_flag_enables_replay():
    args = _build_parser().parse_args(["--replay"])
    assert args.replay is True


def test_compute_replay_sleep_scales_by_speed():
    t0 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    t1 = t0 + dt.timedelta(seconds=3600)
    assert compute_replay_sleep(t0, t1, speed=3600.0) == pytest.approx(1.0)
    assert compute_replay_sleep(t0, t1, speed=1.0) == pytest.approx(3600.0)


def test_compute_replay_sleep_is_zero_for_first_tick():
    t1 = dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)
    assert compute_replay_sleep(None, t1, speed=1.0) == 0.0


def test_compute_replay_sleep_never_negative_for_out_of_order_ticks():
    t0 = dt.datetime(2026, 1, 1, 0, 0, 10, tzinfo=dt.timezone.utc)
    t1 = dt.datetime(2026, 1, 1, 0, 0, 0, tzinfo=dt.timezone.utc)
    assert compute_replay_sleep(t0, t1, speed=1.0) == 0.0
