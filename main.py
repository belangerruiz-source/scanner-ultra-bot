import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

def datos_coin(id_coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={id_coin}"
        r = requests.get(url, timeout=10).json()[0]

        precio = r["current_price"]
        cambio = r["price_change_percentage_24h"]

        return precio, cambio
    except:
        return None, None

def estado(cambio):
    if cambio is None:
        return "Error"
    elif cambio > 1:
        return "Fuerte 📈"
    elif cambio < -1:
        return "Débil 📉"
    else:
        return "Lateral ➖"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo. Usa /scan")

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")

    resultados = []

    texto = "ESCÁNER ULTRA V2\n\n"

    for par, coin in coins.items():
        precio, cambio = datos_coin(coin)
        est = estado(cambio)

        texto += f"{par}: {est}\n"

        if precio:
            resultados.append((par, precio, cambio))

    if resultados:
        mejor = max(resultados, key=lambda x: x[2])

        par = mejor[0]
        precio = mejor[1]

        entrada = round(precio * 0.997, 6)
        tp = round(precio * 1.005, 6)
        sl = round(precio * 0.992, 6)

        confianza = min(max(int(50 + mejor[2] * 10), 55), 90)

        texto += f"\nMEJOR OPCIÓN: {par}\n"
        texto += f"Entrada ideal: {entrada}\n"
        texto += f"TP: {tp}\n"
        texto += f"SL: {sl}\n"
        texto += f"Confianza: {confianza}%"

    await update.message.reply_text(texto)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

app.run_polling()