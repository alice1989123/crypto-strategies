import psycopg2
import os
from typing import List, Dict
import dotenv

dotenv.load_dotenv(".env")
def fetch_latest_prediction_with_metadata(coin: str, model_name: str):
    conn = psycopg2.connect(
        dbname="crypto_predictions",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
    )
    cursor = conn.cursor()

    # Fetch the latest metadata entry
    cursor.execute("""
        SELECT id, metadata_json FROM prediction_metadata
        WHERE coin = %s AND model_name = %s
        ORDER BY created_at DESC LIMIT 1
    """, (coin, model_name))
    row = cursor.fetchone()

    if not row:
        return [], [], {}

    prediction_id, metadata_json = row

    # Fetch with is_historical flag
    cursor.execute("""
        SELECT prediction_time, price, is_historical FROM predicted_prices
        WHERE id = %s ORDER BY prediction_time ASC
    """, (prediction_id,))
    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    # Separate based on is_historical flag
    historical = [{"date": r[0], "price": float(r[1])} for r in rows if r[2]]
    forecast   = [{"date": r[0], "price": float(r[1])} for r in rows if not r[2]]

    return historical, forecast, metadata_json
