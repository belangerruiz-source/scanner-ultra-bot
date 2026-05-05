import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import json
import statistics

TOKEN = os.getenv("TOKEN")

FILE = "capital.json"

# ==============================
# CAPITAL
# ==============================

def cargar_capital():
    if not os.path.exists(FILE):
        data = {
            "capital": 10.0,
            "meta": 20.0,
            "trades": []
        }
        with open(FILE, "w") as f:
            json.dump(data, f)
    with open(FILE, "r") as f:
        return json.load(f)

def guardar_capital(data):
    with open(FILE, "w") as f:
        json.dump(data, f, indent=2)

# ==============================
# API
# ==============================

def obtener_24h(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        return float(data["lastPrice"]), float(data["priceChangePercent"])
    except:
        return None


def obtener_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=20"
        r = requests.get(url, timeout=5)
        if r.status_code != 200:
            return None
        data = r.json()
        closes = [float(c[4]) for c in data]
        return closes
    except:
        return None

# ==============================
# ANALISIS PRO
# ==============================

def analizar(symbol):
    data_24 = obtener_24h(symbol)
    klines = obtener_klines(symbol)

    if not data_24 or not klines:
        return None

    precio, cambio = data_24

    sma = sum(klines) / len(klines)
    tendencia_corta = (klines[-1] - klines[0]) / klines[0] * 100
    volatilidad = statistics.stdev(klines)

    # CLASIFICACIÓN
    if cambio > 1 and tendencia_corta > 0:
        estado = "Fuerte "
        confianza = 85 + min(int(tendencia_corta), 10)
    elif cambio < -1 and tendencia_corta < 0:
        estado = "Débil "
        confianza = 70
    else:
        estado = "Lateral "
        confianza = 50

    # FILTRO NO OPERAR
    if abs(tendencia_corta) < 0.2:
        return {
            "symbol": symbol,
            "no_operar": True
        }

    # ENTRADA LIMIT INTELIGENTE
    entrada = precio * 0.998  # mejor precio
    sl = entrada * 0.99
    tp = entrada * 1.015

    return {
        "symbol": symbol,
        "precio": round(precio, 6),
        "entrada": round(entrada, 6),
        "estado": estado,
        "cambio": round(cambio, 2),
        "tendencia": round(tendencia_corta, 2),
        "confianza": min(confianza, 99),
        "sl": round(sl, 6),
        "tp": round(tp, 6),
        "no_operar": False
    }

# ==============================
# TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " SCANNER ULTRA V7.2 PRO\n\n"
        "/scan\n"
        "/buy monto precio\n"
        "/sell monto precio\n"
        "/stats"
    )

# ==============================
# SCAN
# ==============================

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Escaneando...")

    pares = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]
    resultados = []

    for p in pares:
        r = analizar(p)
        if r:
            resultados.append(r)

    if not resultados:
        await update.message.reply_text(" Sin datos")
        return

    operables = [r for r in resultados if not r.get("no_operar")]

    texto = " V7.2 PRO\n\n"

    for r in resultados:
        if r.get("no_operar"):
            texto += f"{r['symbol']}  No operar\n"
        else:
            texto += f"{r['symbol']} | {r['estado']} | {r['cambio']}%\n"

    if not operables:
        texto += "\n Ningún trade claro\n"
        await update.message.reply_text(texto)
        return

    mejor = max(operables, key=lambda x: x["confianza"])

    texto += "\n------------------\n"
    texto += f" TRADE: {mejor['symbol']}\n"
    texto += f"Precio actual: {mejor['precio']}\n"
    texto += f"Entrada LIMIT: {mejor['entrada']}\n"
    texto += f"SL: {mejor['sl']}\n"
    texto += f"TP: {mejor['tp']}\n"
    texto += f"Confianza: {mejor['confianza']}%\n"
    texto += f"Tendencia: {mejor['tendencia']}%"

    await update.message.reply_text(texto)

# ==============================
# REGISTRO
# ==============================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio = float(context.args[1])

        data = cargar_capital()

        data["trades"].append({
            "tipo": "buy",
            "monto": monto,
            "precio": precio
        })

        guardar_capital(data)

        await update.message.reply_text(" Compra registrada")

    except:
        await update.message.reply_text(" Uso: /buy monto precio")


async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio = float(context.args[1])

        data = cargar_capital()

        compra = next((t for t in reversed(data["trades"]) if t["tipo"] == "buy"), None)

        if not compra:
            await update.message.reply_text(" No hay compra previa")
            return

        ganancia = monto - compra["monto"]
        data["capital"] += ganancia

        data["trades"].append({
            "tipo": "sell",
            "monto": monto,
            "precio": precio,
            "ganancia": ganancia
        })

        guardar_capital(data)

        await update.message.reply_text(
            f" Ganancia: {round(ganancia,2)} USDT"
        )

    except:
        await update.message.reply_text(" Uso: /sell monto precio")

# ==============================
# STATS
# ==============================

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_capital()

    capital = data["capital"]
    meta = data["meta"]

    await update.message.reply_text(
        f" Capital: {round(capital,2)} USDT\n"
        f"Meta: {meta} USDT\n"
        f"Falta: {round(meta - capital,2)} USDT"
    )

# ==============================
# APP
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("sell", sell))
app.add_handler(CommandHandler("stats", stats))

app.run_polling()