import os
import subprocess
from telegram  import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from dotenv import load_dotenv

load_dotenv()

# token de telegram
TELEGRAM_API_KEY=os.getenv('TELEGRAM_API_KEY')

# handler para comando start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! Soy un bot que analiza proyectos :).")

# handler para comando ayuda
async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ayuda_text = (
        "<b>Comandos disponibles:</b>\n\n"
        "/start - Iniciar el bot\n"
        "/ayuda - Mostrar ayuda\n"
        "/repo &lt;owner/repo&gt; - Analizar repositorio GitHub\n"
        "/local &lt;ruta&gt; - Analizar proyecto local"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=ayuda_text, parse_mode='HTML')

def run_opencode_analysis(repo_url):
    try:
        command = f"opencode init {repo_url} && opencode 'Analiza el siguiente repositorio y hazme un resumen general en archivo .HTML'"
        result = subprocess.run(command, shell=True, capture_output=True, text=True)

        if result.returncode == 0:
            return result.stdout
        return f"Error en oepncode: {result.stderr}"

    except Exception as e:
        return str(e)
# handler para buscar repositorio
async def repo_analisys(update:Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Proporciona la url del repositorio: ")
        return

    repo_url = context.args[0]
    await update.message.reply_text(f"Iniciando analisis del repo: {repo_url}")

    analysis_resultado = run_opencode_analysis(repo_url)

    await update.message.reply_text(f"El resultado final es: {analysis_resultado}")


if __name__ == '__main__':
    # construccion de aplicacion
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # handlers
    start_handler = CommandHandler('start', start)
    ayuda_handler = CommandHandler('ayuda', ayuda)
    analizador_handler = CommandHandler('repo', repo_analisys)
    application.add_handler(start_handler)
    application.add_handler(ayuda_handler)
    application.add_handler(analizador_handler)

    # inicializando el bot
    application.run_polling()