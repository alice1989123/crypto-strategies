import psycopg2
import os
import uuid
import json
from dotenv import load_dotenv

load_dotenv(".env")

def save_strategy_signal(coin: str, model_name: str, signal: dict):
    conn = psycopg2.connect(
        dbname="crypto_predictions",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST")
    )
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO strategy_signals (id, coin, model_name, signal)
        VALUES (%s, %s, %s, %s)
    """, (str(uuid.uuid4()), coin, model_name, json.dumps(signal)))

    conn.commit()
    cursor.close()
    conn.close()