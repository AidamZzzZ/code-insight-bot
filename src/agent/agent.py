import os
from mistralai.client import Mistral

from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
# Aumentamos el timeout a 120 segundos (120000 ms) para evitar errores de lectura
client = Mistral(api_key=MISTRAL_API_KEY, timeout_ms=120000)

system_promt = (
    "Eres un asistente experto en analizar repositorios de GitHub y proyectos almacenados en la computadora donde te ejecutes localmente. "
    "Eres experto en dar respuesta precisa, dar descripciones generales de proyectos, desde dar un panorama general de un proyecto, características principales hasta lenguajes de programación utilizados. "
    "IMPORTANTE: No uses el carácter '#' para los títulos. En su lugar, usa negritas para resaltar los títulos de las secciones. "
    "Intenta ser conciso y directo para evitar mensajes excesivamente largos. "
    "Retorna los mensajes ESTRICTAMENTE en formato Markdown puedes utilizar emojis para dar mensajes mas creativos."
    "IMPORTANTE: Tienes PROHIBIDO generar informacion falsa, utiliza la informacion proporcionada por URLs y diccionarios para responder consultas."
)


def mistral_model(prompt):
    chat_response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                'role': 'system',
                "content": system_promt
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.0
    )

    return chat_response.choices[0].message.content

def generate_html_manual(repo_data, readme_content, structure):
    prompt = f"""
    Genera un manual técnico funcional en un ÚNICO archivo HTML para el repositorio: {repo_data['name']}.
    
    INFORMACIÓN DEL PROYECTO:
    - Descripción: {repo_data['description']}
    - Estrellas: {repo_data['stars']} | Forks: {repo_data['forks']}
    - Lenguajes: {', '.join(repo_data['list_languages'])}
    - URL: {repo_data['url']}
    - README: {readme_content[:3000]}
    - Estructura: {structure}
    
    REQUISITOS DEL MANUAL:
    1. ESTRUCTURA DE PÁGINAS: El manual debe estar dividido en secciones claras que parezcan páginas de un libro.
    2. NAVEGACIÓN SIMPLE: Incluye botones de 'Página Anterior' y 'Página Siguiente' que funcionen con JavaScript simple para mostrar/ocultar las secciones.
    3. CONTENIDO OBLIGATORIO:
       - Portada: Nombre del proyecto y resumen.
       - Sección 1: Descripción General y Estadísticas.
       - Sección 2: Lenguajes de Programación utilizados.
       - Sección 3: Estructura del Repositorio (árbol de archivos).
       - Sección 4: Guía de Uso/Instalación (resumen del README).
    4. DISEÑO LIMPIO Y FUNCIONAL:
       - Usa una fuente legible (ej. Arial, Helvetica).
       - Un diseño centrado, con un contenedor tipo 'página' de color blanco sobre un fondo gris claro.
       - El código debe estar bien formateado.
    
    IMPORTANTE: Retorna el código HTML completo con CSS y JS internos. Debe ser 100% funcional al abrirse en un navegador.
    NO incluyas explicaciones adicionales, solo el código.
    """
    
    chat_response = client.chat.complete(
        model="mistral-large-latest",
        messages=[
            {
                'role': 'system',
                "content": "Eres un desarrollador experto en documentación técnica. Generas HTML limpio, funcional y directo."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.1,
        max_tokens=4000
    )
    
    return chat_response.choices[0].message.content