import os
from telegram import Bot
from dotenv import load_dotenv
import asyncio

load_dotenv(".env")

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHANNEL_ID")
bot = Bot(token=token)

async def send_strategy_signal_via_telegram(signal: dict, coin: str):
    if signal.get("action") not in ["BUY", "SHORT"]:
        return

    action = signal["action"]
    entry = signal.get("entry", "N/A")
    stop_loss = signal.get("stop_loss", "N/A")
    take_profit = signal.get("take_profit", "N/A")

    message = (
        f"📈 *{coin}* strategy signal:\n"
        f"🔹 Action: *{action}*\n"
        f"💰 Entry: `{entry}`\n"
        f"🛑 Stop Loss: `{stop_loss}`\n"
        f"🎯 Take Profit: `{take_profit}`"
    )

    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
