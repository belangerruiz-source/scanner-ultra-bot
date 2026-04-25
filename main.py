import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

def precio(symbol):
    url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
    return float(requests.get(url).json()["price"])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo. Usa /scan")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trx = precio("TRXUSDT")
    ada = precio("ADAUSDT")
    doge = precio("DOGEUSDT")

    texto = f"""
SCAN BINANCE

TRX/USDT: {trx}
ADA/USDT: {ada}
DOGE/USDT: {doge}

Versión 1 activa
"""
    await update.message.reply_text(texto)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

app.run_polling()