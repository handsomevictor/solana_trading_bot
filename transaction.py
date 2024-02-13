import json
import base58
import base64
import time
import re
import httpx
import asyncio
from multiprocessing import Process
import random

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


from resources import TEST_USER_PUBLIC_KEY, TEST_USER_PRIVATE_KEY, TOKEN_MINT_INFO
import color_functions as f



class Wallet():

    def __init__(self, rpc_url: str, private_key: str, async_client: bool = True):
        self.wallet = Keypair.from_bytes(base58.b58decode(private_key))
        if async_client:
            self.client = AsyncClient(endpoint=rpc_url)
        else:
            self.client = Client(endpoint=rpc_url)

    async def get_token_balance(self, token_mint_account: str) -> dict:

        if token_mint_account == self.wallet.pubkey().__str__():
            get_token_balance = await self.client.get_balance(pubkey=self.wallet.pubkey())
            token_balance = {
                'decimals': 9,
                'balance': {
                    'int': get_token_balance.value,
                    'float': float(get_token_balance.value / 10 ** 9)
                }
            }
        else:
            get_token_balance = await self.client.get_token_account_balance(pubkey=token_mint_account)
            try:
                token_balance = {
                    'decimals': int(get_token_balance.value.decimals),
                    'balance': {
                        'int': get_token_balance.value.amount,
                        'float': float(get_token_balance.value.amount) / 10 ** int(get_token_balance.value.decimals)
                    }
                }
            except AttributeError:
                token_balance = {'balance': {'int': 0, 'float': 0}}

        return token_balance

    def get_token_balance_no_async(self, token_mint_account: str) -> dict:

        if token_mint_account == self.wallet.pubkey().__str__():
            get_token_balance = self.client.get_balance(pubkey=self.wallet.pubkey())
            token_balance = {
                'decimals': 9,
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
                token_balance = {'balance': {'int': 0, 'float': 0}}

        return token_balance

    async def get_token_mint_account(self, token_mint: str) -> Pubkey:
        token_mint_account = get_associated_token_address(owner=self.wallet.pubkey(),
                                                          mint=Pubkey.from_string(token_mint))
        return token_mint_account

    def get_token_mint_account_no_async(self, token_mint: str) -> Pubkey:
        token_mint_account = get_associated_token_address(owner=self.wallet.pubkey(),
                                                          mint=Pubkey.from_string(token_mint))
        return token_mint_account

    async def sign_send_transaction(self, transaction_data: str, signatures_list: list = None, print_link: bool = True):
        signatures = []

        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = self.wallet.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signatures.append(signature)
        if signatures_list:
            for signature in signatures_list:
                signatures.append(signature)
        signed_txn = VersionedTransaction.populate(raw_transaction.message, signatures)
        opts = TxOpts(skip_preflight=True, preflight_commitment=Processed)

        # print(signatures, transaction_data)
        # input()

        result = await self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_hash = json.loads(result.to_json())['result']
        if print_link is True:
            print(f"{c.GREEN}Transaction sent: https://explorer.solana.com/tx/{transaction_hash}{c.RESET}")
            await inquirer.text(message="\nPress ENTER to continue").execute_async()
        # await self.get_status_transaction(transaction_hash=transaction_hash) # TBD

    def sign_send_transaction_no_async(self, transaction_data: str, signatures_list: list = None,
                                       print_link: bool = True):
        signatures = []

        raw_transaction = VersionedTransaction.from_bytes(base64.b64decode(transaction_data))
        signature = self.wallet.sign_message(message.to_bytes_versioned(raw_transaction.message))
        signatures.append(signature)
        if signatures_list:
            for signature in signatures_list:
                signatures.append(signature)
        signed_txn = VersionedTransaction.populate(raw_transaction.message, signatures)
        opts = TxOpts(skip_preflight=True, preflight_commitment=Processed)

        # print(signatures, transaction_data)
        # input()

        result = self.client.send_raw_transaction(txn=bytes(signed_txn), opts=opts)
        transaction_hash = json.loads(result.to_json())['result']
        if print_link is True:
            print(f"{GREEN}Transaction sent: https://explorer.solana.com/tx/{transaction_hash}{RESET}")

    async def get_status_transaction(self, transaction_hash: str):
        print("Checking transaction status...")
        get_transaction_details = await self.client.confirm_transaction(tx_sig=Signature.from_string(transaction_hash),
                                                                        sleep_seconds=1)
        transaction_status = get_transaction_details.value[0].err

        if transaction_status is None:
            print("Transaction SUCCESS!")
        else:
            print(f"{c.RED}! Transaction FAILED!{c.RESET}")

        await inquirer.text(message="\nPress ENTER to continue").execute_async()


if __name__ == "__main__":
    wallet = Wallet(rpc_url="https://api.mainnet-beta.solana.com",
                    private_key=TEST_USER_PRIVATE_KEY,
                    async_client=False)
    token_balance = wallet.get_token_balance_no_async(token_mint_account=TEST_USER_PUBLIC_KEY)
    print(token_balance)

    # token_mint_account = wallet.get_token_mint_account_no_async(token_mint='So11111111111111111111111111111111111111112')
    # print(token_mint_account)

    # USDC有6个decimal，所以1USDC=1000000，SOL有9个，所以1SOL有1000000000，我要交易0.005SOL，应该写5000000
    # quote_url = ('https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112'
    #              '&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=2000000&slippageBps=10')
    # amount = 0.002SOL，那么交易后Solana应该剩0.01278-gas(0.00011)=个，USDC应该0.24+0.2~左右价值

    output_asset_amount = 1 * (10 ** TOKEN_MINT_INFO["USDC"]["Decimals"])
    output_asset_slippage_list = [20, 50, 100]
    quote_url = (f'https://quote-api.jup.ag/v6/quote'
                 f'?inputMint={TOKEN_MINT_INFO["SOL"]["Address"]}'
                 f'&outputMint={TOKEN_MINT_INFO["USDC"]["Address"]}'
                 f'&amount={output_asset_amount}'
                 f'&slippageBps={output_asset_slippage_list[1]}')
    # 执行这条的话，USDC到Solana，支付0.1USDC，USDC剩余为0.37216，SOL为0.01267+0.00088-gas(0.00011)=0.01344

    quote_response = httpx.get(url=quote_url).json()
    swap_data = {
        "quoteResponse": quote_response,
        "userPublicKey": TEST_USER_PUBLIC_KEY,
        "wrapUnwrapSOL": True
    }
    # print(swap_data)
    get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data).json()
    print(get_swap_data)
    swap_data = get_swap_data['swapTransaction']

    wallet.sign_send_transaction_no_async(transaction_data=swap_data, print_link=True)

    """
    执行完这个之后，直接在jup上成交了，基本上全都转化为USDC了，要小心啊，不然可能没有sol支付gas了
    """
