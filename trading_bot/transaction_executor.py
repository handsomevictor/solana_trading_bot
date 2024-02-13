"""
All logging messages will be handled by the logger in ./trading_bot/logging_formatter.py
"""

import json
import base58
import base64
import httpx
import logging
import datetime
import pandas as pd
from tabulate import tabulate
from InquirerPy import inquirer

from solders import message
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from solders.system_program import transfer, TransferParams

from solana.rpc.api import Client
from solana.rpc.types import TxOpts
from solana.transaction import Transaction
from solana.rpc.commitment import Processed
from solana.rpc.async_api import AsyncClient

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA

from spl.token.instructions import get_associated_token_address

import trading_bot.color_functions as c
from trading_bot.decorators import func_timeout
from trading_bot.logging_formatter import logger
from trading_bot.exceptions_trade import PublicKeyError, TokenNotFoundInResources
from trading_bot.resources import (USER_PUBLIC_KEY, USER_PRIVATE_KEY, TOKEN_MINT_INFO, TRADING_TOKENS, RPC_URL,
                                   TRANSACTION_TIMEOUT_SECONDS)


# noinspection PyShadowingNames
class Wallet:

    def __init__(self, rpc_url: str,
                 private_key: str,
                 async_client: bool = True):
        if rpc_url and private_key:
            self.wallet = Keypair.from_bytes(base58.b58decode(private_key))
            if async_client:
                self.client = AsyncClient(endpoint=rpc_url)
            else:
                self.client = Client(endpoint=rpc_url)
        else:
            self.wallet = None
            self.client = None
        self.transaction_hash = None

    def get_token_balance(self, token_mint_account: Pubkey) -> dict:
        """
        This function returns the balance of a token mint account.
        If the token mint account is the same as the wallet, it will return the SOL balance (since it's SOL chain)
        If the token mint account is different, it will return the mint token balance that the wallet has.
        """
        if token_mint_account == self.wallet.pubkey().__str__():
            get_token_balance = self.client.get_balance(pubkey=self.wallet.pubkey())

            decimals = TOKEN_MINT_INFO["SOL"]["Decimals"]
            balance_int = get_token_balance.value
            balance_float = float(get_token_balance.value / 10 ** 9)

        else:
            get_token_balance = self.client.get_token_account_balance(pubkey=token_mint_account)
            try:
                decimals = int(get_token_balance.value.decimals)
                balance_int = get_token_balance.value.amount
                balance_float = float(get_token_balance.value.amount) / 10 ** int(get_token_balance.value.decimals)

            except AttributeError:
                decimals = -1
                balance_int = 0
                balance_float = 0

        token_balance = {'decimals': decimals, 'balance': {'int': balance_int, 'float': balance_float}}
        return token_balance

    def get_token_mint_account(self, token_mint: str) -> Pubkey:
        token_mint_account = get_associated_token_address(owner=self.wallet.pubkey(),
                                                          mint=Pubkey.from_string(token_mint))
        return token_mint_account

    @func_timeout(TRANSACTION_TIMEOUT_SECONDS)
    def sign_send_transaction(self, transaction_data: str,
                              signatures_list: list = None):
        """
        STARTS THE TRANSACTION HERE!
        """
        signatures = []

        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = self.wallet.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signatures.append(signature)
        if signatures_list:
            for signature in signatures_list:
                signatures.append(signature)
        signed_txn = VersionedTransaction.populate(raw_transaction.message, signatures)
        opts = TxOpts(skip_preflight=True, preflight_commitment=Processed)

        result = self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_hash = json.loads(result.to_json())['result']

        self.transaction_hash = transaction_hash
        logger.info(f"{c.GREEN}Transaction sent: https://explorer.solana.com/tx/{transaction_hash}{c.RESET}")

    def get_status_transaction(self, transaction_hash: str):
        logger.info(f"{c.GREEN}Checking transaction status...{c.GRAY} This might take 20 seconds.{c.RESET}")
        get_transaction_details = self.client.confirm_transaction(tx_sig=Signature.from_string(transaction_hash),
                                                                  sleep_seconds=1)
        transaction_status = get_transaction_details.value[0].err

        if transaction_status is None:
            logger.info(f"{c.GREEN} Transaction SUCCESS! {c.RESET}"
                        f"{c.GRAY} transaction_hash is {transaction_hash}{c.RESET}")
        else:
            logger.fatal(f"{c.RED} Transaction FAILED! {c.RESET}"
                         f"{c.GRAY} transaction_hash is {transaction_hash}{c.RESET}")
        return 200 if transaction_status is None else 400


