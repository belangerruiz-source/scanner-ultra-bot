import requests
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)

TOKEN = os.getenv("TOKEN")

# Monedas a revisar
coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}


# =========================
# DATOS
# =========================
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


# =========================
# REGLAS
# =========================
def estado(cambio):
    if cambio is None:
        return "Error"
    elif cambio >= 1:
        return "Fuerte 📈"
    elif cambio <= -1:
        return "Débil 📉"
    else:
        return "Lateral ➖"


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


def accion(cambio):
    if cambio is None:
        return "Sin datos"
    elif cambio >= 1:
        return "Esperar retroceso"
    elif -0.50 <= cambio < 1:
        return "Entrada prudente"
    else:
        return "No entrar"


# =========================
# ANALISIS
# =========================
def analizar():
    resultados = []

    texto = "ESCÁNER ULTRA V6\n\n"

    for par, coin in coins.items():

        precio, cambio = datos_coin(coin)

        if precio is None:
            texto += f"{par}: Error\n"
            continue

        est = estado(cambio)

        texto += f"{par}: {est} | {round(cambio,2)}%\n"

        resultados.append((par, precio, cambio))

    if not resultados:
        return texto + "\nSin datos."

    # Mejor par = menor volatilidad y no tan rojo
    mejor = sorted(resultados, key=lambda x: abs(x[2]))[0]

    par = mejor[0]
    precio = mejor[1]
    cambio = mejor[2]

    conf = confianza(cambio)
    act = accion(cambio)

    # FILTRO NO OPERAR
    if cambio < -0.50 or conf < 65:
        texto += "\n------------------\n"
        texto += "🚫 NO OPERAR HOY\n"
        texto += "Mercado sin ventaja clara."
        return texto

    entrada = round(precio * 0.997, 6)
    tp = round(precio * 1.005, 6)
    sl = round(precio * 0.992, 6)

    texto += "\n------------------\n"
    texto += f"MEJOR OPCIÓN: {par}\n\n"
    texto += f"Precio actual: {precio}\n"
    texto += f"Entrada ideal: {entrada}\n"
    texto += f"TP: {tp}\n"
    texto += f"SL: {sl}\n"
    texto += f"Confianza: {conf}%\n"
    texto += f"Acción: {act}"

    return texto


# =========================
# COMANDOS
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton("🔍 Escanear", callback_data="scan")
        ],
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("🛑 Cerrar", callback_data="cerrar")
        ]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Bot activo. Usa botones:",
        reply_markup=reply_markup
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")
    texto = analizar()
    await update.message.reply_text(texto)


# =========================
# BOTONES
# =========================
async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "scan":
        await query.message.reply_text("Escaneando mercado...")
        texto = analizar()
        await query.message.reply_text(texto)

    elif query.data == "estado":
        await query.message.reply_text("Sistema activo ✅")

    elif query.data == "cerrar":
        await query.message.reply_text("Sin operación abierta aún.")


# =========================
# APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CallbackQueryHandler(botones))

print("Bot iniciado...")
app.run_polling()