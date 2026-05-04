import requests
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")
DATA_FILE = "capital.json"

# ------------------ UTIL ------------------

def cargar_datos():
    if not os.path.exists(DATA_FILE):
        return {"capital": 10, "objetivo": 20, "operaciones": []}
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def guardar_datos(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def precio(symbol):
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        data = requests.get(url, timeout=5).json()
        return float(data["price"])
    except:
        return None

# ------------------ SCANNER ------------------

def analizar(symbol):
    p1 = precio(symbol)
    p2 = precio(symbol)

    if not p1 or not p2:
        return None

    cambio = ((p2 - p1) / p1) * 100

    if cambio > 0.3:
        estado = "Fuerte 🚀"
        confianza = 90
    elif cambio < -0.3:
        estado = "Débil 📉"
        confianza = 70
    else:
        estado = "Lateral ➖"
        confianza = 50

    entrada = p2
    sl = entrada * 0.985
    tp = entrada * 1.02

    return {
        "symbol": symbol,
        "precio": round(entrada, 6),
        "estado": estado,
        "cambio": round(cambio, 2),
        "confianza": confianza,
        "sl": round(sl, 6),
        "tp": round(tp, 6)
    }

# ------------------ COMANDOS ------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 SCANNER ULTRA V7 PRO\n\n"
        "/scan → Analizar mercado\n"
        "/buy monto precio par\n"
        "/sell monto precio par\n"
        "/capital → Ver estado\n"
        "/stats → Estadísticas\n"
    )

# ------------------ SCAN ------------------

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔎 Escaneando mercado...")

    pares = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]

    resultados = []
    for p in pares:
        r = analizar(p)
        if r:
            resultados.append(r)

    if not resultados:
        await update.message.reply_text("❌ Error obteniendo datos")
        return

    mejor = max(resultados, key=lambda x: x["confianza"])

    texto = "📊 ESCÁNER ULTRA V7\n\n"

    for r in resultados:
        texto += f"{r['symbol']}\n"
        texto += f"{r['precio']} USD | {r['estado']} | {r['cambio']}%\n"
        texto += f"Confianza: {r['confianza']}%\n\n"

    texto += "------------------\n"
    texto += f"🔥 TRADE: {mejor['symbol']}\n"
    texto += f"Entrada: {mejor['precio']}\n"
    texto += f"SL: {mejor['sl']}\n"
    texto += f"TP: {mejor['tp']}\n"
    texto += f"Confianza: {mejor['confianza']}%"

    await update.message.reply_text(texto)

# ------------------ BUY ------------------

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio_compra = float(context.args[1])
        par = context.args[2]

        data = cargar_datos()

        operacion = {
            "tipo": "buy",
            "monto": monto,
            "precio": precio_compra,
            "par": par
        }

        data["operaciones"].append(operacion)
        guardar_datos(data)

        await update.message.reply_text(f"✅ Compra registrada: {par} {monto} USDT")

    except:
        await update.message.reply_text("❌ Uso: /buy monto precio par")

# ------------------ SELL ------------------

async def sell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        monto = float(context.args[0])
        precio_venta = float(context.args[1])
        par = context.args[2]

        data = cargar_datos()

        # buscar última compra
        compra = None
        for op in reversed(data["operaciones"]):
            if op["tipo"] == "buy" and op["par"] == par:
                compra = op
                break

        if not compra:
            await update.message.reply_text("❌ No hay compra previa")
            return

        ganancia = monto - compra["monto"]
        data["capital"] += ganancia

        operacion = {
            "tipo": "sell",
            "monto": monto,
            "precio": precio_venta,
            "par": par,
            "resultado": round(ganancia, 4)
        }

        data["operaciones"].append(operacion)
        guardar_datos(data)

        await update.message.reply_text(
            f"💰 Venta registrada\n"
            f"Resultado: {round(ganancia,4)} USDT\n"
            f"Capital actual: {round(data['capital'],2)} USDT"
        )

    except:
        await update.message.reply_text("❌ Uso: /sell monto precio par")

# ------------------ CAPITAL ------------------

async def capital(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_datos()

    capital_actual = data["capital"]
    objetivo = data["objetivo"]

    await update.message.reply_text(
        f"💼 Capital actual: {round(capital_actual,2)} USDT\n"
        f"🎯 Objetivo: {objetivo} USDT\n"
        f"📈 Progreso: {round((capital_actual/objetivo)*100,2)}%"
    )

# ------------------ STATS ------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_datos()

    wins = 0
    losses = 0

    for op in data["operaciones"]:
        if op.get("resultado"):
            if op["resultado"] > 0:
                wins += 1
            else:
                losses += 1

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0

    await update.message.reply_text(
        f"📊 Estadísticas\n\n"
        f"Operaciones: {total}\n"
        f"Ganadas: {wins}\n"
        f"Perdidas: {losses}\n"
        f"Winrate: {round(winrate,2)}%"
    )

# ------------------ APP ------------------

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("buy", buy))
app.add_handler(CommandHandler("sell", sell))
app.add_handler(CommandHandler("capital", capital))
app.add_handler(CommandHandler("stats", stats))

app.run_polling()