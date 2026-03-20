def detect_regime(momentum, volatility):
    if volatility > 70:
        return "CHAOTIC"
    if abs(momentum) > 40:
        return "TREND"
    return "RANGE"


def decide_trade(p0, p1, momentum, volatility, threshold):
    regime = detect_regime(momentum, volatility)

    if regime == "CHAOTIC":
        return "SKIP", regime

    if regime == "RANGE" and abs(p1 - p0) < threshold:
        return "RANGE_TRADE", regime

    if regime == "TREND":
        if momentum > 0:
            return "UP", regime
        else:
            return "DOWN", regime

    return "SKIP", regime
