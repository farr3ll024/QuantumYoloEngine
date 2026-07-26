from __future__ import annotations

import pytest

from quantum_yolo_engine.feeds import CsvMarketFeed, DemoMarketFeed


def test_demo_feed_is_deterministic_for_fixed_seed():
    feed_a = DemoMarketFeed(seed=7)
    feed_b = DemoMarketFeed(seed=7)

    seq_a = [feed_a.next_prices() for _ in range(30)]
    seq_b = [feed_b.next_prices() for _ in range(30)]

    assert seq_a == seq_b


def test_demo_feed_differs_across_seeds():
    feed_a = DemoMarketFeed(seed=1)
    feed_b = DemoMarketFeed(seed=2)

    seq_a = [feed_a.next_prices() for _ in range(10)]
    seq_b = [feed_b.next_prices() for _ in range(10)]

    assert seq_a != seq_b


def test_demo_feed_prices_stay_within_bounds():
    feed = DemoMarketFeed(seed=7)
    for _ in range(200):
        prices = feed.next_prices()
        assert 45000.0 <= prices["BTC-USD"] <= 95000.0
        assert 1200.0 <= prices["ETH-USD"] <= 4500.0


def test_csv_feed_forward_fills_missing_assets(tmp_path):
    p = tmp_path / "history.csv"
    p.write_text(
        "ts,product_id,price\n"
        "2026-01-01T00:00:00Z,BTC-USD,100.0\n"
        "2026-01-01T00:00:00Z,ETH-USD,10.0\n"
        "2026-01-01T00:01:00Z,BTC-USD,101.0\n"  # ETH missing this tick; must forward-fill
        "2026-01-01T00:02:00Z,ETH-USD,11.0\n",
        encoding="utf-8",
    )
    ticks = list(CsvMarketFeed(str(p)))

    assert len(ticks) == 3
    _, prices0 = ticks[0]
    assert prices0 == {"BTC-USD": 100.0, "ETH-USD": 10.0}

    _, prices1 = ticks[1]
    assert prices1 == {"BTC-USD": 101.0, "ETH-USD": 10.0}  # ETH forward-filled

    _, prices2 = ticks[2]
    assert prices2 == {"BTC-USD": 101.0, "ETH-USD": 11.0}  # BTC forward-filled


def test_csv_feed_never_invents_value_before_first_observation(tmp_path):
    p = tmp_path / "history.csv"
    p.write_text(
        "ts,product_id,price\n"
        "2026-01-01T00:00:00Z,BTC-USD,100.0\n"
        "2026-01-01T00:01:00Z,ETH-USD,10.0\n",
        encoding="utf-8",
    )
    ticks = list(CsvMarketFeed(str(p)))
    _, prices0 = ticks[0]
    assert "ETH-USD" not in prices0  # no ETH observation yet -> not fabricated


def test_csv_feed_rejects_empty_file(tmp_path):
    p = tmp_path / "empty.csv"
    p.write_text("ts,product_id,price\n", encoding="utf-8")
    with pytest.raises(ValueError, match="empty"):
        CsvMarketFeed(str(p))


def test_csv_feed_rejects_missing_columns(tmp_path):
    p = tmp_path / "bad.csv"
    p.write_text("ts,price\n2026-01-01T00:00:00Z,100.0\n", encoding="utf-8")
    with pytest.raises(ValueError, match="must include columns"):
        CsvMarketFeed(str(p))
