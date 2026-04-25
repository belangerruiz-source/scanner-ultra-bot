import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

# Pares a escanear
coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

# Obtener precio y variación 24h desde CoinGecko
def datos_coin(id_coin):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids={id_coin}"
        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        data = r.json()[0]

        precio = float(data["current_price"])
        cambio = float(data["price_change_percentage_24h"])

        return precio, cambio

    except:
        return None, None


# Clasificación simple
def estado(cambio):
    if cambio is None:
        return "Error"
    elif cambio >= 1:
        return "Fuerte 📈"
    elif cambio <= -1:
        return "Débil 📉"
    else:
        return "Lateral ➖"


# Recomendación principal
def recomendacion(cambio):
    if cambio is None:
        return "Sin datos"
    elif cambio >= 1:
        return "Esperar retroceso y entrar límite"
    elif cambio > -0.5 and cambio < 1:
        return "Entrada prudente posible"
    else:
        return "No entrar aún"


# Confianza
def confianza(cambio):
    if cambio is None:
        return 0

    base = 70 - abs(cambio * 10)

    if cambio > 0:
        base += 8

    if base < 55:
        base = 55
    if base > 88:
        base = 88

    return int(base)


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot activo. Usa /scan")


# SCAN
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")

    resultados = []
    texto = "ESCÁNER ULTRA V3\n\n"

    for par, coin in coins.items():
        precio, cambio = datos_coin(coin)

        if precio is None:
            texto += f"{par}: Error\n"
            continue

        est = estado(cambio)

        texto += f"{par}: {est} | {round(cambio,2)}%\n"

        resultados.append((par, precio, cambio))

    if resultados:

        # Mejor par = más cercano a positivo sin estar disparado
        mejor = sorted(resultados, key=lambda x: abs(x[2]))[0]

        par = mejor[0]
        precio = mejor[1]
        cambio = mejor[2]

        entrada = round(precio * 0.997, 6)
        tp = round(precio * 1.005, 6)
        sl = round(precio * 0.992, 6)

        texto += "\n--------------------\n"
        texto += f"MEJOR OPCIÓN: {par}\n\n"
        texto += f"Precio actual: {precio}\n"
        texto += f"Entrada ideal: {entrada}\n"
        texto += f"TP: {tp}\n"
        texto += f"SL: {sl}\n"
        texto += f"Confianza: {confianza(cambio)}%\n"
        texto += f"Acción: {recomendacion(cambio)}"

    await update.message.reply_text(texto)


# APP
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

print("Bot iniciado...")
app.run_polling()