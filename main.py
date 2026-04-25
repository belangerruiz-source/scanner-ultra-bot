import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

# Monedas a revisar
coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

# Obtener datos desde CoinGecko mostrando error real
def datos_coin(id_coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={id_coin}"
        
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(url, headers=headers, timeout=10)

        # si no responde 200
        r.raise_for_status()

        data = r.json()

        if not data:
            return "Sin datos", None

        precio = data[0]["current_price"]
        cambio = data[0]["price_change_percentage_24h"]

        return precio, cambio

    except Exception as e:
        return f"ERROR: {str(e)}", None


# Estado del mercado
def estado(cambio):
    if cambio is None:
        return "Error"
    elif cambio > 1:
        return "Fuerte 📈"
    elif cambio < -1:
        return "Débil 📉"
    else:
        return "Lateral ➖"


# Comando start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo. Usa /scan")


# Comando scan
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")

    texto = "ESCÁNER DEBUG V1\n\n"

    for par, coin in coins.items():
        precio, cambio = datos_coin(coin)

        if cambio is None:
            texto += f"{par}: {precio}\n\n"
        else:
            texto += f"{par}: {precio} USD | {estado(cambio)} | {round(cambio,2)}%\n"

    await update.message.reply_text(texto)


# Inicializar bot
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

print("Bot iniciado...")
app.run_polling()