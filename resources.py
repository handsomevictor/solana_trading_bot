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

TEST_USER_PUBLIC_KEY = os.environ.get("TEST_USER_PUBLIC_KEY")
TEST_USER_PRIVATE_KEY = os.environ.get("TEST_SOLANA_USER_PRIVATE_KEY")


if __name__ == '__main__':
    print(TOKEN_MINT_INFO)
    print(TEST_USER_PUBLIC_KEY)
    print(TEST_USER_PRIVATE_KEY)
