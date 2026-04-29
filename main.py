# main.py
# ESCÁNER ULTRA V4.1 PRO - FIX ESTABLE
# Telegram + CoinGecko + análisis 72h

import requests
import os
import json
import statistics
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

TOKEN = os.getenv("TOKEN")

# =========================
# CONFIG
# =========================
PAIRS = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

CAPITAL_FILE = "capital.json"


# =========================
# CAPITAL
# =========================
def cargar_capital():
    try:
        with open(CAPITAL_FILE, "r") as f:
            return json.load(f)
    except:
        data = {
            "capital": 10.0,
            "meta": 20.0
        }
        guardar_capital(data)
        return data


def guardar_capital(data):
    with open(CAPITAL_FILE, "w") as f:
        json.dump(data, f)


# =========================
# API
# =========================
def precio_actual(coin_id):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd"
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return float(data[coin_id]["usd"])
    except:
        return None


def historial_72h(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": 3,
            "interval": "hourly"
        }

        r = requests.get(url, params=params, timeout=15)
        data = r.json()

        precios = [x[1] for x in data["prices"]]
        return precios

    except:
        return []


# =========================
# ANALISIS
# =========================
def analizar(coin_id):
    actual = precio_actual(coin_id)
    hist = historial_72h(coin_id)

    if actual is None or len(hist) < 10:
        return None

    prom = statistics.mean(hist[-24:])
    minimo = min(hist[-24:])
    maximo = max(hist[-24:])

    cambio = ((actual - hist[-2]) / hist[-2]) * 100

    volatilidad = ((maximo - minimo) / minimo) * 100

    score = 0

    # precio sobre promedio
    if actual > prom:
        score += 25
    else:
        score -= 15

    # impulso
    if cambio > 0:
        score += 25
    else:
        score -= 15

    # volatilidad útil
    if volatilidad > 2:
        score += 20

    # cerca del mínimo = buena entrada
    rango = (actual - minimo) / (maximo - minimo + 0.0000001)

    if rango < 0.35:
        score += 25
    elif rango > 0.75:
        score -= 20

    confianza = max(50, min(96, 50 + score))

    if confianza >= 80:
        estado = "Fuerte 🚀"
    elif confianza >= 68:
        estado = "Moderado 📈"
    else:
        estado = "Lateral ➖"

    sl = round(actual * 0.985, 6)
    tp = round(actual * 1.018, 6)

    return {
        "precio": actual,
        "estado": estado,
        "confianza": confianza,
        "sl": sl,
        "tp": tp,
        "cambio": round(cambio, 2)
    }


# =========================
# BOT
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "ESCÁNER ULTRA V4.1 PRO ACTIVO\n\n"
        "/scan = escanear\n"
        "/capital = ver capital\n"
        "/sumar 2.5 = añadir ganancia\n"
        "/restar 1 = pérdida"
    )


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Escaneando mercado...")

    resultados = []

    texto = "ESCÁNER ULTRA V4.1 PRO\n\n"

    for pair, coin_id in PAIRS.items():
        r = analizar(coin_id)

        if r:
            texto += (
                f"{pair}\n"
                f"{r['precio']:.6f} USD | {r['estado']} | {r['cambio']}%\n"
                f"Confianza: {r['confianza']}%\n\n"
            )
            resultados.append((pair, r))
        else:
            texto += f"{pair}: Error\n\n"

    if resultados:
        mejor = max(resultados, key=lambda x: x[1]["confianza"])

        pair = mejor[0]
        r = mejor[1]

        texto += (
            "------------------\n"
            f"✅ Mejor opción: {pair}\n"
            f"Entrada: {r['precio']:.6f}\n"
            f"SL: {r['sl']:.6f}\n"
            f"TP: {r['tp']:.6f}\n"
            f"Confianza: {r['confianza']}%"
        )

    await update.message.reply_text(texto)


async def capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_capital()

    await update.message.reply_text(
        f"Capital actual: {data['capital']} USDT\n"
        f"Meta actual: {data['meta']} USDT"
    )


async def sumar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        data = cargar_capital()

        data["capital"] += valor

        if data["capital"] >= data["meta"]:
            data["meta"] += 10

        guardar_capital(data)

        await update.message.reply_text(
            f"Nuevo capital: {round(data['capital'],2)} USDT\n"
            f"Nueva meta: {data['meta']} USDT"
        )
    except:
        await update.message.reply_text("Usa: /sumar 2.5")


async def restar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(context.args[0])
        data = cargar_capital()

        data["capital"] -= valor
        guardar_capital(data)

        await update.message.reply_text(
            f"Capital actual: {round(data['capital'],2)} USDT"
        )
    except:
        await update.message.reply_text("Usa: /restar 1")


# =========================
# RUN
# =========================
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("capital", capital))
app.add_handler(CommandHandler("sumar", sumar))
app.add_handler(CommandHandler("restar", restar))

print("BOT V4.1 PRO ONLINE")
app.run_polling()