import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

# ==============================
# TEST API
# ==============================

def test_api():
    try:
        r = requests.get("https://api.binance.com/api/v3/time", timeout=5)
        return r.status_code == 200
    except Exception as e:
        print("API ERROR:", e)
        return False

# ==============================
# DATA
# ==============================

def obtener_precio(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)

        print("STATUS:", r.status_code)

        if r.status_code != 200:
            return None

        data = r.json()
        return float(data["price"])

    except Exception as e:
        print("ERROR PRECIO:", e)
        return None

# ==============================
# COMMANDS
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok = test_api()

    msg = " BOT ACTIVO\n"

    if ok:
        msg += " API Binance OK\n"
    else:
        msg += " API Binance FALLA\n"

    msg += "\nUsa /scan"

    await update.message.reply_text(msg)

# ==============================

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Escaneando...")

    try:
        pares = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]

        texto = " DEBUG SCAN\n\n"

        for p in pares:
            precio = obtener_precio(p)

            if precio:
                texto += f"{p}: {precio}\n"
            else:
                texto += f"{p}: ERROR\n"

        await update.message.reply_text(texto)

    except Exception as e:
        await update.message.reply_text(f" ERROR SCAN:\n{e}")

# ==============================
# APP
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

print("BOT INICIADO...")

app.run_polling()