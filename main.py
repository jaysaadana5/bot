import time
from datetime import datetime

import config
from data import get_btc_price
from strategy import decide_trade
from risk import RiskManager
from paper_trade import execute_paper_trade
from execution import execute_real_trade
from auto_tune import AutoTuneManager, should_tune, adjust_threshold
from memory import is_bad_condition, store_bad_pattern
from logger import log_trade
from claude_ai import ask_claude

risk = RiskManager()
tuner = AutoTuneManager()
trade_history = []


def run():
    cycle = 0

    while True:
        cycle += 1
        tuner.next_cycle()

        print(f"\n[Cycle {cycle}] {datetime.utcnow().strftime('%H:%M:%S UTC')} | threshold={config.THRESHOLD}")

        try:
            p0 = get_btc_price()
        except Exception as e:
            print(f"Price fetch error: {e}")
            time.sleep(10)
            continue

        time.sleep(config.ENTRY_SECOND)

        try:
            p1 = get_btc_price()
        except Exception as e:
            print(f"Price fetch error: {e}")
            time.sleep(10)
            continue

        momentum = p1 - p0
        volatility = abs(momentum)

        decision, regime = decide_trade(p0, p1, momentum, volatility, config.THRESHOLD)
        print(f"  p0={p0:.2f} p1={p1:.2f} momentum={momentum:+.2f} volatility={volatility:.2f} regime={regime} decision={decision}")

        if decision == "SKIP":
            print("  Skipping — regime filter.")
            continue

        if is_bad_condition(momentum, volatility):
            print("  Skipping — known bad condition.")
            continue

        mode = "PAPER" if risk.in_cooldown() else "REAL"
        profit = 0

        if mode == "REAL":
            execute_real_trade(decision, config.POSITION_SIZE)
            # Fetch exit price after a short hold (simulated here)
            time.sleep(5)
            try:
                exit_price = get_btc_price()
            except Exception:
                exit_price = p1
            # Simulate profit for tracking (replace with real PnL from Polymarket)
            if (decision == "UP" and exit_price > p1) or (decision == "DOWN" and exit_price < p1):
                profit = 8
            else:
                profit = -config.STOP_LOSS
            print(f"  [REAL] profit={profit:+}")
        else:
            try:
                exit_price = get_btc_price()
            except Exception:
                exit_price = p1
            profit, balance = execute_paper_trade(decision, p1, exit_price, config)

        trade = {
            "cycle": cycle,
            "timestamp": datetime.utcnow().isoformat(),
            "mode": mode,
            "regime": regime,
            "decision": decision,
            "p0": p0,
            "p1": p1,
            "momentum": momentum,
            "volatility": volatility,
            "profit": profit,
        }

        trade_history.append(trade)
        log_trade(trade)
        risk.update(profit, config)

        if profit < -config.STOP_LOSS * 0.5:
            store_bad_pattern(trade)

        # Auto-tune during cooldown / paper phase
        if mode == "PAPER" and tuner.can_tune(config) and should_tune(trade_history):
            increase = profit >= 0
            adjust_threshold(config, increase=not increase)
            tuner.mark_tuned()
            print(f"  [AutoTune] threshold adjusted to {config.THRESHOLD}")

        # Ask Claude for commentary every 10 cycles
        if cycle % 10 == 0:
            try:
                summary = ask_claude(
                    f"BTC trading bot cycle {cycle}. "
                    f"Last regime: {regime}, decision: {decision}, profit: {profit:+}. "
                    f"Recent trades: {len(trade_history)}. "
                    "Give a one-sentence market assessment."
                )
                print(f"  [Claude] {summary}")
            except Exception as e:
                print(f"  [Claude] unavailable: {e}")

        # Small pause between cycles to avoid hammering the API
        time.sleep(5)


if __name__ == "__main__":
    print("BTC Adaptive Trading Bot starting...")
    print(f"Mode: REAL → PAPER on cooldown | threshold={config.THRESHOLD} | stop_loss={config.STOP_LOSS}")
    run()
