import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)
import os

TOKEN = os.getenv("TOKEN")

# ==============================
# TEST SIMPLE
# ==============================

def get_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/ping", timeout=5)
        return r.status_code == 200
    except:
        return False

# ==============================
# START
# ==============================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("START ejecutado")

    keyboard = [
        [InlineKeyboardButton(" Escanear", callback_data="scan")]
    ]

    await update.message.reply_text(
        " BOT V8.1 ACTIVO\nPulsa el botón",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ==============================
# BOTONES
# ==============================

async def botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    print("BOTÓN:", query.data)

    if query.data == "scan":

        ok = get_price()

        if ok:
            texto = " API funcionando\n\nTRX: OK\nADA: OK\nDOGE: OK"
        else:
            texto = " API FALLANDO\n(Revisa Railway/red)"

        keyboard = [
            [InlineKeyboardButton(" Reintentar", callback_data="scan")]
        ]

        await query.edit_message_text(
            texto,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ==============================
# APP
# ==============================

print("INICIANDO BOT...")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(botones))

print("BOT LISTO")

app.run_polling()