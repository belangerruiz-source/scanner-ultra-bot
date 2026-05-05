import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import os
import json

TOKEN = os.getenv("TOKEN")

# ==============================
# CAPITAL STORAGE
# ==============================

FILE = "capital.json"

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
# API BINANCE (ESTABLE)
# ==============================

def obtener_data(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()

        precio = float(data["lastPrice"])
        cambio = float(data["priceChangePercent"])

        return precio, cambio

    except Exception as e:
        print("ERROR API:", e)
        return None

# ==============================
# ANALISIS
# ==============================

def analizar(symbol):
    data = obtener_data(symbol)

    if not data:
        return None

    precio_actual, cambio = data

    if cambio > 1:
        estado = "Fuerte "
        confianza = 90
    elif cambio < -1:
        estado = "Débil "
        confianza = 70
    else:
        estado = "Lateral "
        confianza = 55

    entrada = precio_actual
    sl = entrada * 0.99
    tp = entrada * 1.015

    return {
        "symbol": symbol,
        "precio": round(entrada, 6),
        "estado": estado,
        "cambio": round(cambio, 2),
        "confianza": confianza,
        "sl": round(sl, 6),
        "tp": round(tp, 6)
    }

# ==============================
# COMANDOS TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " SCANNER ULTRA V7.1 FIX\n\n"
        "Comandos:\n"
        "/scan - Escanear mercado\n"
        "/buy - Registrar compra\n"
        "/sell - Registrar venta\n"
        "/stats - Ver progreso"
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
        else:
            resultados.append({
                "symbol": p,
                "precio": "Error",
                "estado": "Sin datos",
                "cambio": 0,
                "confianza": 0,
                "sl": "-",
                "tp": "-"
            })

    # filtrar válidos
    validos = [r for r in resultados if r["confianza"] > 0]

    if not validos:
        await update.message.reply_text(" No se pudo obtener datos del mercado")
        return

    mejor = max(validos, key=lambda x: x["confianza"])

    texto = " ESCÁNER ULTRA V7.1\n\n"

    for r in resultados:
        texto += f"{r['symbol']} | {r['estado']} | {r['cambio']}%\n"

    texto += "\n------------------\n"
    texto += f" TRADE: {mejor['symbol']}\n"
    texto += f"Entrada: {mejor['precio']}\n"
    texto += f"SL: {mejor['sl']}\n"
    texto += f"TP: {mejor['tp']}\n"
    texto += f"Confianza: {mejor['confianza']}%"

    await update.message.reply_text(texto)

# ==============================
# REGISTRO
# ==============================

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio = float(context.args[1])

        data = cargar_capital()

        trade = {
            "tipo": "buy",
            "monto": monto,
            "precio": precio
        }

        data["trades"].append(trade)
        guardar_capital(data)

        await update.message.reply_text(" Compra registrada")

    except:
        await update.message.reply_text(" Uso: /buy monto precio")

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio = float(context.args[1])

        data = cargar_capital()

        compra = None
        for t in reversed(data["trades"]):
            if t["tipo"] == "buy":
                compra = t
                break

        if not compra:
            await update.message.reply_text(" No hay compra registrada")
            return

        ganancia = monto - compra["monto"]
        data["capital"] += ganancia

        trade = {
            "tipo": "sell",
            "monto": monto,
            "precio": precio,
            "ganancia": ganancia
        }

        data["trades"].append(trade)
        guardar_capital(data)

        await update.message.reply_text(
            f" Venta registrada\nGanancia: {round(ganancia,2)} USDT"
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
        f" PROGRESO\n\n"
        f"Capital: {round(capital,2)} USDT\n"
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