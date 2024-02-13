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

from resources import TEST_USER_PUBLIC_KEY, TEST_USER_PRIVATE_KEY, TOKEN_MINT_INFO, TRADING_TOKENS
import color_functions as c


# make PublicKeyError
class PublicKeyError(Exception):
    pass


# noinspection PyShadowingNames
class Wallet():

    def __init__(self, rpc_url: str, private_key: str, async_client: bool = True):
        self.wallet = Keypair.from_bytes(base58.b58decode(private_key))
        if async_client:
            self.client = AsyncClient(endpoint=rpc_url)
        else:
            self.client = Client(endpoint=rpc_url)

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

    def sign_send_transaction(self, transaction_data: str, signatures_list: list = None, print_link: bool = True):
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

        self.get_status_transaction(transaction_hash=transaction_hash)
        if print_link is True:
            print(f"{c.GREEN}Transaction sent: https://explorer.solana.com/tx/{transaction_hash}{c.RESET}")

    def get_status_transaction(self, transaction_hash: str):
        print("Checking transaction status...")
        get_transaction_details = self.client.confirm_transaction(tx_sig=Signature.from_string(transaction_hash),
                                                                  sleep_seconds=1)
        transaction_status = get_transaction_details.value[0].err

        if transaction_status is None:
            print(f"Transaction SUCCESS! transaction_hash is {transaction_hash}")
        else:
            print(f"{c.RED}! Transaction FAILED!{c.RESET}")


snipers_processes = []


class Token_Sniper:

    def __init__(self, token_id, token_data):
        self.token_id = token_id
        self.token_data = token_data
        self.success = False

    def snipe_token(self):

        tokens_data = Config_CLI.get_tokens_data_no_async()
        config_data = Config_CLI.get_config_data_no_async()
        wallets = Wallets_CLI.get_wallets_no_async()
        wallet = Wallet(rpc_url=config_data['RPC_URL'],
                        private_key=wallets[str(tokens_data[self.token_id]['WALLET'])]['private_key'],
                        async_client=False)
        token_account = wallet.get_token_mint_account_no_async(self.token_data['ADDRESS'])
        token_balance = wallet.get_token_balance_no_async(token_mint_account=token_account)

        while True:
            if self.token_data['STATUS'] in ["NOT IN", "ERROR WHEN SWAPPING"]:

                while True:
                    if self.token_data['TIMESTAMP'] is None:
                        time.sleep(1)
                    elif self.token_data['TIMESTAMP'] is not None:
                        sleep_time = self.token_data['TIMESTAMP'] - int(time.time()) - 3
                        try:
                            time.sleep(sleep_time)
                        except ValueError:
                            pass

                    sol_price = f.get_crypto_price('SOL')
                    amount = int((self.token_data['BUY_AMOUNT'] * 10 ** 9) / sol_price)
                    quote_url = "https://quote-api.jup.ag/v6/quote?" + f"inputMint=So11111111111111111111111111111111111111112" + f"&outputMint={self.token_data['ADDRESS']}" + f"&amount={amount}" + f"&slippageBps={int(self.token_data['SLIPPAGE_BPS'])}"
                    quote_response = httpx.get(url=quote_url).json()

                    try:
                        if quote_response['error']:
                            time.sleep(1)
                    except:
                        break

                swap_data = {
                    "quoteResponse": quote_response,
                    "userPublicKey": wallet.wallet.pubkey().__str__(),
                    "wrapUnwrapSOL": True
                }

                retries = 0
                while True:
                    try:
                        get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data).json()
                        swap_data = get_swap_data['swapTransaction']
                        wallet.sign_send_transaction_no_async(transaction_data=swap_data, print_link=False)
                        self.success = True
                        break
                    except:
                        if retries == 3:
                            self.success = False
                            break
                        retries += 1
                        time.sleep(0.5)

                if self.success is True:
                    tokens_data[self.token_id]['STATUS'] = "IN"
                    self.token_data['STATUS'] = "IN"
                    alert_message = f"{self.token_data['NAME']} ({self.token_data['ADDRESS']}): IN"
                    f.send_discord_alert(alert_message)
                    f.send_telegram_alert(alert_message)
                else:
                    tokens_data[self.token_id]['STATUS'] = "ERROR ON SWAPPING"
                    self.token_data['STATUS'] = "ERROR WHEN SWAPPING"
                    alert_message = f"{self.token_data['NAME']} ({self.token_data['ADDRESS']}): BUY FAILED"
                    f.send_discord_alert(alert_message)
                    f.send_telegram_alert(alert_message)
                Config_CLI.edit_tokens_file_no_async(tokens_data)

            elif self.token_data['STATUS'] not in ["NOT IN", "ERROR WHEN SWAPPING"] and not self.token_data[
                'STATUS'].startswith('> '):
                time.sleep(1)
                sol_price = f.get_crypto_price('SOL')
                quote_url = "https://quote-api.jup.ag/v6/quote?" + f"inputMint={self.token_data['ADDRESS']}" + f"&outputMint=So11111111111111111111111111111111111111112" + f"&amount={token_balance['balance']['int']}" + f"&slippageBps={int(self.token_data['SLIPPAGE_BPS'])}"
                quote_response = httpx.get(quote_url).json()
                try:
                    out_amount = (int(quote_response['outAmount']) / 10 ** 9) * sol_price

                    amount_usd = out_amount

                    if amount_usd < self.token_data['STOP_LOSS'] or amount_usd > self.token_data['TAKE_PROFIT']:
                        swap_data = {
                            "quoteResponse": quote_response,
                            "userPublicKey": wallet.wallet.pubkey().__str__(),
                            "wrapUnwrapSOL": True
                        }
                        get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data).json()
                        swap_data = get_swap_data['swapTransaction']
                        wallet.sign_send_transaction_no_async(transaction_data=swap_data, print_link=False)

                        if amount_usd < self.token_data['STOP_LOSS']:
                            tokens_data[self.token_id]['STATUS'] = f"> STOP LOSS"
                            alert_message = f"{self.token_data['NAME']} ({self.token_data['ADDRESS']}): STOP LOSS @ ${amount_usd}"
                            f.send_discord_alert(alert_message)
                            f.send_telegram_alert(alert_message)
                        elif amount_usd > self.token_data['TAKE_PROFIT']:
                            tokens_data[self.token_id]['STATUS'] = f"> TAKE PROFIT"
                            alert_message = f"{self.token_data['NAME']} ({self.token_data['ADDRESS']}): TAKE PROFIT @ ${amount_usd}"
                            f.send_discord_alert(alert_message)
                            f.send_telegram_alert(alert_message)

                        Config_CLI.edit_tokens_file_no_async(tokens_data)
                        break
                # If token balance not synchronized yet (on buy)
                except:
                    pass

            else:
                break

    @staticmethod
    async def run():
        """Starts all the sniper token instance"""
        tokens_snipe = await Config_CLI.get_tokens_data()
        for token_id, token_data in tokens_snipe.items():
            token_sniper_instance = Token_Sniper(token_id, token_data)
            process = Process(target=token_sniper_instance.snipe_token, args=())
            snipers_processes.append(process)

        for sniper_process in snipers_processes:
            sniper_process.start()


