import os

from telegram  import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

from bot.handlers import start, help, list_repos, detail_repo_handler

from dotenv import load_dotenv

load_dotenv()

# token de telegram
TELEGRAM_API_KEY=os.getenv('TELEGRAM_API_KEY')

# orquestacion del bot
if __name__ == '__main__':
    # construccion de aplicacion
    application = ApplicationBuilder().token(TELEGRAM_API_KEY).build()

    # handlers
    start_handler = CommandHandler('start', start)
    ayuda_handler = CommandHandler('ayuda', help)
    list_repos_handler = CommandHandler('listar_repos', list_repos)
    detail_handler = CommandHandler('detalles_repo', detail_repo_handler)

    # anadiendo el handler
    application.add_handler(start_handler)
    application.add_handler(ayuda_handler)
    application.add_handler(list_repos_handler)
    application.add_handler(detail_handler)

    # inicializando el bot
    application.run_polling()