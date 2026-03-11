from telegram.ext import ApplicationBuilder, CommandHandler
import requests

TOKEN = "TOKEN"

async def investigate(update,context):

    target = context.args[0]

    r = requests.get(f"https://SEUDEPLOY.vercel.app/api/investigate?target={target}")

    await update.message.reply_text(r.text)

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("investigar",investigate))

app.run_polling()
