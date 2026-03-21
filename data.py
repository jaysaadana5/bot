from tradingview_ta import TA_Handler, Interval


_handler = TA_Handler(
    symbol="BTCUSDT",
    screener="crypto",
    exchange="BINANCE",
    interval=Interval.INTERVAL_1_MINUTE,
)


def get_btc_price():
    analysis = _handler.get_analysis()
    return float(analysis.indicators["close"])
