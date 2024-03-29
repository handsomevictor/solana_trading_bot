# Solana On-Chain Trading Bot (Very Immature Now)

This project is owned by [@handsomevictor](https://github.com/handsomevictor), a Chinese boy living in Paris.

## Introduction

The aim of this project is to provide a powerful tool for trading on Web3's most renowned exchanges, such as
[JUP](https://jup.ag/). JUP is primarily used for swapping tokens, and this tool focuses on utilizing it for trading
rather than traditional limit orders.

**Disclaimer**: This project, owned solely by [@handsomevictor](https://github.com/handsomevictor), offers open-source
strategies without warranty. The author holds no responsibility for any losses incurred while using this project.

## Usage

Before using the project, ensure you have created a wallet, transferred some SOL or other tokens to it, and placed the
public and private keys in the environment variables. The project utilizes these keys to sign transactions.

```python
USER_PUBLIC_KEY = os.environ.get("TEST_USER_PUBLIC_KEY")
USER_PRIVATE_KEY = os.environ.get("TEST_SOLANA_USER_PRIVATE_KEY")
```

## How to Run

Execute [transaction_executor.py](trading_bot%2Ftransaction_executor.py) in `./trading_bot`.

## Example Calculation

Assume your Solana wallet holds 1 SOL and 1 USDC, and you want to swap 0.1 SOL for USDC. Assuming a gas fee of 0.00007
SOL and a price of 1 SOL = 100 USDC, the result would be:

- SOL: 1 - 0.1 (swapping amount in SOL) - 0.00007 (gas fee) = 0.89993
- USDC: 1 + 0.1 (swapping amount in SOL) * 100 (exchange rate) = 2

## Email Notification

If you want to use it, register an account on Outlook (or any other email service) and enable the SMTP server,
and change the following parameters in `./tools/resources.py` or add them to your environment variables:

- SMTP_SERVER
- SMTP_PORT
- SENDER_EMAIL
- EMAIL_PASSWORD

## Reminders

- Never trade all your SOL. Always leave some for gas fees.
- No matter if a trade is made or not, as long as it's sent to the blockchain, a gas fee will be charged (range is
  usually 0.00006 - 0.00015 SOL but can be higher).

## Resourcess

This project utilizes the documentation provided by [Jup](https://station.jup.ag/docs/apis/swap-api)
and [solana-py](https://michaelhly.com/solana-py/), also took some pieces of code
from [0xTaoDev](https://github.com/0xTaoDev/jupiter-python-cli)

## Data Source

Real-time data is sourced from Kaiko and the Binance API. However, only Kaiko data is used for building trading
strategies. If you're interested in leveraging Kaiko data, feel free to reach out. Note that it's not free.

## Some Good Blockchain Analytics Websites

- [BirdEye](https://birdeye.so/)
- [Defillama](https://defillama.com/airdrops?chain=Solana)
- [ArkhamIntelligence](https://platform.arkhamintelligence.com/explorer/entity/grayscale)
- [Dune](https://dune.com/etaetaeta/pyth-stakers-over-time)

Date: Feb. 13, 2024