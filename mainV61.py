# main.py
# SCANNER ULTRA V6.1 PRO (CON MENÚ)

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
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
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
def precio_actual(coin_id):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        r = requests.get(url, params={"ids": coin_id, "vs_currencies": "usd"}, timeout=10)
        return float(r.json()[coin_id]["usd"])
    except:
        return None


def historial_72h(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        r = requests.get(url, params={
            "vs_currency": "usd",
            "days": 3,
            "interval": "hourly"
        }, timeout=15)

        return [x[1] for x in r.json()["prices"]]
    except:
        return []


# =========================
# ANALISIS
# =========================
def analizar(coin_id):

    precio = precio_actual(coin_id)
    hist = historial_72h(coin_id)

    if precio is None or len(hist) < 10:
        return None

    prom = statistics.mean(hist[-24:])
    minimo = min(hist[-24:])
    maximo = max(hist[-24:])
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

    if volatilidad > 2:
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
        "🤖 Scanner Ultra V6.1\n\nSelecciona una opción:",
        reply_markup=reply_markup
    )


# =========================
# SCAN
# =========================
async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):

    data = cargar_data()

    if data["bloqueado"]:
        await update.message.reply_text("🚫 Bloqueado por pérdidas. Usa Reset")
        return

    await update.message.reply_text("Escaneando mercado...")

    resultados = []

    for pair, coin_id in PAIRS.items():
        r = analizar(coin_id)
        if r:
            resultados.append((pair, r))

    if not resultados:
        await update.message.reply_text("Error en datos")
        return

    resultados.sort(key=lambda x: x[1]["confianza"], reverse=True)

    texto = "📊 ESCÁNER V6.1\n\n"

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
        texto += "\n⚠️ No operar ahora"

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
        await update.message.reply_text("Error en formato")


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

print("BOT V6.1 PRO ACTIVO")
app.run_polling()