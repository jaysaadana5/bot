import json


def log_trade(trade):
    with open("trades.json", "a") as f:
        f.write(json.dumps(trade) + "\n")
