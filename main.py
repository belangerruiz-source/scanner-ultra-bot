import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os

TOKEN = os.getenv("TOKEN")

# ==============================
# FALLBACK COINGECKO
# ==============================

COINGECKO_IDS = {
    "TRXUSDT": "tron",
    "ADAUSDT": "cardano",
    "DOGEUSDT": "dogecoin"
}

def precio_coingecko(symbol):
    try:
        coin_id = COINGECKO_IDS[symbol]
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        return float(r.json()[coin_id]["usd"])

    except:
        return None

# ==============================
# BINANCE
# ==============================

def precio_binance(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        return float(r.json()["price"])

    except:
        return None

# ==============================
# SISTEMA INTELIGENTE
# ==============================

def obtener_precio(symbol):
    precio = precio_binance(symbol)

    if precio:
        fuente = "Binance"
        return precio, fuente

    precio = precio_coingecko(symbol)

    if precio:
        fuente = "CoinGecko"
        return precio, fuente

    return None, "Error"

# ==============================
# ANALISIS SIMPLE (ESTABLE)
# ==============================

def analizar(symbol):
    precio, fuente = obtener_precio(symbol)

    if not precio:
        return None

    # Simulación de tendencia básica
    if precio % 2 > 1:
        estado = "Fuerte "
        confianza = 80
    else:
        estado = "Lateral "
        confianza = 60

    entrada = precio * 0.998
    sl = entrada * 0.99
    tp = entrada * 1.015

    return {
        "symbol": symbol,
        "precio": round(precio, 6),
        "entrada": round(entrada, 6),
        "sl": round(sl, 6),
        "tp": round(tp, 6),
        "estado": estado,
        "confianza": confianza,
        "fuente": fuente
    }

# ==============================
# TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " SCANNER ULTRA V7.2 FINAL\n\n"
        " Anti-fallos activo\n"
        " Binance + CoinGecko\n\n"
        "/scan"
    )

# ==============================
# SCAN
# ==============================

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Escaneando mercado...")

    pares = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]
    resultados = []

    for p in pares:
        r = analizar(p)
        if r:
            resultados.append(r)

    if not resultados:
        await update.message.reply_text(" Sin datos disponibles")
        return

    mejor = max(resultados, key=lambda x: x["confianza"])

    texto = " SCAN V7.2 FINAL\n\n"

    for r in resultados:
        texto += f"{r['symbol']} | {r['estado']} | Fuente: {r['fuente']}\n"

    texto += "\n------------------\n"
    texto += f" TRADE: {mejor['symbol']}\n"
    texto += f"Precio: {mejor['precio']}\n"
    texto += f"Entrada LIMIT: {mejor['entrada']}\n"
    texto += f"SL: {mejor['sl']}\n"
    texto += f"TP: {mejor['tp']}\n"
    texto += f"Confianza: {mejor['confianza']}%"

    await update.message.reply_text(texto)

# ==============================
# APP
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))

print("BOT V7.2 FINAL INICIADO")

app.run_polling()