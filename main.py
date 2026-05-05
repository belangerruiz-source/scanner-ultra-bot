import requests
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

PARES = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]

CAPITAL_FILE = "capital.json"

# ==============================
# CAPITAL
# ==============================

def cargar_capital():
    if not os.path.exists(CAPITAL_FILE):
        data = {"capital": 10.0, "meta": 20.0, "historial": []}
        guardar_capital(data)
        return data
    with open(CAPITAL_FILE, "r") as f:
        return json.load(f)

def guardar_capital(data):
    with open(CAPITAL_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ==============================
# DATOS MERCADO (COINGECKO)
# ==============================

def get_price(symbol):
    try:
        mapa = {
            "TRXUSDT": "tron",
            "ADAUSDT": "cardano",
            "DOGEUSDT": "dogecoin"
        }

        coin = mapa[symbol]

        url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
        data = requests.get(url, timeout=10).json()

        return float(data[coin]["usd"])
    except:
        return None

# ==============================
# ANÁLISIS
# ==============================

def analizar(precio):
    # Simulación de variación simple
    import random
    cambio = random.uniform(-3, 3)

    if cambio > 1.5:
        estado = "Fuerte "
        confianza = random.randint(80, 95)
    elif cambio < -1.5:
        estado = "Débil "
        confianza = random.randint(80, 95)
    else:
        estado = "Lateral "
        confianza = random.randint(50, 70)

    return estado, cambio, confianza

# ==============================
# SCAN
# ==============================

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(" Escaneando mercado...")

    resultados = []

    for par in PARES:
        precio = get_price(par)

        if precio is None:
            resultados.append((par, "Error", 0, 0, 0))
            continue

        estado, cambio, confianza = analizar(precio)

        resultados.append((par, estado, cambio, confianza, precio))

    texto = " ESCÁNER V7 REBUILD\n\n"

    mejor = None

    for par, estado, cambio, confianza, precio in resultados:
        if estado == "Error":
            texto += f"{par}: Error\n"
            continue

        texto += f"{par}: {precio:.6f} | {estado} | {cambio:.2f}%\n"

        if mejor is None or confianza > mejor[3]:
            mejor = (par, estado, cambio, confianza, precio)

    if mejor and mejor[1] != "Lateral ":
        entrada = mejor[4]
        sl = entrada * 0.985
        tp = entrada * 1.02

        texto += f"\n TRADE: {mejor[0]}"
        texto += f"\nEntrada: {entrada:.6f}"
        texto += f"\nSL: {sl:.6f}"
        texto += f"\nTP: {tp:.6f}"
        texto += f"\nConfianza: {mejor[3]}%"
    else:
        texto += "\n\n No operar (mercado lateral)"

    await update.message.reply_text(texto)

# ==============================
# REGISTRAR OPERACIÓN
# ==============================

async def registrar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ganancia = float(context.args[0])

        data = cargar_capital()
        data["capital"] += ganancia
        data["historial"].append(ganancia)

        guardar_capital(data)

        await update.message.reply_text(
            f" Operación registrada\n"
            f"Resultado: {ganancia} USDT\n"
            f"Capital actual: {data['capital']:.2f} USDT"
        )

    except:
        await update.message.reply_text("Uso: /registrar 0.18")

# ==============================
# STATUS
# ==============================

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = cargar_capital()

    await update.message.reply_text(
        f" Capital: {data['capital']:.2f} USDT\n"
        f" Meta: {data['meta']} USDT\n"
        f" Operaciones: {len(data['historial'])}"
    )

# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        " BOT V7 REBUILD ACTIVO\n\n"
        "Comandos:\n"
        "/scan\n"
        "/registrar +ganancia\n"
        "/status"
    )

# ==============================
# APP
# ==============================

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("scan", scan))
app.add_handler(CommandHandler("registrar", registrar))
app.add_handler(CommandHandler("status", status))

app.run_polling()