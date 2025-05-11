import psycopg2
import os
import dotenv

dotenv.load_dotenv(".env")

def get_all_tracked_coins():
    conn = psycopg2.connect(
        dbname="crypto_predictions",
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        host=os.getenv("DB_HOST"),
    )
    cursor = conn.cursor()
    cursor.execute("SELECT symbol FROM coin_catalog WHERE tracked = true")
    coins = [r[0] for r in cursor.fetchall()]
    cursor.close()
    conn.close()
    return coins