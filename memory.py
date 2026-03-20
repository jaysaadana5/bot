BAD_CONDITIONS = []


def store_bad_pattern(trade):
    BAD_CONDITIONS.append({
        "momentum": trade["momentum"],
        "volatility": trade["volatility"],
    })


def is_bad_condition(momentum, volatility):
    for bad in BAD_CONDITIONS:
        if abs(bad["momentum"] - momentum) < 10 and abs(bad["volatility"] - volatility) < 10:
            return True
    return False
