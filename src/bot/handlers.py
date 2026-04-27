from telegram import Update
from telegram.ext import ContextTypes
from services.analyzer import list_repo_user, detail_repo
from agent.agent import mistral_model
from tools.format_scape import escape_markdown

# handler para comando start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="¡Hola! Soy un bot que analiza proyectos :).")

# handler para comando ayuda
async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ayuda_text = (
        "<b>Comandos disponibles:</b>\n\n"
        "/start - Iniciar el bot\n"
        "/ayuda - Mostrar ayuda\n"
        "/listar_repos - Mostrar repositorios de usuario\n"
        "/detalles_repo - Mostrar detalles de repositorio"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=ayuda_text, parse_mode='HTML')

async def detail_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Por favor, ingresa el nombre de usuario y el repositorio de GitHub después del comando.\n Ejemplo: `/detalles_repo aidam sistemagym`",
            parse_mode='MarkdownV2'
        )
        return

    username = context.args[0]
    repository = context.args[1]
    
    try:
        repo_data = detail_repo(username, repository)
        
        response_model = mistral_model()
        formatted_response = escape_markdown(response_model)

        # Telegram tiene un límite de 4096 caracteres por mensaje.
        # Si la respuesta es más larga, la dividimos en partes.
        MAX_LENGTH = 4096
        if len(formatted_response) > MAX_LENGTH:
            for i in range(0, len(formatted_response), MAX_LENGTH):
                part = formatted_response[i:i + MAX_LENGTH]
                await context.bot.send_message(chat_id=update.effective_chat.id, text=part, parse_mode='MarkdownV2')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=formatted_response, parse_mode='MarkdownV2')

    except Exception as e:
        print(f"Error: {e}")
        error_message = f"No se pudo encontrar al usuario <b>{username}</b> o al repositorio: <b>{repository}</b>, quizás hubo un error con la API de GitHub."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message, parse_mode='HTML')


# handler para listar repositorioos
async def list_repos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text="Por favor, ingresa el nombre de usuario de GitHub después del comando.\nEjemplo: <code>/listar_repos aidam</code>",
            parse_mode='HTML'
        )
        return

    username = context.args[0]
    
    try: 
        repos = list_repo_user(username)

        if repos:
            message = f"<b>Repositorios de {username}:</b>\n\n" + "\n".join([f"- {repo}" for repo in repos])
        else:
            message = f"El usuario <b>{username}</b> no tiene repositorios públicos."

        await context.bot.send_message(chat_id=update.effective_chat.id, text=message, parse_mode='HTML')
    except Exception as e:
        error_message = f"No se pudo encontrar al usuario <b>{username}</b> o hubo un error con la API de GitHub."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message, parse_mode='HTML')
        print(f"Error: {e}")