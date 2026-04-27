import os
import json
import requests
from statistics import mean
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =====================================================
# CONFIG
# =====================================================

TOKEN = os.getenv("TOKEN")
ARCHIVO = "capital.json"

PARES = {
    "TRX/USDT": "tron",
    "ADA/USDT": "cardano",
    "DOGE/USDT": "dogecoin"
}

# =====================================================
# UTILIDADES CAPITAL
# =====================================================

def cargar_data():
    if not os.path.exists(ARCHIVO):
        return {
            "capital_inicial": 0,
            "capital_actual": 0,
            "meta": 20,
            "historial": []
        }

    with open(ARCHIVO, "r") as f:
        return json.load(f)


def guardar_data(data):
    with open(ARCHIVO, "w") as f:
        json.dump(data, f)


def siguiente_meta(actual):
    metas = [20, 30, 50, 75, 100, 150, 250, 500]
    for m in metas:
        if actual < m:
            return m
    return actual + 250


# =====================================================
# API PRECIOS
# =====================================================

def precio_y_cambio(coin_id):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "ids": coin_id
    }

    r = requests.get(url, params=params, timeout=10)
    data = r.json()

    if not data:
        raise Exception("Sin datos")

    precio = float(data[0]["current_price"])
    cambio = float(data[0]["price_change_percentage_24h"])

    return precio, cambio


# =====================================================
# ANALISIS SERIO
# =====================================================

def analizar(precio, cambio):
    score = 50

    if cambio > 2:
        score += 25
    elif cambio > 0.5:
        score += 15
    elif cambio < -2:
        score -= 25
    elif cambio < -0.5:
        score -= 15

    if score >= 75:
        tendencia = "Fuerte 🚀"
        señal = "BUY 🟢"
    elif score >= 60:
        tendencia = "Alcista 📈"
        señal = "BUY 🟢"
    elif score >= 45:
        tendencia = "Lateral ➖"
        señal = "WAIT 🟡"
    else:
        tendencia = "Débil 📉"
        señal = "NO TRADE 🔴"

    tp = round(precio * 1.018, 6)
    sl = round(precio * 0.992, 6)

    return {
        "score": score,
        "tendencia": tendencia,
        "senal": señal,
        "tp": tp,
        "sl": sl
    }


# =====================================================
# COMANDOS TELEGRAM
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = """
🤖 ESCÁNER ULTRA V3 SERIO

Comandos:

/scan -> analizar mercado
/capital 10 -> iniciar capital
/update 12.5 -> actualizar capital
/status -> ver progreso
/history -> historial
/reset -> reiniciar cuenta
"""
    await update.message.reply_text(texto)


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Escaneando mercado...")

    resultados = []
    errores = ""

    for par, coin in PARES.items():
        try:
            precio, cambio = precio_y_cambio(coin)
            analisis = analizar(precio, cambio)

            resultados.append({
                "par": par,
                "precio": precio,
                "cambio": cambio,
                **analisis
            })

        except Exception as e:
            errores += f"{par}: {str(e)}\n"

    if not resultados:
        await update.message.reply_text(
            "❌ No se pudo obtener mercado.\n\n" + errores
        )
        return

    resultados.sort(key=lambda x: x["score"], reverse=True)
    mejor = resultados[0]

    texto = "📊 ESCÁNER V3.1\n\n"

    for r in resultados:
        texto += (
            f"{r['par']}\n"
            f"Precio: {r['precio']:.6f}\n"
            f"{r['senal']}\n"
            f"Confianza: {r['score']}%\n\n"
        )

    texto += f"✅ Mejor opción: {mejor['par']}"

    if errores:
        texto += "\n\n⚠️ Errores:\n" + errores

    await update.message.reply_text(texto)
    if not resultados:
        await update.message.reply_text("❌ No se pudo obtener mercado.")
        return

    resultados.sort(key=lambda x: x["score"], reverse=True)
    mejor = resultados[0]

    texto = "📊 ESCÁNER ULTRA V3 SERIO\n\n"

    for r in resultados:
        texto += (
            f"{r['par']}\n"
            f"Precio: {r['precio']:.6f}\n"
            f"{r['tendencia']} | {r['cambio']:.2f}%\n"
            f"Señal: {r['senal']}\n"
            f"TP: {r['tp']}\n"
            f"SL: {r['sl']}\n"
            f"Confianza: {r['score']}%\n\n"
        )

    texto += "------------------\n"
    texto += f"✅ Mejor opción: {mejor['par']}\n"
    texto += f"Señal: {mejor['senal']}"

    await update.message.reply_text(texto)


async def capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usa: /capital 10")
        return

    monto = float(context.args[0])

    data = {
        "capital_inicial": monto,
        "capital_actual": monto,
        "meta": siguiente_meta(monto),
        "historial": [monto]
    }

    guardar_data(data)

    await update.message.reply_text(
        f"💰 Capital iniciado en {monto} USDT\n🎯 Meta actual: {data['meta']} USDT"
    )


async def update_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usa: /update 12.5")
        return

    monto = float(context.args[0])
    data = cargar_data()

    data["capital_actual"] = monto
    data["historial"].append(monto)

    if monto >= data["meta"]:
        vieja = data["meta"]
        data["meta"] = siguiente_meta(monto)

        guardar_data(data)

        await update.message.reply_text(
            f"🎯 Meta {vieja} alcanzada!\n🚀 Nueva meta: {data['meta']} USDT"
        )
        return

    guardar_data(data)

    await update.message.reply_text(
        f"✅ Capital actualizado: {monto} USDT"
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    actual = data["capital_actual"]
    inicial = data["capital_inicial"]

    if inicial == 0:
        await update.message.reply_text("Primero usa /capital")
        return

    ganancia = actual - inicial
    porcentaje = (ganancia / inicial) * 100

    faltan = data["meta"] - actual

    texto = (
        f"📈 ESTADO CUENTA\n\n"
        f"Inicial: {inicial} USDT\n"
        f"Actual: {actual} USDT\n"
        f"Ganancia: {ganancia:.2f} ({porcentaje:.2f}%)\n\n"
        f"🎯 Meta actual: {data['meta']} USDT\n"
        f"Faltan: {faltan:.2f} USDT"
    )

    await update.message.reply_text(texto)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    if not data["historial"]:
        await update.message.reply_text("Sin historial.")
        return

    texto = "📜 HISTORIAL CAPITAL\n\n"

    for i, v in enumerate(data["historial"], start=1):
        texto += f"{i}. {v} USDT\n"

    await update.message.reply_text(texto)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(ARCHIVO):
        os.remove(ARCHIVO)

    await update.message.reply_text("♻️ Cuenta reiniciada.")


# =====================================================
# APP
# =====================================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("capital", capital))
app.add_handler(CommandHandler("update", update_capital))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("reset", reset))

print("BOT V3 SERIO ACTIVO")
app.run_polling()