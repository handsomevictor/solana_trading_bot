# Solana On-Chain Trading Bot

This project is developed by @handsomevictor, a Chinese boy living in Paris.

This project aims to provide a better tool for people to trade on Web3 most famous exchanges like https://jup.ag/ etc.

JUP is mainly for swapping tokens, and I will only use it (instead of using limit orders) to trade.

This project belongs to @handsomevictor only, all the open-source strategies are without any warranty, and the author
is not responsible for any loss caused by using this project.

Currently, this project only supports trading on JUP using Solana Wallet.

When using the project, remember to create a wallet and transfer some SOL or other tokens to it, and put the public
and private key to the environment variables, because the project will use them to sign the transactions:

```angular2html
TEST_USER_PUBLIC_KEY = os.environ.get("TEST_USER_PUBLIC_KEY")
TEST_USER_PRIVATE_KEY = os.environ.get("TEST_SOLANA_USER_PRIVATE_KEY")
```

This project is using the documentation provided by [Jup](https://station.jup.ag/docs/apis/swap-api)
and [solana-py](https://michaelhly.com/solana-py/)

This project uses real time data from [Kaiko](https://www.kaiko.com/) and Binance API, but for building trading
strategies, only Kaiko data was used. If you want to have a look at how Kaiko data can help you, contact me. Remember
it's not free.

Feb. 13, 2024
