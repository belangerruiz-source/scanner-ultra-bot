# main.py
# SCANNER ULTRA V6.2 PRO (ESTABLE + FALLBACK)

import requests
import os
import json
import statistics
from datetime import datetime

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters
)

TOKEN = os.getenv("TOKEN")

PAIRS = {
    "TRX/USDT": ("tron", "TRXUSDT"),
    "ADA/USDT": ("cardano", "ADAUSDT"),
    "DOGE/USDT": ("dogecoin", "DOGEUSDT")
}

DATA_FILE = "data.json"

# =========================
# DATA
# =========================
def cargar_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        data = {
            "capital": 10.0,
            "meta": 20.0,
            "operaciones": [],
            "bloqueado": False
        }
        guardar_data(data)
        return data


def guardar_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# API
# =========================
def precio_coingecko(coin_id):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        r = requests.get(url, params={"ids": coin_id, "vs_currencies": "usd"}, timeout=15)

        if r.status_code != 200:
            print("CoinGecko error:", r.text)
            return None

        data = r.json()
        return float(data[coin_id]["usd"])
    except Exception as e:
        print("Error CoinGecko:", e)
        return None


def precio_binance(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            print("Binance error:", r.text)
            return None

        return float(r.json()["price"])
    except Exception as e:
        print("Error Binance:", e)
        return None


def historial_24h(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        r = requests.get(url, params={
            "vs_currency": "usd",
            "days": 1,
            "interval": "hourly"
        }, timeout=15)

        data = r.json()

        if "prices" not in data:
            print("Historial error:", data)
            return []

        return [x[1] for x in data["prices"]]
    except Exception as e:
        print("Error historial:", e)
        return []


# =========================
# ANALISIS
# =========================
def analizar(pair, coin_id, symbol):

    precio = precio_coingecko(coin_id)

    # fallback
    if precio is None:
        precio = precio_binance(symbol)

    hist = historial_24h(coin_id)

    if precio is None or len(hist) < 10:
        return None

    prom = statistics.mean(hist[-12:])
    minimo = min(hist[-12:])
    maximo = max(hist[-12:])
    cambio = ((precio - hist[-2]) / hist[-2]) * 100
    volatilidad = ((maximo - minimo) / minimo) * 100

    score = 0

    if precio > prom:
        score += 25
    else:
        score -= 10

    if cambio > 0:
        score += 25
    else:
        score -= 10

    if volatilidad > 1:
        score += 15

    rango = (precio - minimo) / (maximo - minimo + 1e-9)

    if rango < 0.4:
        score += 20
    elif rango > 0.75:
        score -= 20

    confianza = max(50, min(95, 50 + score))

    if confianza >= 80:
        decision = "ENTRAR"
    elif confianza >= 65:
        decision = "ESPERAR"
    else:
        decision = "NO OPERAR"

    entrada = precio * 0.995 if decision == "ENTRAR" else None
    sl = entrada * 0.985 if entrada else None
    tp = entrada * 1.02 if entrada else None

    return {
        "precio": precio,
        "confianza": confianza,
        "decision": decision,
        "entrada": round(entrada, 6) if entrada else None,
        "sl": round(sl, 6) if sl else None,
        "tp": round(tp, 6) if tp else None,
        "cambio": round(cambio, 2)
    }


# =========================
# MENU
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    teclado = [
        ["🔍 Escanear"],
        ["💰 Operar", "📊 Resumen"],
        ["🔓 Reset"]
    ]

    reply_markup = ReplyKeyboardMarkup(teclado, resize_keyboard=True)

    await update.message.reply_text(
        "🤖 Scanner Ultra V6.2 PRO\n\nSelecciona una opción:",
        reply_markup=reply_markup
    )


# =========================
# SCAN
# =========================
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = cargar_data()

    if data["bloqueado"]:
        await update.message.reply_text("🚫 Bloqueado por pérdidas")
        return

    await update.message.reply_text("Escaneando mercado...")

    resultados = []

    for pair, (coin_id, symbol) in PAIRS.items():
        r = analizar(pair, coin_id, symbol)
        if r:
            resultados.append((pair, r))

    if not resultados:
        await update.message.reply_text("❌ Error en datos de mercado")
        return

    resultados.sort(key=lambda x: x[1]["confianza"], reverse=True)

    texto = "📊 ESCÁNER V6.2 PRO\n\n"

    for pair, r in resultados:
        texto += f"{pair} | {r['decision']} | {r['confianza']}%\n"

    mejor = resultados[0]
    pair, r = mejor

    if r["decision"] == "ENTRAR":
        texto += (
            "\n------------------\n"
            f"🔥 TRADE: {pair}\n\n"
            f"Entrada: {r['entrada']}\n"
            f"SL: {r['sl']}\n"
            f"TP: {r['tp']}\n"
            f"Confianza: {r['confianza']}%"
        )
    else:
        texto += "\n⚠️ No operar"

    await update.message.reply_text(texto)


# =========================
# OPERAR
# =========================
async def operar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usa: /operar 1.5")


async def operar_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = cargar_data()

    if data["bloqueado"]:
        await update.message.reply_text("🚫 Bloqueado")
        return

    try:
        monto = float(context.args[0])
        riesgo = data["capital"] * 0.05

        if monto > riesgo:
            await update.message.reply_text(f"Máximo recomendado: {round(riesgo,2)}")
            return

        op = {
            "fecha": str(datetime.now()),
            "monto": monto,
            "resultado": "pendiente"
        }

        data["operaciones"].append(op)
        guardar_data(data)

        await update.message.reply_text("Operación registrada")

    except:
        await update.message.reply_text("Formato incorrecto")


# =========================
# RESULTADOS
# =========================
async def win(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    for op in reversed(data["operaciones"]):
        if op["resultado"] == "pendiente":
            data["capital"] += op["monto"] * 0.02
            op["resultado"] = "ganada"
            break

    data["bloqueado"] = False
    guardar_data(data)

    await update.message.reply_text(f"✅ Capital: {round(data['capital'],2)}")


async def loss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    consecutivas = 0

    for op in reversed(data["operaciones"]):
        if op["resultado"] == "pendiente":
            data["capital"] -= op["monto"] * 0.015
            op["resultado"] = "perdida"
            break

    for op in reversed(data["operaciones"]):
        if op["resultado"] == "perdida":
            consecutivas += 1
        else:
            break

    if consecutivas >= 2:
        data["bloqueado"] = True

    guardar_data(data)

    await update.message.reply_text(f"❌ Capital: {round(data['capital'],2)}")


# =========================
# RESET Y RESUMEN
# =========================
async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()
    data["bloqueado"] = False
    guardar_data(data)
    await update.message.reply_text("🔓 Desbloqueado")


async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    ganadas = sum(1 for op in data["operaciones"] if op["resultado"] == "ganada")
    perdidas = sum(1 for op in data["operaciones"] if op["resultado"] == "perdida")

    await update.message.reply_text(
        f"Capital: {data['capital']} USDT\n"
        f"Meta: {data['meta']} USDT\n"
        f"Ganadas: {ganadas}\n"
        f"Perdidas: {perdidas}\n"
        f"Bloqueado: {data['bloqueado']}"
    )


# =========================
# MENU HANDLER
# =========================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):

    texto = update.message.text

    if texto == "🔍 Escanear":
        await scan(update, context)

    elif texto == "💰 Operar":
        await operar(update, context)

    elif texto == "📊 Resumen":
        await resumen(update, context)

    elif texto == "🔓 Reset":
        await reset(update, context)


# =========================
# RUN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("operar", operar_cmd))
app.add_handler(CommandHandler("win", win))
app.add_handler(CommandHandler("loss", loss))
app.add_handler(CommandHandler("resumen", resumen))
app.add_handler(CommandHandler("reset", reset))

app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu))

print("BOT V6.2 PRO ACTIVO")
app.run_polling()