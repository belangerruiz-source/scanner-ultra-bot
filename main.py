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

# =========================
# PARES A ANALIZAR
# =========================
coins = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}


# =========================
# CONSULTA PRECIOS
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

    score = 72 - abs(cambio * 8)

    if cambio > 0:
        score += 8

    if score < 55:
        score = 55

    if score > 90:
        score = 90

    return int(score)


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
# MEJOR PAR
# =========================
def mejor_par():
    lista = []

    for par, coin in coins.items():
        precio, cambio = datos_coin(coin)

        if precio is not None:
            lista.append((par, precio, cambio))

    if not lista:
        return None

    # Menor volatilidad = más estable
    mejor = sorted(lista, key=lambda x: abs(x[2]))[0]

    return mejor


# =========================
# ESCANEO GENERAL
# =========================
def escanear():
    texto = "ESCÁNER ULTRA V6.5\n\n"

    lista = []

    for par, coin in coins.items():
        precio, cambio = datos_coin(coin)

        if precio is None:
            texto += f"{par}: Error\n"
            continue

        texto += f"{par}: {estado(cambio)} | {round(cambio,2)}%\n"
        lista.append((par, precio, cambio))

    if not lista:
        return texto + "\nSin datos."

    mejor = sorted(lista, key=lambda x: abs(x[2]))[0]

    par = mejor[0]
    precio = mejor[1]
    cambio = mejor[2]

    conf = confianza(cambio)

    texto += "\n------------------\n"

    if cambio < -0.50 or conf < 65:
        texto += "🚫 NO OPERAR HOY\nMercado sin ventaja clara."
        return texto

    texto += f"✅ Mejor opción: {par}\n"
    texto += f"Confianza: {conf}%"

    return texto


# =========================
# PREPARAR ENTRADA
# =========================
def preparar_entrada():
    dato = mejor_par()

    if dato is None:
        return "Sin datos de mercado."

    par, precio, cambio = dato
    conf = confianza(cambio)

    if cambio < -0.50 or conf < 65:
        return "🚫 Hoy no conviene entrar."

    entrada = round(precio * 0.997, 6)
    tp = round(precio * 1.005, 6)
    sl = round(precio * 0.992, 6)

    texto = f"""
📌 ENTRADA PREPARADA

Par: {par}

Precio actual: {precio}
Compra límite: {entrada}

Take Profit: {tp}
Stop Loss: {sl}

Confianza: {conf}%
Riesgo: Bajo/Medio
Monto sugerido: 10 USDT
"""
    return texto


# =========================
# CAPITAL
# =========================
def ruta_20():
    texto = """
💰 RUTA A 20 USDT

Capital actual: 10 USDT

Meta:
+0.20 USDT promedio por operación buena

Necesitas aprox:
50 operaciones limpias

Regla:
Solo operar cuando confianza > 70%
"""
    return texto


# =========================
# COMANDO START
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [InlineKeyboardButton("🔍 Escanear", callback_data="scan")],
        [InlineKeyboardButton("✅ Preparar Entrada", callback_data="entrar")],
        [
            InlineKeyboardButton("📊 Estado", callback_data="estado"),
            InlineKeyboardButton("💰 Ruta 20", callback_data="ruta")
        ],
        [InlineKeyboardButton("🛑 No operar", callback_data="cerrar")]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "SCANNER ULTRA BOT V6.5",
        reply_markup=reply_markup
    )


# =========================
# COMANDO /SCAN
# =========================
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")
    await update.message.reply_text(escanear())


# =========================
# BOTONES
# =========================
async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    if query.data == "scan":
        await query.message.reply_text("Escaneando mercado...")
        await query.message.reply_text(escanear())

    elif query.data == "entrar":
        await query.message.reply_text(preparar_entrada())

    elif query.data == "estado":
        await query.message.reply_text("Sistema activo ✅")

    elif query.data == "ruta":
        await query.message.reply_text(ruta_20())

    elif query.data == "cerrar":
        await query.message.reply_text("🛑 Confirmado: hoy no operamos.")


# =========================
# APP
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CallbackQueryHandler(botones))

print("Bot iniciado...")
app.run_polling()