if __name__ == "__main__":
    wallet = Wallet(rpc_url="https://api.mainnet-beta.solana.com",
                    private_key=TEST_USER_PRIVATE_KEY,
                    async_client=False)

    # Print all balances
    balances_df = pd.DataFrame(columns=["Token", "Balance", "Decimals", "Amount", "int"])
    for token in TRADING_TOKENS:
        if token == "SOL":
            token_balance = wallet.get_token_balance(token_mint_account=TEST_USER_PUBLIC_KEY)
            balances_df = pd.concat([balances_df, pd.DataFrame({"Token": token,
                                                                "Balance": token_balance['balance']['float'],
                                                                "Decimals": TOKEN_MINT_INFO[token]["Decimals"],
                                                                "int": token_balance['balance']['int'],
                                                                "Amount": token_balance['balance']['float']},
                                                               index=[0])])
        else:
            token_mint_account = wallet.get_token_mint_account(token_mint=TOKEN_MINT_INFO[token]["Address"])
            token_balance = wallet.get_token_balance(token_mint_account=token_mint_account)
            balances_df = pd.concat([balances_df, pd.DataFrame({"Token": token,
                                                                "Balance": token_balance['balance']['float'],
                                                                "Decimals": TOKEN_MINT_INFO[token]["Decimals"],
                                                                "int": token_balance['balance']['int'],
                                                                "Amount": token_balance['balance']['float']},
                                                               index=[0])])
    balances_df = balances_df.reset_index(drop=True)
    print(tabulate(balances_df, headers='keys', tablefmt='pretty'))

    # token_balance = wallet.get_token_balance(token_mint_account=TEST_USER_PUBLIC_KEY)
    # print(f'SOL balance: {token_balance}')
    #
    # token_mint_account = wallet.get_token_mint_account(token_mint=TOKEN_MINT_INFO["USDC"]["Address"])
    # print(f'token mint account type: {type(token_mint_account)}')
    #
    # print(TOKEN_MINT_INFO["USDC"]["Address"])
    # token_balance = wallet.get_token_balance(token_mint_account=token_mint_account)
    # print(f'USDC balance: {token_balance}')

    # USDC有6个decimal，所以1USDC=1000000，SOL有9个，所以1SOL有1000000000，我要交易0.005SOL，应该写5000000
    # quote_url = ('https://quote-api.jup.ag/v6/quote?inputMint=So11111111111111111111111111111111111111112'
    #              '&outputMint=EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v&amount=2000000&slippageBps=10')
    # amount = 0.002SOL，那么交易后Solana应该剩0.01278-gas(0.00011)=个，USDC应该0.24+0.2~左右价值

    # output_asset_amount = 0.01 * (10 ** TOKEN_MINT_INFO["USDC"]["Decimals"])
    # # remove the decimal point
    # output_asset_amount = int(output_asset_amount)
    #
    # output_asset_slippage_list = [20, 50, 100]
    # quote_url = (f'https://quote-api.jup.ag/v6/quote'
    #              f'?inputMint={TOKEN_MINT_INFO["SOL"]["Address"]}'
    #              f'&outputMint={TOKEN_MINT_INFO["USDC"]["Address"]}'
    #              f'&amount={output_asset_amount}'
    #              f'&slippageBps={output_asset_slippage_list[1]}')
    # print(quote_url)
    # # 执行这条的话，USDC到Solana，支付0.1USDC，USDC剩余为0.37216，SOL为0.01267+0.00088-gas(0.00011)=0.01344
    #
    # quote_response = httpx.get(url=quote_url).json()
    # swap_data = {
    #     "quoteResponse": quote_response,
    #     "userPublicKey": TEST_USER_PUBLIC_KEY,
    #     "wrapUnwrapSOL": True
    # }
    # # print(swap_data)
    # get_swap_data = httpx.post(url="https://quote-api.jup.ag/v6/swap", json=swap_data).json()
    # print(get_swap_data)
    # swap_data = get_swap_data['swapTransaction']
    #
    # wallet.sign_send_transaction(transaction_data=swap_data, print_link=True)
    #
    # """
    # 执行完这个之后，直接在jup上成交了，基本上全都转化为USDC了，要小心啊，不然可能没有sol支付gas了
    # """
