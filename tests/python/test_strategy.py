from __future__ import annotations

from quantum_yolo_engine.strategy import load_strategy_config


def test_loads_default_strategy_yaml():
    bankroll, strategies = load_strategy_config("strategy.yaml")

    assert bankroll == 1000.0
    assert set(strategies.keys()) == {"BTC-USD", "ETH-USD"}

    btc = strategies["BTC-USD"]
    assert btc.enabled is True
    assert btc.allocation_usd == 600.0
    assert btc.stop_price == 62000.0
    assert btc.take_profit.tp1_price == 91000.0
    assert btc.take_profit.tp2_price == 96000.0
    assert len(btc.entries) == 6
    assert btc.entries[0].id == "btc_e1"


def test_loads_yaml_with_minimal_asset(tmp_path):
    p = tmp_path / "strategy.yaml"
    p.write_text(
        """
bankroll_usd: 500.0
assets:
  BTC-USD:
    allocation_usd: 500.0
    stop_price: 50.0
    take_profit:
      tp1_price: 110.0
      tp1_fraction: 0.5
      tp2_price: 130.0
      tp2_fraction: 0.5
    entries:
      - id: e1
        price: 100.0
        quote_size_usd: 100.0
""",
        encoding="utf-8",
    )
    bankroll, strategies = load_strategy_config(str(p))
    assert bankroll == 500.0
    # `enabled` defaults to True when omitted
    assert strategies["BTC-USD"].enabled is True
