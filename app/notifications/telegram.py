from telegram import Bot
from app.strategies.base import BaseStrategy
import os
from dotenv import load_dotenv

load_dotenv(".env")

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
chat_id = os.getenv("TELEGRAM_CHANNEL_ID")

def format_message(coin: str, signal: dict, confirmations: list[BaseStrategy]) -> str:
    action = signal.get("action", "HOLD")
    entry = signal.get("entry", "N/A")
    stop_loss = signal.get("stop_loss", "N/A")
    take_profit = signal.get("take_profit", "N/A")

    explanation_lines = [
        f"📌 *Why:*",
        *[f"• {s.justification_text(signal)}" for s in confirmations]
    ]

    return (
        f"📈 *{coin}* strategy signal\n\n"
        f"🧠 *Action:* `{action}`\n"
        f"💰 *Entry:* `{entry}`\n"
        f"📉 *Stop Loss:* `{stop_loss}`\n"
        f"🎯 *Take Profit:* `{take_profit}`\n\n"
        + "\n".join(explanation_lines)
    )

async def send_strategy_signal_via_telegram(signal: dict, coin: str, confirmations: list[BaseStrategy]):
    if signal.get("action") not in ["BUY", "SHORT"]:
        return

    message = format_message(coin, signal, confirmations)
    await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
