import os

# To verify the address, check: https://solscan.io/token/So11111111111111111111111111111111111111112
TOKEN_MINT_INFO = {
    "USDC": {
        "Address": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "Decimals": 6
    },
    "USDT": {
        "Address": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
        "Decimals": 6
    },
    "SOL": {
        "Address": "So11111111111111111111111111111111111111112",
        "Decimals": 9
    },
    "JitoSOL": {
        "Address": "J1toso1uCk3RLmjorhTtrVwY9HJ7X8V9yYac6Y7kGCPn",
        "Decimals": 9
    },
}

USER_PUBLIC_KEY = os.environ.get("TEST_USER_PUBLIC_KEY")
USER_PRIVATE_KEY = os.environ.get("TEST_SOLANA_USER_PRIVATE_KEY")

TRADING_TOKENS = ["SOL", "USDC", "USDT", "JitoSOL"]

RPC_URL = "https://api.mainnet-beta.solana.com"

TRANSACTION_TIMEOUT_SECONDS = 5

# Judge if there is key in the environment
if not USER_PUBLIC_KEY or not USER_PRIVATE_KEY:
    raise ValueError("Please set the environment variables for USER_PUBLIC_KEY and USER_PRIVATE_KEY")


if __name__ == '__main__':
    print(TOKEN_MINT_INFO)
    print(USER_PUBLIC_KEY)
    print(USER_PRIVATE_KEY)
