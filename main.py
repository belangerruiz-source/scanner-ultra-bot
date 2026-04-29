import os
import json
import math
import requests
from statistics import mean
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# =====================================================
# CONFIG
# =====================================================

TOKEN = os.getenv("TOKEN")
ARCHIVO = "capital.json"

PARES = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]
BASE_URL = "https://api.binance.com/api/v3/klines"

# =====================================================
# CAPITAL
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
# BINANCE DATA
# =====================================================

def obtener_klines(symbol, interval="1h", limit=72):
    params = {
        "symbol": symbol,
        "interval": interval,
        "limit": limit
    }

    r = requests.get(BASE_URL, params=params, timeout=10)
    data = r.json()

    if not isinstance(data, list):
        raise Exception("Sin datos")

    return data


def cierres(klines):
    return [float(x[4]) for x in klines]


# =====================================================
# INDICADORES
# =====================================================

def ema(valores, periodo):
    if len(valores) < periodo:
        return mean(valores)

    k = 2 / (periodo + 1)
    ema_actual = mean(valores[:periodo])

    for precio in valores[periodo:]:
        ema_actual = precio * k + ema_actual * (1 - k)

    return ema_actual


def rsi(valores, periodo=14):
    if len(valores) < periodo + 1:
        return 50

    ganancias = []
    perdidas = []

    for i in range(1, periodo + 1):
        cambio = valores[-i] - valores[-i - 1]

        if cambio >= 0:
            ganancias.append(cambio)
        else:
            perdidas.append(abs(cambio))

    avg_gain = mean(ganancias) if ganancias else 0.0001
    avg_loss = mean(perdidas) if perdidas else 0.0001

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


# =====================================================
# ANALISIS V4.1
# =====================================================

def analizar_par(symbol):
    kl = obtener_klines(symbol, "1h", 72)
    closes = cierres(kl)

    precio = closes[-1]
    minimo = min(closes)
    maximo = max(closes)

    rango = maximo - minimo if maximo != minimo else 0.0001
    posicion = ((precio - minimo) / rango) * 100

    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    valor_rsi = rsi(closes, 14)

    score = 50

    # Tendencia EMA
    if ema9 > ema21:
        score += 18
    else:
        score -= 18

    # RSI
    if 45 <= valor_rsi <= 62:
        score += 12
    elif valor_rsi > 72:
        score -= 10
    elif valor_rsi < 32:
        score += 8

    # Posición en rango 72h
    if posicion < 35:
        score += 15
    elif posicion > 78:
        score -= 15

    # Momentum últimas 3h
    ult3 = closes[-1] - closes[-4]
    if ult3 > 0:
        score += 8
    else:
        score -= 8

    score = max(1, min(score, 99))

    # Clasificación
    if score >= 82:
        estado = "FUERTE 🟢"
        operar = "SÍ"
    elif score >= 70:
        estado = "BUENA 🟡"
        operar = "POSIBLE"
    elif score >= 55:
        estado = "LATERAL ➖"
        operar = "MEJOR ESPERAR"
    else:
        estado = "DÉBIL 🔴"
        operar = "NO"

    tp1 = round(precio * 1.006, 6)
    tp2 = round(precio * 1.011, 6)
    sl = round(precio * 0.994, 6)

    return {
        "symbol": symbol,
        "precio": precio,
        "score": score,
        "estado": estado,
        "operar": operar,
        "rsi": round(valor_rsi, 2),
        "ema9": round(ema9, 6),
        "ema21": round(ema21, 6),
        "posicion": round(posicion, 1),
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl
    }


# =====================================================
# TELEGRAM
# =====================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = """
🤖 SCANNER ULTRA V4.1 PRO

Comandos:

/scan -> mejor oportunidad
/deep -> análisis detallado
/capital 10
/update 12.4
/status
/history
/reset
"""
    await update.message.reply_text(txt)


async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Escaneando mercado profesional...")

    resultados = []

    for par in PARES:
        try:
            resultados.append(analizar_par(par))
        except:
            pass

    if not resultados:
        await update.message.reply_text("❌ Error obteniendo mercado.")
        return

    resultados.sort(key=lambda x: x["score"], reverse=True)
    mejor = resultados[0]

    txt = "📊 SCANNER ULTRA V4.1 PRO\n\n"

    for r in resultados:
        txt += (
            f"{r['symbol']}\n"
            f"{r['estado']} | Score {r['score']}\n"
            f"Precio: {r['precio']:.6f}\n"
            f"Operar: {r['operar']}\n\n"
        )

    txt += "------------------\n"
    txt += f"🏆 Mejor opción: {mejor['symbol']}\n"
    txt += f"Confianza: {mejor['score']}%"

    await update.message.reply_text(txt)


async def deep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📈 Generando análisis profundo...")

    resultados = []

    for par in PARES:
        try:
            resultados.append(analizar_par(par))
        except:
            pass

    if not resultados:
        await update.message.reply_text("❌ Sin datos.")
        return

    resultados.sort(key=lambda x: x["score"], reverse=True)
    r = resultados[0]

    txt = f"""
📌 ANÁLISIS PROFUNDO

Par: {r['symbol']}
Precio: {r['precio']:.6f}

Score: {r['score']}%
Estado: {r['estado']}
Operar: {r['operar']}

RSI: {r['rsi']}
EMA9: {r['ema9']}
EMA21: {r['ema21']}

Posición rango 72h: {r['posicion']}%

🎯 Entrada ideal: {r['precio']:.6f}
TP1: {r['tp1']}
TP2: {r['tp2']}
SL: {r['sl']}
"""
    await update.message.reply_text(txt)


# =====================================================
# CAPITAL COMMANDS
# =====================================================

async def capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usa /capital 10")
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
        f"💰 Capital inicial: {monto} USDT\n🎯 Meta: {data['meta']} USDT"
    )


async def update_capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usa /update 12.5")
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
            f"🎯 Meta {vieja} lograda.\n🚀 Nueva meta: {data['meta']}"
        )
        return

    guardar_data(data)
    await update.message.reply_text(f"✅ Capital actualizado: {monto} USDT")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    if data["capital_inicial"] == 0:
        await update.message.reply_text("Usa /capital primero.")
        return

    ini = data["capital_inicial"]
    act = data["capital_actual"]
    gan = act - ini
    pct = (gan / ini) * 100

    faltan = data["meta"] - act

    txt = f"""
📈 ESTADO CUENTA

Inicial: {ini}
Actual: {act}

Ganancia: {gan:.2f}
Rentabilidad: {pct:.2f}%

🎯 Meta: {data['meta']}
Faltan: {faltan:.2f}
"""
    await update.message.reply_text(txt)


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_data()

    if not data["historial"]:
        await update.message.reply_text("Sin historial.")
        return

    txt = "📜 HISTORIAL\n\n"

    for i, h in enumerate(data["historial"], 1):
        txt += f"{i}. {h} USDT\n"

    await update.message.reply_text(txt)


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if os.path.exists(ARCHIVO):
        os.remove(ARCHIVO)

    await update.message.reply_text("♻️ Cuenta reiniciada.")


# =====================================================
# RUN
# =====================================================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("deep", deep))
app.add_handler(CommandHandler("capital", capital))
app.add_handler(CommandHandler("update", update_capital))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("history", history))
app.add_handler(CommandHandler("reset", reset))

print("SCANNER ULTRA V4.1 PRO ACTIVO")
app.run_polling()