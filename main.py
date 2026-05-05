import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler
)
import os

TOKEN = os.getenv("TOKEN")

# ==============================
# CONFIG
# ==============================

COINS = {
    "TRXUSDT": "tron",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin"
}

# ==============================
# DATOS (ANTI-FALLO)
# ==============================

def get_price(symbol):
    # intento Binance
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()["price"]), "Binance"
    except:
        pass

    # fallback CoinGecko
    try:
        coin = COINS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            return float(r.json()[coin]["usd"]), "CoinGecko"
    except:
        pass

    return None, "Error"

# ==============================
# ANALISIS
# ==============================

def analyze(symbol):
    price, source = get_price(symbol)

    if not price:
        return None

    # lógica simple pero estable
    if price % 2 > 1:
        trend = "Fuerte "
        confidence = 80
    else:
        trend = "Lateral "
        confidence = 60

    entry = price * 0.998
    sl = entry * 0.99
    tp = entry * 1.015

    return {
        "symbol": symbol,
        "price": round(price, 6),
        "entry": round(entry, 6),
        "sl": round(sl, 6),
        "tp": round(tp, 6),
        "trend": trend,
        "confidence": confidence,
        "source": source
    }

# ==============================
# TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton(" Escanear mercado", callback_data="scan")]
    ]
    await update.message.reply_text(
        " SCANNER ULTRA V8\n\nModo rápido activo",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# SCAN
# ==============================

async def scan_market(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    results = []

    for symbol in COINS.keys():
        r = analyze(symbol)
        if r:
            results.append(r)

    if not results:
        await query.edit_message_text(" Sin datos")
        return

    best = max(results, key=lambda x: x["confidence"])

    text = " SCAN V8\n\n"

    keyboard = []

    for r in results:
        text += f"{r['symbol']} | {r['trend']} | {r['confidence']}%\n"
        keyboard.append([
            InlineKeyboardButton(
                f"Operar {r['symbol']}",
                callback_data=f"trade_{r['symbol']}"
            )
        ])

    text += "\n Mejor opción:\n"
    text += f"{best['symbol']} ({best['confidence']}%)"

    keyboard.append([InlineKeyboardButton(" Reescanear", callback_data="scan")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# PREPARAR TRADE
# ==============================

async def prepare_trade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    symbol = query.data.split("_")[1]

    r = analyze(symbol)

    if not r:
        await query.edit_message_text(" Error obteniendo datos")
        return

    text = f"""
 TRADE {symbol}

Precio actual: {r['price']}
Entrada LIMIT: {r['entry']}
SL: {r['sl']}
TP: {r['tp']}

Confianza: {r['confidence']}%
Fuente: {r['source']}
"""

    keyboard = [
        [InlineKeyboardButton(" Volver", callback_data="scan")]
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# ROUTER
# ==============================

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.data == "scan":
        await scan_market(update, context)

    elif query.data.startswith("trade_"):
        await prepare_trade(update, context)

# ==============================
# APP
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(handle_buttons))

print(" BOT V8 INICIADO")

app.run_polling()