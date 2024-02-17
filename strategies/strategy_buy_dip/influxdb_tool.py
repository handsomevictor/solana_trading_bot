import os
import time
import pandas as pd
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client import InfluxDBClient, Point, WriteOptions, WritePrecision

INFLUXDB_ORG = os.environ.get('VICTOR_INFLUXDB_ORG')
INFLUXDB_TOKEN = os.environ.get('VICTOR_INFLUXDB_TOKEN')
INFLUXDB_URL = os.environ.get('VICTOR_INFLUXDB_URL')

client = influxdb_client.InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG
)

write_api = client.write_api(write_options=SYNCHRONOUS)
TMP_DATABASE_DIR = os.path.join(os.path.dirname(__file__), "records")


def save_records_to_influxdb(measurement_name, bucket_name, records_path):
    saving_time = time.time()
    print(f"Start uploading records file {records_path} to InfluxDB...")
    # judge if the file exists
    if not os.path.exists(records_path):
        print(f"File {records_path} does not exist!")
        return None

    records_df = pd.read_csv(records_path)
    # "time", "record", "status", "time_elapsed"

    points = []
    for i, row in records_df.iterrows():
        p = Point(measurement_name) \
            .tag("status", row['status']) \
            .tag("record", row['record']) \
            .field("time_elapsed", row['time_elapsed']) \
            .field("current_position", row['current_position']) \
            .time(row['time'], WritePrecision.NS)
        points.append(p)
    write_api.write(bucket_name, record=points)
    print(f"Have uploaded the records file {len(records_df)} records to InfluxDB!")
    print(f"Time elapsed: {time.time() - saving_time} seconds")


if __name__ == '__main__':
    base = "SOL"
    quote = "USDC"
    measurement_name = "jup_solusdc_records_1"
    bucket_name = "test_bucket"
    save_unit_buy_price(base, quote, measurement_name, bucket_name)
