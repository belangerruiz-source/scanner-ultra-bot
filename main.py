import requests
import os
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

cache = {}

def precio(coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={coin}"
        r = requests.get(url, timeout=10)
        data = r.json()[0]
        return float(data["current_price"]), float(data["price_change_percentage_24h"])
    except:
        return None, None

def scan_market():
    global cache

    texto = "ESCÁNER ULTRA PRO V1\n\n"
    datos = []

    for par, coin in coins.items():
        p, c = precio(coin)

        if p is None:
            texto += f"{par}: Error\n"
            continue

        texto += f"{par}: {round(p,6)} | {round(c,2)}%\n"
        datos.append((par,p,c))

    if not datos:
        return "Sin datos."

    mejor = sorted(datos, key=lambda x: abs(x[2]))[0]

    cache = {
        "par": mejor[0],
        "precio": mejor[1],
        "cambio": mejor[2],
        "time": int(time.time())
    }

    texto += f"\n✅ Mejor opción: {mejor[0]}"
    return texto

def preparar():
    if not cache:
        return "Primero pulsa 🔍 Escanear"

    p = cache["precio"]
    par = cache["par"]

    entrada = round(p * 0.997, 6)
    tp = round(p * 1.005, 6)
    sl = round(p * 0.992, 6)

    return f"""
📌 ENTRADA PREPARADA

Par: {par}

Compra límite: {entrada}
Take Profit: {tp}
Stop Loss: {sl}

Monto sugerido: 10 USDT
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    kb = [
        [InlineKeyboardButton("🔍 Escanear", callback_data="scan")],
        [InlineKeyboardButton("✅ Preparar Entrada", callback_data="prep")],
        [InlineKeyboardButton("📊 Estado", callback_data="estado")],
        [InlineKeyboardButton("💰 Ruta 20", callback_data="ruta")],
        [InlineKeyboardButton("🛑 No operar", callback_data="stop")]
    ]

    await update.message.reply_text(
        "SCANNER ULTRA BOT PRO",
        reply_markup=InlineKeyboardMarkup(kb)
    )

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.data == "scan":
        await q.message.reply_text("Escaneando...")
        await q.message.reply_text(scan_market())

    elif q.data == "prep":
        await q.message.reply_text(preparar())

    elif q.data == "estado":
        await q.message.reply_text("Sistema activo ✅")

    elif q.data == "ruta":
        await q.message.reply_text("Meta: 10 USDT → 20 USDT")

    elif q.data == "stop":
        await q.message.reply_text("Hoy no operamos 🛑")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(botones))

print("BOT PRO INICIADO")
app.run_polling()