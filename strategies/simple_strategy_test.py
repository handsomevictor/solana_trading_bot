"""
Swap from USDC to SOL every minute: 0.01 USDC to SOL with slippage 10, 22, 35, 50
"""
import os
import json
import datetime
import pandas as pd

from tools.logging_formatter import logger

import tools.color_functions as c
from trading_bot.transaction_executor import TradeOnJup
from trading_bot.resources import (USER_PRIVATE_KEY, TOKEN_MINT_INFO, RPC_URL)


def write_to_records(balances_df: pd.DataFrame):
    # write to records as json file, always use add mode
    with open(os.path.join(os.path.dirname(__file__), "records", "records.json"), "a") as f:
        f.write(str(datetime.datetime.now()))
        f.write("\n")
        f.write(json.dumps(balances_df.to_dict()))
        f.write("\n\n")
    logger.info(f"{c.GREEN}Records written to records.json at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "
                f"to ./trading_bot/strategies/records/records.json{c.RESET}")


def main():
    executor = TradeOnJup(rpc_url=RPC_URL,
                          private_key=USER_PRIVATE_KEY,
                          async_client=False)
    original_balances_df = executor.get_token_balance_df()
    write_to_records(original_balances_df)

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

    current_balances_df = executor.get_token_balance_df()
    write_to_records(current_balances_df)


if __name__ == '__main__':
    main()
    print(os.path.dirname(__file__))