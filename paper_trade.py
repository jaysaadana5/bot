balance = 0


def execute_paper_trade(direction, entry_price, exit_price, config):
    global balance

    if direction == "UP" and exit_price > entry_price:
        profit = 8
    elif direction == "DOWN" and exit_price < entry_price:
        profit = 8
    else:
        profit = -config.STOP_LOSS

    balance += profit
    print(f"[PAPER] {direction} | entry={entry_price:.2f} exit={exit_price:.2f} | profit={profit:+} | balance={balance}")
    return profit, balance
