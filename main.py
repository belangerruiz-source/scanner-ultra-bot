import requests
import os
import time

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

TOKEN = os.getenv("TOKEN")

# =========================
# CONFIG
# =========================
coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

cache = {}


# =========================
# API COINGECKO
# =========================
def precio(coin_id):
    try:
        url = (
            "https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&ids={coin_id}"
        )

        headers = {"User-Agent": "Mozilla/5.0"}

        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()

        data = r.json()

        if not data:
            return None, None

        item = data[0]

        p = float(item["current_price"])
        c = float(item["price_change_percentage_24h"])

        return p, c

    except Exception:
        return None, None


# =========================
# REGLAS
# =========================
def estado(cambio):
    if cambio is None:
        return "Error"
    if cambio >= 1:
        return "Fuerte 📈"
    if cambio <= -1:
        return "Débil 📉"
    return "Lateral ➖"


def confianza(cambio):
    if cambio is None:
        return 0

    score = 80 - abs(cambio * 10)

    if cambio > 0:
        score += 5

    if score < 55:
        score = 55

    if score > 92:
        score = 92

    return int(score)


# =========================
# ESCANEO
# =========================
def scan_market():
    global cache

    texto = "ESCÁNER ULTRA PRO V2\n\n"
    datos = []

    for par, coin in coins.items():

        p, c = precio(coin)

        if p is None:
            texto += f"{par}: Error\n"
            continue

        texto += f"{par}: {round(p,6)} USD | {estado(c)} | {round(c,2)}%\n"

        datos.append((par, p, c))

    if not datos:
        return "Sin datos del mercado."

    # mejor = cambio más cercano a cero
    mejor = sorted(datos, key=lambda x: abs(x[2]))[0]

    par = mejor[0]
    p = mejor[1]
    c = mejor[2]
    conf = confianza(c)

    cache = {
        "par": par,
        "precio": p,
        "cambio": c,
        "confianza": conf,
        "time": int(time.time())
    }

    texto += "\n------------------\n"

    if c < -0.60 or conf < 68:
        texto += "🚫 NO OPERAR HOY\nMercado sin ventaja clara."
        return texto

    texto += f"✅ Mejor opción: {par}\n"
    texto += f"Confianza: {conf}%"

    return texto


# =========================
# PREPARAR ENTRADA
# =========================
def preparar():
    if not cache:
        return "Primero pulsa 🔍 Escanear"

    par = cache["par"]
    p = cache["precio"]
    conf = cache["confianza"]

    entrada = round(p * 0.997, 6)
    tp = round(p * 1.005, 6)
    sl = round(p * 0.992, 6)

    seg = int(time.time()) - cache["time"]

    return f"""
📌 ENTRADA PREPARADA

Par: {par}

Precio actual: {p}
Compra límite: {entrada}

Take Profit: {tp}
Stop Loss: {sl}

Confianza: {conf}%
Datos de hace: {seg} seg
Monto sugerido: 10 USDT
"""


# =========================
# RUTA CAPITAL
# =========================
def ruta():
    return """
💰 RUTA A 20 USDT

Capital actual: 10 USDT

Meta:
+0.20 USDT promedio por trade bueno

Necesitas:
50 trades limpios aprox.

Solo entrar con confianza > 75%
"""


# =========================
# START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    kb = [
        [InlineKeyboardButton("🔍 Escanear", callback_data="scan")],
        [InlineKeyboardButton("✅ Preparar Entrada", callback_data="prep")],
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("💰 Ruta 20", callback_data="ruta")
        ],
        [InlineKeyboardButton("🛑 No operar", callback_data="stop")]
    ]

    await update.message.reply_text(
        "SCANNER ULTRA BOT PRO V2",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# =========================
# BOTONES
# =========================
async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):

    q = update.callback_query
    await q.answer()

    if q.data == "scan":
        await q.message.reply_text("Escaneando mercado...")
        await q.message.reply_text(scan_market())

    elif q.data == "prep":
        await q.message.reply_text(preparar())

    elif q.data == "estado":
        await q.message.reply_text("Sistema activo ✅")

    elif q.data == "ruta":
        await q.message.reply_text(ruta())

    elif q.data == "stop":
        await q.message.reply_text("🛑 Confirmado: hoy no operamos.")


# =========================
# APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(botones))

print("BOT PRO V2 INICIADO")
app.run_polling()