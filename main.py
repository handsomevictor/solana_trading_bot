"""
Should execute the followings:

- Remove all files in `./trading_bot/database/tmp/` directory

"""
import os

from all_strategies.strategy_buy_dip.strategy_buy_dip import BuyInstantDip

# 这里需要包含邮件通知
if __name__ == '__main__':
    base = "SOL"
    quote = "USDC"
    dip_level = [0.01, 0.046]
    upload_records_measurement_name = "jup_solusdc_records_4"
    bucket_name = "test_bucket"

    TMP_DATABASE_DIR = os.path.join(os.path.dirname(__file__), "all_strategies", "strategy_buy_dip", "records")
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
