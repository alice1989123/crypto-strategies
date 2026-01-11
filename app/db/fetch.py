import psycopg2
import os
from typing import List, Dict
import dotenv
import pandas as pd
dotenv.load_dotenv(".env")
def fetch_latest_prediction_with_metadata(coin: str,  interval: str, model_name: str) :
    conn = psycopg2.connect(
        dbname=os.getenv("DBNAME"),
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD"),
        host=os.getenv("DBHOST"),
    )
    cursor = conn.cursor()

    # Fetch the latest metadata entry
    cursor.execute("""
    SELECT prediction_id, metadata_json
    FROM prediction_runs
    WHERE coin = %s
      AND model_name = %s
      AND "interval" = %s
    ORDER BY created_at DESC
    LIMIT 1
    """, (coin, model_name, interval))
    row = cursor.fetchone()

    if not row:
        return [], [], {}

    prediction_id, metadata_json = row

    # Fetch with is_historical flag
    cursor.execute("""
        SELECT point_time, value, is_historical FROM predicted_prices
        WHERE prediction_id = %s ORDER BY point_time ASC
    """, (prediction_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # Separate based on is_historical flag
    historical = [{"date": r[0], "price": float(r[1])} for r in rows if r[2]]
    forecast   = [{"date": r[0], "price": float(r[1])} for r in rows if not r[2]]

    return historical, forecast, metadata_json


def get_stored_klines(coin: str, start: str, end: str, interval: str ) -> pd.DataFrame:
    start_ts = pd.to_datetime(start)
    end_ts = pd.to_datetime(end)

    conn = psycopg2.connect(
        dbname="crypto_predictions",
        user=os.getenv("DBUSER"),
        password=os.getenv("DBPASSWORD"),
        host=os.getenv("DBHOST"),
    )
    query = """
        SELECT open_time, close
        FROM binance_klines
        WHERE symbol = %s
        AND timeframe = %s
        AND open_time >= %s
        AND open_time <= %s
        ORDER BY open_time ASC
    """

    df = pd.read_sql_query(query, conn, params=(coin, interval, start_ts, end_ts))
    df["open_time"] = pd.to_datetime(df["open_time"])
    df["close"] = df["close"].astype(float)

    conn.close()
    return df