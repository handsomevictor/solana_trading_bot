"""
According to JUP SOL/USDC price graph, very often the price would dip a bit, example:
Normal level =106.7, dip level = [102-106].

I don't believe the price can be as low as 80, so I will set a range.

Strategy details:
1. When there is a dip for once (0.66% - 4.6%), start to buy a fixed amount of SOL instantly
2. When checked the price went back to normal, sell it instantly - if failed, sell it after 5 seconds
   after the status is confirmed
3. If the transaction price is not expected (didn't buy the dip), sell it instantly
4. How to calculate the dip level? I will compare the latest price with the average of the past 20 prices
5. Every 2 transactions should have at least 1 minute interval


Reminders:
1. Always leave 0.1 SOL in the account for transaction fee
2. If you have bought SOL, but somehow didn't trigger the sell, after 15 seconds, sell it
3. If the transaction price is not expected, sell it
4. Always check the balance before buying or selling
5. Always record the gas fee
6. When started the program, self.records_for_trading should always be more than 30 rows before making any decision
7. When initializing the program, always check if the balance is correct, if there is no USDC, don't start the program
   or sell all the SOL
"""

import os
import csv
import json
import time
import sched
import datetime
import requests
import threading
import pandas as pd

from strategies.strategy_buy_dip.influxdb_tool import save_records_to_influxdb

from trading_bot.transaction_executor import TradeOnJup
from trading_bot.resources import (USER_PUBLIC_KEY, USER_PRIVATE_KEY, TOKEN_MINT_INFO, TRADING_TOKENS, RPC_URL,
                                   TRANSACTION_TIMEOUT_SECONDS)

