import json
import base58
import base64
import time
import re
import httpx
import asyncio
from multiprocessing import Process
import random
import pandas as pd

from datetime import datetime

from InquirerPy import inquirer

from tabulate import tabulate
import pandas as pd

from yaspin import yaspin

from solders import message
from solders.keypair import Keypair
from solders.pubkey import Pubkey
from solders.transaction import VersionedTransaction
from solders.signature import Signature
from solders.system_program import transfer, TransferParams

from solana.rpc.async_api import AsyncClient
from solana.rpc.api import Client
from solana.rpc.commitment import Processed
from solana.rpc.types import TxOpts
from solana.transaction import Transaction

from spl.token.instructions import get_associated_token_address

from jupiter_python_sdk.jupiter import Jupiter, Jupiter_DCA

from resources import TEST_USER_PUBLIC_KEY, TEST_USER_PRIVATE_KEY, TOKEN_MINT_INFO, TRADING_TOKENS, RPC_URL
from exceptions import PublicKeyError, TokenNotFoundInResources
import color_functions as c

USER_PRIVATE_KEY = TEST_USER_PRIVATE_KEY
USER_PUBLIC_KEY = TEST_USER_PUBLIC_KEY


# noinspection PyShadowingNames
class Wallet:

    def __init__(self, rpc_url: str,
                 private_key: str,
                 async_client: bool = True):
        self.wallet = Keypair.from_bytes(base58.b58decode(private_key))
        if async_client:
            self.client = AsyncClient(endpoint=rpc_url)
        else:
            self.client = Client(endpoint=rpc_url)
        self.transaction_hash = None

    def get_token_balance(self, token_mint_account: Pubkey) -> dict:
        """
        This function returns the balance of a token mint account.
        If the token mint account is the same as the wallet, it will return the SOL balance (since it's SOL chain)
        If the token mint account is different, it will return the mint token balance that the wallet has.
        """
        if token_mint_account == self.wallet.pubkey().__str__():
            get_token_balance = self.client.get_balance(pubkey=self.wallet.pubkey())
            return {
                'decimals': TOKEN_MINT_INFO["SOL"]["Decimals"],
                'balance': {
                    'int': get_token_balance.value,
                    'float': float(get_token_balance.value / 10 ** 9)
                }
            }
        else:
            get_token_balance = self.client.get_token_account_balance(pubkey=token_mint_account)
            try:
                token_balance = {
                    'decimals': int(get_token_balance.value.decimals),
                    'balance': {
                        'int': get_token_balance.value.amount,
                        'float': float(get_token_balance.value.amount) / 10 ** int(get_token_balance.value.decimals)
                    }
                }
            except AttributeError:
                token_balance = {'decimals': -1, 'balance': {'int': 0, 'float': 0}}
            return token_balance
            # later will add operations on multiple wallets

    def get_token_mint_account(self, token_mint: str) -> Pubkey:
        token_mint_account = get_associated_token_address(owner=self.wallet.pubkey(),
                                                          mint=Pubkey.from_string(token_mint))
        return token_mint_account

    def get_token_mint_account_no_async(self, token_mint: str) -> Pubkey:
        token_mint_account = get_associated_token_address(owner=self.wallet.pubkey(),
                                                          mint=Pubkey.from_string(token_mint))
        return token_mint_account

    def sign_send_transaction(self, transaction_data: str,
                              signatures_list: list = None,
                              print_link: bool = False):
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

        if print_link is True:
            print(f"{c.GREEN}Transaction sent: https://explorer.solana.com/tx/{transaction_hash}{c.RESET}")

    def get_status_transaction(self, transaction_hash: str):
        print("Checking transaction status...This might take 20 seconds.")
        get_transaction_details = self.client.confirm_transaction(tx_sig=Signature.from_string(transaction_hash),
                                                                  sleep_seconds=1)
        transaction_status = get_transaction_details.value[0].err

        if transaction_status is None:
            print(f"{c.GREEN} Transaction SUCCESS! transaction_hash is {transaction_hash}{c.RESET}")
        else:
            print(f"{c.RED}! Transaction FAILED!{c.RESET}")


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
                token_balance = self.wallet.get_token_balance(token_mint_account=USER_PUBLIC_KEY)
                balances_df = pd.concat([balances_df, pd.DataFrame({"Token": token,
                                                                    "Balance": token_balance['balance']['float'],
                                                                    "Decimals": TOKEN_MINT_INFO[token]["Decimals"],
                                                                    "int": token_balance['balance']['int'],
                                                                    "Amount": token_balance['balance']['float']},
                                                                   index=[0])])
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
        print(tabulate(balances_df, headers='keys', tablefmt='pretty'))
        return balances_df

    def trade_on_jup(self, input_asset: str,
                     output_asset: str,
                     output_asset_amount: int,
                     output_asset_slippage_list: list,
                     print_jup_link: bool = True):

        if input_asset not in TOKEN_MINT_INFO.keys() or output_asset not in TOKEN_MINT_INFO.keys():
            raise TokenNotFoundInResources("Input or output asset not found in TOKEN_MINT_INFO")

        quote_url = (f'https://quote-api.jup.ag/v6/quote'
                     f'?inputMint={TOKEN_MINT_INFO[input_asset]["Address"]}'
                     f'&outputMint={TOKEN_MINT_INFO[output_asset]["Address"]}'
                     f'&amount={output_asset_amount}'
                     f'&slippageBps={output_asset_slippage_list[1]}')
        if print_jup_link:
            print(f"{c.GREEN}Quote URL: {quote_url}{c.RESET}")

        quote_response = httpx.get(url=quote_url).json()
        swap_data = {
            "quoteResponse": quote_response,
            "userPublicKey": USER_PUBLIC_KEY,
            "wrapUnwrapSOL": True
        }

        get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data).json()
        swap_data = get_swap_data['swapTransaction']

        self.wallet.sign_send_transaction(transaction_data=swap_data, print_link=True)
        print(
            f'Transaction sent to swap {input_asset} to {output_asset} with amount {output_asset_amount} and slippage '
            f'{output_asset_slippage_list[1]}, checking transaction status...')

        self.wallet.get_status_transaction(transaction_hash=self.wallet.transaction_hash)


if __name__ == "__main__":
    executor = TradeOnJup(rpc_url=RPC_URL,
                          private_key=USER_PRIVATE_KEY,
                          async_client=False)
    # print balance
    balances_df = executor.get_token_balance_df()

    # trade
    input_asset = "USDC"
    output_asset = "SOL"

    trade_pamras = {
        "input_asset": input_asset,
        "output_asset": output_asset,
        "output_asset_amount": int(0.01 * (10 ** TOKEN_MINT_INFO[input_asset]["Decimals"])),
        "output_asset_slippage_list": [10, 22, 35, 50],
        "print_jup_link": True
    }
    execute_trade = executor.trade_on_jup(**trade_pamras)
    # 变化应该是：
    # USDC: 0.3555 - 0.01 = 0.3455
    # SOL: 0.01311 + 0.00009 - 0.00007 = 0.01313

    # check balance again
    executor.get_token_balance_df()

    # USDC有6个decimal，所以1USDC=1000000，SOL有9个，所以1SOL有1000000000，我要交易0.005SOL，应该写5000000
    # quote_url = ('https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112'
    #              '&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=2000000&slippageBps=10')
    # amount = 0.002SOL，那么交易后Solana应该剩0.01278-gas(0.00011)=个，USDC应该0.24+0.2~左右价值

    """
    执行完这个之后，直接在jup上成交了，基本上全都转化为USDC了，要小心啊，不然可能没有sol支付gas了
    """