# noinspection PyShadowingNames
class TradeOnJup(Wallet):
    def __init__(self, rpc_url: str,
                 private_key: str,
                 async_client: bool = True):
        super().__init__(rpc_url=rpc_url, private_key=private_key, async_client=async_client)
        self.wallet = Wallet(rpc_url=rpc_url, private_key=private_key, async_client=async_client)

    def get_token_balance_df(self):
        balances_df = pd.DataFrame(columns=["Token", "Balance", "Decimals", "Amount", "int"])

        for token in TRADING_TOKENS:
            if token == "SOL":
                token_mint_account = USER_PUBLIC_KEY
            else:
                token_mint_account = self.wallet.get_token_mint_account(token_mint=TOKEN_MINT_INFO[token]["Address"])

            token_balance = self.wallet.get_token_balance(token_mint_account=token_mint_account)
            balances_df = pd.concat([balances_df, pd.DataFrame({"Token": token,
                                                                "Balance": token_balance['balance']['float'],
                                                                "Decimals": TOKEN_MINT_INFO[token]["Decimals"],
                                                                "int": token_balance['balance']['int'],
                                                                "Amount": token_balance['balance']['float']},
                                                               index=[0])])

        balances_df = balances_df.reset_index(drop=True)

        logger.info(f"\n{c.YELLOW}Balances: \n{tabulate(balances_df, headers='keys', tablefmt='pretty')}{c.RESET}")
        return balances_df

    def trade_on_jup(self, input_asset: str,
                     output_asset: str,
                     input_asset_amount: int,
                     output_asset_slippage_list: list,
                     jup_post_request_timeout_seconds: float = 10) -> int:
        """
        STARTS THE TRADE ON JUPITER
        :return: status code either 200 (success) or 400 (failure)
        """
        if input_asset not in TOKEN_MINT_INFO.keys() or output_asset not in TOKEN_MINT_INFO.keys():
            raise TokenNotFoundInResources("Input or output asset not found in TOKEN_MINT_INFO")

        quote_url = (f'https://quote-api.jup.ag/v6/quote'
                     f'?inputMint={TOKEN_MINT_INFO[input_asset]["Address"]}'
                     f'&outputMint={TOKEN_MINT_INFO[output_asset]["Address"]}'
                     f'&amount={input_asset_amount}'
                     f'&slippageBps={output_asset_slippage_list[1]}')

        logger.debug(f"{c.GREEN}Quote URL: {quote_url}{c.RESET}")

        quote_response = httpx.get(url=quote_url).json()
        swap_data = {
            "quoteResponse": quote_response,
            "userPublicKey": USER_PUBLIC_KEY,
            "wrapUnwrapSOL": True
        }

        get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data,
                                   timeout=jup_post_request_timeout_seconds).json()
        swap_data = get_swap_data['swapTransaction']

        self.wallet.sign_send_transaction(transaction_data=swap_data)

        logger.info(f"{c.GRAY}Transaction sent to swap {input_asset} to {output_asset} with amount "
                    f"{input_asset_amount} and slippage {output_asset_slippage_list[1]}.{c.RESET}")

        return self.wallet.get_status_transaction(transaction_hash=self.wallet.transaction_hash)


if __name__ == "__main__":
    executor = TradeOnJup(rpc_url=RPC_URL,
                          private_key=USER_PRIVATE_KEY,
                          async_client=False)
    # print balance
    original_balances_df = executor.get_token_balance_df()

    # trade
    input_asset = "USDC"
    output_asset = "SOL"
    input_asset_amount = 0.01

    trade_pamras = {
        "input_asset": input_asset,
        "output_asset": output_asset,
        "input_asset_amount": int(input_asset_amount * (10 ** TOKEN_MINT_INFO[input_asset]["Decimals"])),
        "output_asset_slippage_list": [10, 22, 35, 50],
        "jup_post_request_timeout_seconds": 10,
    }
    execute_trade = executor.trade_on_jup(**trade_pamras)

    if execute_trade != 200:
        pass  # do something

    # check balance again
    current_balances_df = executor.get_token_balance_df()
