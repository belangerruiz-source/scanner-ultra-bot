import requests
import asyncio
import json
import os
from statistics import mean
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.getenv("TOKEN")

PARES = ["TRXUSDT", "ADAUSDT", "DOGEUSDT"]

STATE_FILE = "estado.json"

# ==============================
# ESTADO BOT
# ==============================

def cargar_estado():
    if not os.path.exists(STATE_FILE):
        data = {"activo": False}
        guardar_estado(data)
        return data
    with open(STATE_FILE, "r") as f:
        return json.load(f)

def guardar_estado(data):
    with open(STATE_FILE, "w") as f:
        json.dump(data, f)

# ==============================
# BINANCE DATA
# ==============================

def get_klines(symbol):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=30"
        r = requests.get(url, timeout=5)

        if r.status_code != 200:
            return None

        data = r.json()
        closes = [float(candle[4]) for candle in data]
        return closes
    except:
        return None

# ==============================
# ANALISIS
# ==============================

def analizar(closes):
    actual = closes[-1]
    promedio = mean(closes[-10:])
    cambio = ((actual - promedio) / promedio) * 100

    if cambio > 1:
        estado = "Fuerte "
        confianza = min(95, int(abs(cambio) * 40))
    elif cambio < -1:
        estado = "Débil "
        confianza = min(95, int(abs(cambio) * 40))
    else:
        estado = "Lateral "
        confianza = 50

    return estado, cambio, confianza, actual

# ==============================
# SCAN LOGICA
# ==============================

def scan_market():
    resultados = []
    mejor = None

    for par in PARES:
        closes = get_klines(par)

        if closes is None:
            continue

        estado, cambio, confianza, precio = analizar(closes)
        resultados.append((par, estado, cambio, confianza, precio))

        if mejor is None or confianza > mejor[3]:
            mejor = (par, estado, cambio, confianza, precio)

    if mejor and mejor[1] != "Lateral ":
        entrada = mejor[4]
        sl = entrada * 0.992
        tp = entrada * 1.008

        return {
            "par": mejor[0],
            "entrada": entrada,
            "sl": sl,
            "tp": tp,
            "confianza": mejor[3]
        }

    return None

# ==============================
# LOOP AUTOMATICO
# ==============================

async def auto_scan(app):
    while True:
        estado = cargar_estado()

        if estado["activo"]:
            print("Escaneando automático...")

            trade = scan_market()

            if trade:
                mensaje = (
                    f" TRADE DETECTADO\n\n"
                    f"{trade['par']}\n"
                    f"Entrada: {trade['entrada']:.6f}\n"
                    f"SL: {trade['sl']:.6f}\n"
                    f"TP: {trade['tp']:.6f}\n"
                    f"Confianza: {trade['confianza']}%"
                )

                # enviar a TODOS los chats activos
                if "chats" in estado:
                    for chat_id in estado["chats"]:
                        await app.bot.send_message(chat_id=chat_id, text=mensaje)

        await asyncio.sleep(1800)  # 30 minutos

# ==============================
# COMANDOS TELEGRAM
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = cargar_estado()

    chat_id = update.effective_chat.id

    if "chats" not in estado:
        estado["chats"] = []

    if chat_id not in estado["chats"]:
        estado["chats"].append(chat_id)
        guardar_estado(estado)

    await update.message.reply_text(
        " BOT AUTO SCAN\n\n"
        "/activar\n"
        "/desactivar\n"
        "/status"
    )

async def activar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = cargar_estado()
    estado["activo"] = True
    guardar_estado(estado)

    await update.message.reply_text(" Auto-scan ACTIVADO")

async def desactivar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = cargar_estado()
    estado["activo"] = False
    guardar_estado(estado)

    await update.message.reply_text(" Auto-scan DESACTIVADO")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    estado = cargar_estado()
    estado_txt = "ACTIVO" if estado["activo"] else "INACTIVO"

    await update.message.reply_text(f"Estado: {estado_txt}")

# ==============================
# APP
# ==============================

async def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("activar", activar))
    app.add_handler(CommandHandler("desactivar", desactivar))
    app.add_handler(CommandHandler("status", status))

    # iniciar loop automático
    app.create_task(auto_scan(app))

    print("BOT CLOUD CORRIENDO...")
    await app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())