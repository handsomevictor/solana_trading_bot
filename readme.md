# Solana On-Chain Trading Bot

This project is developed by [@handsomevictor](https://github.com/handsomevictor), a Chinese boy living in Paris.

This project aims to provide a better tool for people to trade on Web3 most famous exchanges like
[JUP](https://jup.ag/) etc.

JUP is mainly for swapping tokens, and I will only use it (instead of using limit orders) to trade.

This project belongs to [@handsomevictor](https://github.com/handsomevictor) only,
all the open-source strategies are without any warranty, and the author
is not responsible for any loss caused by using this project.

Currently, this project only supports trading on JUP using Solana Wallet.

When using the project, remember to create a wallet and transfer some SOL or other tokens to it, and put the public
and private key to the environment variables, because the project will use them to sign the transactions:

```angular2html
USER_PUBLIC_KEY = os.environ.get("TEST_USER_PUBLIC_KEY")
USER_PRIVATE_KEY = os.environ.get("TEST_SOLANA_USER_PRIVATE_KEY")
```

## An Example of Calculate the Result

Assume in your Solana wallet, you have 1 SOL and 1USDC, and you want to swap 0.1 SOL to USDC, assume gas fee is
0.00007 SOL, and the price is 1 SOL = 100 USDC, then after swapping, the result would be:

SOL: 1 - 0.1 (swapping amount in SOL) - 0.00007 (gas fee) = 0.89993

USDC: 1 + 0.1 (swapping amount in SOL) * 100 (exchange rate) = 2

This project is using the documentation provided by [Jup](https://station.jup.ag/docs/apis/swap-api)
and [solana-py](https://michaelhly.com/solana-py/)

## Project Data Source

This project uses real time data from [Kaiko](https://www.kaiko.com/) and Binance API, but for building trading
strategies, only Kaiko data was used. If you want to have a look at how Kaiko data can help you, contact me. Remember
it's not free.

Feb. 13, 2024