class BuyInstantDip:
    def __init__(self, base, quote, dip_level, upload_records_measurement_name, bucket_name, abnormal_price_range=0.05):
        self.base = base
        self.quote = quote

        self.executor = TradeOnJup(rpc_url=RPC_URL,
                                   private_key=USER_PRIVATE_KEY,
                                   async_client=False)
        # check balance
        self.executor.get_token_balance_df()

        self.dip_level = [0.01, 0.046] if dip_level is None else dip_level
        self.mid_dip_level = (self.dip_level[0] + self.dip_level[1]) / 2

        self.first_dip_price = None
        self.latest_price = None

        self.position = 0
        self.sell_start_time = time.time()  # this is for forced selling after 60 seconds of buying without selling

        self.upload_records_measurement_name = upload_records_measurement_name
        self.bucket_name = bucket_name

        self.abnormal_price_range = abnormal_price_range

        # the following records are for trading - only the latest 100 records will be kept
        self.records_for_trading = pd.DataFrame(columns=["time", "base_id", "quote_id", "price", "time_delay",
                                                         "gas_fee", "record", "status"])
        self.records = pd.DataFrame(columns=["time", "record", "status", "current_position", "buy_price", 'sell_price',
                                             "time_elapsed"])
        self.records.to_csv(records_path, mode='a', header=True, index=False)

    def __get_unit_buy_price(self):
        url = f'https://price.jup.ag/v4/price?ids={self.base}&vsToken={self.quote}'
        response = requests.get(url)
        data = response.json()
        return (data['data'][self.base]['id'],
                data['data'][self.base]['vsToken'],
                data['data'][self.base]['price'],
                data['timeTaken'])

    def __get_unit_buy_price_every_second(self):
        """
        This function will be called twice every second
        """
        base_id, quote_id, price, time_delay = self.__get_unit_buy_price()
        time_str = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        data = {
            "time": time_str,
            "base_id": base_id,
            "quote_id": quote_id,
            "price": round(price, 6),
            "time_delay": time_delay
        }

        with open(file_path, "a") as f:
            writer = csv.writer(f)
            writer.writerow(data.values())

        self.records_for_trading = pd.concat([self.records_for_trading, pd.DataFrame(data, index=[0])])
        time.sleep(0.5 - time.time() % 0.5)

    def __detect_back_to_normal(self):
        print(f"Checking if the price is back to normal......")
        # will return if this is dip or back to normal
        latest_5_prices = self.records_for_trading["price"].iloc[-5: -1].mean()
        print(f'First dip price: {self.first_dip_price}, selling threshold: {latest_5_prices * (1 - self.dip_level[0])}')
        if self.first_dip_price is not None and latest_5_prices * (1 - self.dip_level[0]) > self.first_dip_price:
            self.first_dip_price = None
            return True
        else:
            return False

    def __detect_dip(self):
        latest_price = self.records_for_trading["price"].iloc[-1]
        self.latest_price = latest_price

        # normal price level = average of the last 100 prices
        general_normal_price = self.records_for_trading["price"].iloc[-100: -1]
        general_normal_price = general_normal_price[(general_normal_price >
                                                     (1 - self.abnormal_price_range) * latest_price) &
                                                    (general_normal_price <
                                                     (1 + self.abnormal_price_range) * latest_price)].mean()

        print(f"latest price: {latest_price:.6f}, general normal price: {general_normal_price:.6f}, "
              f"dip price: {general_normal_price * (1 - self.dip_level[0]):.6f}, current price is "
              f"{'lower' if latest_price < general_normal_price * (1 - self.dip_level[0]) else 'higher'}")

        # if the latest price is lower than the general normal price, it's a dip
        if (general_normal_price * (1 - self.dip_level[0]) >
                latest_price > general_normal_price * (1 - self.dip_level[1]) and self.position == 0):
            self.first_dip_price = latest_price
            return True
        else:
            return False

    def __transaction_status(self):
        print(f"Checking transaction status for {self.base} to {self.quote}......GOOD! Sleep for 5 seconds.")
        time.sleep(5)
        return True

    def __buy_instantly(self):
        print(f'Buying {self.base} instantly')

    def __sell_instantly(self):
        print(f'Selling {self.base} instantly')

    def execute_transaction(self):
        if len(self.records_for_trading) < 30:
            print(f"records_for_trading has only {len(self.records_for_trading)} records, do nothing")
            return None

        current_time = datetime.datetime.utcnow()

        detect_dip = self.__detect_dip()  # this step can't be optimized, you have to check every time

        if self.position == 1:
            detect_back_to_normal = self.__detect_back_to_normal()
        else:
            detect_back_to_normal = False

        if detect_dip:
            if self.position == 1:
                print(f"At {current_time.strftime('%Y-%m-%d %H:%M:%S')}, already bought, do nothing")
                return None
            elif self.position == 0:
                self.__buy_instantly()

                self.sell_start_time = time.time()
                self.position = 1
            else:
                print(f"Unknown position: {self.position}")

        elif detect_back_to_normal:
            if self.position == 0:
                print(f"At {current_time.strftime('%Y-%m-%d %H:%M:%S')}, already sold, do nothing")
                return None
            elif self.position == 1:
                self.__sell_instantly()
                self.position = 0
            else:
                print(f"Unknown position: {self.position}")

        else:
            return None

        status = self.__transaction_status()  # 耗时较长，所以只在position发生变化时才调用

        time_elapsed = datetime.datetime.utcnow() - current_time
        time_elapsed = round((time_elapsed.seconds * 1000 + time_elapsed.microseconds // 1000) / 1000, 6)

        self.records = pd.concat([self.records,
                                  pd.DataFrame({"time": current_time,
                                                "record": "buy" if detect_dip else "sell",
                                                "status": status,
                                                "current_position": self.position,
                                                "buy_price": float(self.first_dip_price) if detect_dip else float(-1.0),
                                                "sell_price": float(-1.0) if detect_dip else float(self.latest_price),
                                                "time_elapsed": time_elapsed}, index=[0])])
        self.records.to_csv(records_path, mode='a', header=False, index=False)
        print(f"Saved records to {records_path}")
        self.records = pd.DataFrame(columns=["time", "record", "status", "current_position", "buy_price",
                                             "sell_price", "time_elapsed"])
        # 打印一下balance
        original_balances_df = self.executor.get_token_balance_df()

    def run_strategy(self):
        start_time = time.time()
        while True:
            try:
                self.__get_unit_buy_price_every_second()
                self.execute_transaction()

                self.records_for_trading = self.records_for_trading.iloc[-150:]
                if time.time() - start_time > 5:
                    start_time = time.time()
                    print(f"records are being saved to influxdb...")
                    save_records_to_influxdb(measurement_name=self.upload_records_measurement_name,
                                             bucket_name=self.bucket_name,
                                             records_path=os.path.join(TMP_DATABASE_DIR, f"{base}_{quote}_records.csv"))
                    # check balance - very fast, almost have no impact on the performance
                    self.executor.get_token_balance_df()

                # If it takes more than 1 minute before selling, sell it
                if time.time() - self.sell_start_time > 60 and self.position == 1:
                    print(f'Forced to sell, because it takes more than 60 seconds to sell')
                    self.__sell_instantly()
                    self.position = 0
                    self.__transaction_status()
                    self.sell_start_time = time.time()

                    self.records = pd.concat([self.records, pd.DataFrame({"time": datetime.datetime.utcnow(),
                                                                          "record": "forced_sell",
                                                                          "status": 'Transaction Status tbd',
                                                                          "current_position": self.position,
                                                                          "buy_price": self.first_dip_price,
                                                                          "sell_price": self.latest_price,
                                                                          "time_elapsed": -1}, index=[0])])

                    self.records.to_csv(records_path, mode='a', header=False, index=False)

            except Exception as e:
                # Generally the error mainly comes from connecting to InfluxDB
                print(f"Error occurred: {str(e)}")
                pass


if __name__ == '__main__':
    base = "SOL"
    quote = "USDC"
    dip_level = [0.01, 0.046]
    upload_records_measurement_name = "jup_solusdc_records_4"
    bucket_name = "test_bucket"

    TMP_DATABASE_DIR = os.path.join(os.path.dirname(__file__), "records")
    file_path = os.path.join(TMP_DATABASE_DIR, f"{base}_{quote}_price.csv")
    records_path = os.path.join(TMP_DATABASE_DIR, f"{base}_{quote}_records.csv")

    if not os.path.exists(TMP_DATABASE_DIR):
        os.makedirs(TMP_DATABASE_DIR)

    # When first running, clear the price.csv
    os.remove(file_path) if os.path.exists(file_path) else None
    os.remove(records_path) if os.path.exists(records_path) else None
    print(f"Removed {file_path}")

    strategy = BuyInstantDip(base, quote, dip_level, upload_records_measurement_name, bucket_name)
    strategy.run_strategy()


    # input_asset = quote
    # output_asset = base
    # input_asset_amount = 0.01
    #
    # trade_pamras = {
    #     "input_asset": input_asset,
    #     "output_asset": output_asset,
    #     "input_asset_amount": int(input_asset_amount * (10 ** TOKEN_MINT_INFO[input_asset]["Decimals"])),
    #     "output_asset_slippage_list": [10, 22, 35, 50],
    #     "jup_post_request_timeout_seconds": 10,
    # }
    # execute_trade = executor.trade_on_jup(**trade_pamras)
    #
    # if execute_trade != 200:
    #     pass  # do something
    #
    # # check balance again
    # current_balances_df = executor.get_token_balance_df()








