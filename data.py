import requests


def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return float(response.json()["price"])
