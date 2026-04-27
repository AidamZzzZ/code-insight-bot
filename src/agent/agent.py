import os
from mistralai.client import Mistral

from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(MISTRAL_API_KEY)

system_promt = (
    "Eres un asistente experto en analizar repositorios de GitHub y proyectos almacenados en la computadora donde te ejecutes localmente. "
    "Eres experto en dar respuesta precisa, dar descripciones generales de proyectos, desde dar un panorama general de un proyecto, características principales hasta lenguajes de programación utilizados. "
    "IMPORTANTE: No uses el carácter '#' para los títulos. En su lugar, usa negritas para resaltar los títulos de las secciones. "
    "Intenta ser conciso y directo para evitar mensajes excesivamente largos. "
    "Retorna los mensajes ESTRICTAMENTE en formato Markdown puedes utilizar emojis para dar mensajes mas creativos."
)


def mistral_model():
    chat_response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {
                'role': 'system',
                "content": system_promt
            },
            {
                "role": "user",
                "content": "https://github.com/Dixon282005/GymSystem"
            }
        ]
    )

    return chat_response.choices[0].message.content