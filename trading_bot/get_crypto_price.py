"""
I plan to use multiple ways to get the price. The price is not only from Binance
"""

import httpx


def get_crypto_price(crypto: str) -> float:
    """Returns crypto price."""
    API_BINANCE = f"https://www.binance.com/api/v3/ticker/price?symbol={crypto}USDT"
    crypto_price =float(httpx.get(API_BINANCE).json()['price'])
    return crypto_price


if __name__ == '__main__':
    print(get_crypto_price('SOL'))
