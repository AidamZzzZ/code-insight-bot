from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.analyzer import list_repo_user, detail_repo, get_readme, get_repo_structure
from services.path_searcher import list_projects, BASE_DIR, get_local_readme, get_local_structure, get_local_languages
from agent.agent import mistral_model, generate_html_manual
import os
import tempfile
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
        "/detalles_repo - Mostrar detalles de repositorio\n"
        "/analizar_local - Mostrar de projectos locales"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=ayuda_text, parse_mode='HTML')

async def detail_repo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Por favor, ingresa el nombre de usuario y el repositorio de GitHub después del comando.\n Ejemplo: /detalles_repo <b>usuario</b> <b>repositorio</b>",
            parse_mode='HTML'
        )
        return

    username = context.args[0]
    repository = context.args[1]
    
    try:
        repo_data = detail_repo(username, repository)
        readme = get_readme(username, repository)
        structure = get_repo_structure(username, repository)
        
        # Guardamos la información en user_data para el callback de HTML
        context.user_data['current_repo'] = {
            'username': username,
            'repository': repository,
            'data': repo_data
        }

        prompt = f"""Analiza el siguiente repositorio de GitHub y desarrolla un informe estructurado.
        
        INFORMACIÓN DEL PROYECTO:
        - Nombre: {repo_data.get('name', repository)}
        - Descripción: {repo_data.get('description', 'Sin descripción')}
        - Estrellas: {repo_data.get('stars', 0)} | Forks: {repo_data.get('forks', 0)}
        - Lenguajes: {', '.join(repo_data.get('list_languages', []))}
        - URL: {repo_data.get('url', '')}
        
        ESTRUCTURA DEL REPOSITORIO (primeros archivos):
        {structure}
        
        README (resumen):
        {readme[:2000]}
        
        Usa esta información para generar un análisis preciso y detallado del repositorio.
        Asegúrate de formatear la respuesta correctamente en Markdown.
        """
        
        response_model = mistral_model(prompt)
        formatted_response = escape_markdown(response_model)

        # Telegram tiene un límite de 4096 caracteres por mensaje.
        # Si la respuesta es más larga, la dividimos por párrafos para no romper el Markdown.
        MAX_LENGTH = 4000
        if len(formatted_response) > MAX_LENGTH:
            paragraphs = formatted_response.split('\n\n')
            current_message = ""
            for p in paragraphs:
                # Si un solo párrafo es más grande que MAX_LENGTH, lo cortamos (caso extremo)
                if len(p) > MAX_LENGTH:
                    if current_message:
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=current_message, parse_mode='MarkdownV2')
                        current_message = ""
                    for i in range(0, len(p), MAX_LENGTH):
                        await context.bot.send_message(chat_id=update.effective_chat.id, text=p[i:i+MAX_LENGTH], parse_mode='MarkdownV2')
                elif len(current_message) + len(p) + 2 > MAX_LENGTH:
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=current_message, parse_mode='MarkdownV2')
                    current_message = p + "\n\n"
                else:
                    current_message += p + "\n\n"
            
            if current_message.strip():
                await context.bot.send_message(chat_id=update.effective_chat.id, text=current_message, parse_mode='MarkdownV2')
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=formatted_response, parse_mode='MarkdownV2')

        # Menú de selección para descargar informe HTML
        keyboard = [
            [
                InlineKeyboardButton("Descargar informe (.HTML)", callback_data='download_html'),
                InlineKeyboardButton("No, gracias", callback_data='cancel_download')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="¿Te gustaría descargar este análisis en formato HTML?",
            reply_markup=reply_markup
        )

    except Exception as e:
        print(f"Error: {e}")
        error_message = f"No se pudo encontrar al usuario <b>{username}</b> o al repositorio: <b>{repository}</b>, quizás hubo un error con la API de GitHub."
        await context.bot.send_message(chat_id=update.effective_chat.id, text=error_message, parse_mode='HTML')


async def html_selection_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'download_html':
        repo_info = context.user_data.get('current_repo')
        if not repo_info:
            await query.edit_message_text(text="Lo siento, perdí la referencia al repositorio. Por favor, solicita los detalles de nuevo.")
            return

        await query.edit_message_text(text="Generando tu manual técnico funcional... 📄")

        username = repo_info['username']
        repository = repo_info['repository']
        repo_data = repo_info['data']

        try:
            readme = get_readme(username, repository)
            structure = get_repo_structure(username, repository)
            
            html_content = generate_html_manual(repo_data, readme, structure)
            
            # Limpiar el contenido si el modelo devuelve bloques de código markdown
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0].strip()
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0].strip()

            # Crear un archivo temporal
            filename = f"manual_{repository}.html"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                tmp.write(html_content.encode('utf-8'))
                tmp_path = tmp.name

            # Enviar el archivo
            with open(tmp_path, 'rb') as doc:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=doc,
                    filename=filename,
                    caption=f"Aquí tienes tu manual interactivo para {repository}. ¡Disfrútalo! ✨"
                )
            
            # Eliminar archivo temporal
            os.remove(tmp_path)
            
        except Exception as e:
            print(f"Error generando HTML: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Hubo un error al generar el manual HTML.")

    elif query.data.startswith('select_proj:'):
        project_name = query.data.split('select_proj:')[1]
        local_projects = context.user_data.get('local_projects', {})
        project_path = local_projects.get(project_name)

        if not project_path:
            await query.edit_message_text(text="Lo siento, no pude encontrar la ruta del proyecto seleccionado.")
            return

        await query.edit_message_text(text=f"Analizando proyecto local: <b>{project_name}</b>... 📂", parse_mode='HTML')

        try:
            # Obtener información del proyecto local
            readme = get_local_readme(project_path)
            structure = get_local_structure(project_path)
            languages = get_local_languages(project_path)
            
            # Crear un repo_data ficticio para la función generate_html_manual
            repo_data = {
                'name': project_name,
                'description': 'Proyecto analizado localmente desde el servidor.',
                'stars': 'N/A',
                'forks': 'N/A',
                'list_languages': languages,
                'url': project_path
            }

            # Generar el HTML
            html_content = generate_html_manual(repo_data, readme, structure)

            # Limpiar bloques de código
            if "```html" in html_content:
                html_content = html_content.split("```html")[1].split("```")[0].strip()
            elif "```" in html_content:
                html_content = html_content.split("```")[1].split("```")[0].strip()

            # Crear archivo temporal
            filename = f"manual_local_{project_name}.html"
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as tmp:
                tmp.write(html_content.encode('utf-8'))
                tmp_path = tmp.name

            # Enviar archivo
            with open(tmp_path, 'rb') as doc:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=doc,
                    filename=filename,
                    caption=f"Manual técnico generado para el proyecto local: {project_name} 🚀"
                )

            os.remove(tmp_path)

        except Exception as e:
            print(f"Error en análisis local: {e}")
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Hubo un error al analizar el proyecto local.")

    elif query.data == 'cancel_download':
        await query.edit_message_text(text="Entendido, no se generará el archivo HTML.")


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

async def select_local_project(update: Update, context: ContextTypes.DEFAULT_TYPE):
    projects = list_projects(BASE_DIR)
    
    if not projects:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No se encontraron proyectos en el directorio base.")
        return
    
    keyboard = []
    for project_path in projects:
        # Usamos el nombre de la carpeta para el botón
        project_name = os.path.basename(project_path)
        # Limitamos el callback_data a 64 bytes (límite de Telegram)
        # Si el path es muy largo, esto podría fallar, pero por ahora lo usaremos así
        keyboard.append([InlineKeyboardButton(project_name, callback_data=f"select_proj:{project_name}")])
    
    # Guardamos los paths completos en user_data para recuperarlos luego
    context.user_data['local_projects'] = {os.path.basename(p): p for p in projects}
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Selecciona uno de los proyectos encontrados localmente:",
        reply_markup=reply_markup
    )