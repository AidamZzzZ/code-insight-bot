import os
import time
import tempfile
from mistralai.client import Mistral
from fpdf import FPDF
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=MISTRAL_API_KEY, timeout_ms=180000)

system_promt = (
    "Eres un asistente experto en analizar repositorios de GitHub y proyectos locales. "
    "Eres experto en dar descripciones generales de proyectos, características principales y lenguajes utilizados. "
    "IMPORTANTE: No uses el carácter '#' para los títulos. Usa negritas. "
    "Retorna los mensajes en formato Markdown con emojis. "
    "IMPORTANTE: Tienes PROHIBIDO generar información falsa."
)

ANALYST_SYSTEM = (
    "Eres un analista tecnico de software senior escribiendo documentacion de onboarding. "
    "Respondes de forma concisa, directa y tecnica en espanol. "
    "Solo usas informacion provista. No inventas nada. "
    "No incluyas texto introductorio ni conclusiones, solo el contenido pedido. "
    "IMPORTANTE: No uses caracteres especiales como acentos, tildes ni enes. "
    "Escribe todo en espanol sin acentos (ejemplo: 'descripcion' en vez de 'descripcion')."
)


def mistral_model(prompt):
    chat_response = client.chat.complete(
        model="mistral-small-latest",
        messages=[
            {'role': 'system', "content": system_promt},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )
    return chat_response.choices[0].message.content


def _call(prompt, max_tokens=800):
    """Llamada al modelo con reintentos y backoff exponencial ante rate limit (429)."""
    wait_times = [10, 20, 40, 60]
    for attempt, wait in enumerate(wait_times + [None]):
        try:
            r = client.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {'role': 'system', 'content': ANALYST_SYSTEM},
                    {'role': 'user', 'content': prompt}
                ],
                temperature=0.0,
                max_tokens=max_tokens
            )
            return r.choices[0].message.content.strip()
        except Exception as e:
            err = str(e)
            is_rate_limit = '429' in err or 'rate_limit' in err.lower() or 'rate limit' in err.lower()
            if is_rate_limit and wait is not None:
                print(f"[Rate limit] Reintento {attempt + 1}/4 -- esperando {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Rate limit persistente tras 4 reintentos.")


# ═══════════════════════════════════════════════════════════════
#  Utilidades PDF
# ═══════════════════════════════════════════════════════════════

def _safe(text):
    """Limpia texto para fpdf - convierte a latin-1 seguro."""
    if not text:
        return ""
    replacements = {
        '\u2018': "'", '\u2019': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '--', '\u2026': '...',
        '\u00e1': 'a', '\u00e9': 'e', '\u00ed': 'i', '\u00f3': 'o', '\u00fa': 'u',
        '\u00c1': 'A', '\u00c9': 'E', '\u00cd': 'I', '\u00d3': 'O', '\u00da': 'U',
        '\u00f1': 'n', '\u00d1': 'N', '\u00fc': 'u', '\u00dc': 'U',
        '\u00bf': '?', '\u00a1': '!',
    }
    result = str(text)
    for old, new in replacements.items():
        result = result.replace(old, new)
    return result.encode('latin-1', errors='replace').decode('latin-1')


def _write_line(pdf, line):
    """Escribe una linea al PDF con formato automatico segun su contenido."""
    line = line.strip()
    if not line:
        pdf.ln(3)
        return

    pdf.set_x(pdf.l_margin)

    # Sub-encabezado con **texto** o MAYUSCULAS:
    if line.startswith('**') and line.endswith('**'):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, text=_safe(line.strip('*').strip()))
        pdf.set_font("Helvetica", "", 10)
        return

    # Items de lista con indentacion
    if line.startswith('- ') or line.startswith('* '):
        pdf.set_x(20)
        pdf.multi_cell(0, 5.5, text=_safe(line))
        pdf.set_x(pdf.l_margin)
        return

    # Sub-items (doble indentacion)
    if line.startswith('  - ') or line.startswith('  * '):
        pdf.set_x(28)
        pdf.multi_cell(0, 5.5, text=_safe(line.strip()))
        pdf.set_x(pdf.l_margin)
        return

    # Encabezados markdown
    if line.startswith('#'):
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, text=_safe(line.lstrip('#').strip()))
        pdf.set_font("Helvetica", "", 10)
        return

    # Texto normal
    pdf.multi_cell(0, 5.5, text=_safe(line))


def _add_section(pdf, title, content):
    """Agrega una seccion completa con titulo y contenido al PDF."""
    # Titulo de seccion
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 10, text=_safe(title), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(50, 100, 200)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Contenido
    pdf.set_font("Helvetica", "", 10)
    for line in content.split('\n'):
        _write_line(pdf, line)
    pdf.ln(3)


def _add_toc(pdf, section_titles):
    """Agrega una tabla de contenidos."""
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, text="Indice de Contenidos", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    pdf.set_font("Helvetica", "", 12)
    for i, title in enumerate(section_titles, 1):
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 8, text=_safe(f"  {i}. {title}"), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)


# ═══════════════════════════════════════════════════════════════
#  Generacion del manual tecnico PDF
# ═══════════════════════════════════════════════════════════════

def generate_pdf_manual(repo_data, readme_content, structure, source_code=""):
    """
    Genera un manual tecnico PDF completo para onboarding de desarrolladores.
    Usa 3 llamadas LLM enfocadas + ensamblado en Python.
    Retorna la ruta al archivo PDF temporal generado.
    """
    name = repo_data.get('name', 'Proyecto')
    description = repo_data.get('description', 'Sin descripcion')
    stars = repo_data.get('stars', 'N/A')
    forks = repo_data.get('forks', 'N/A')
    url = repo_data.get('url', '')
    languages = repo_data.get('list_languages', [])

    readme_short = readme_content[:3000]
    structure_text = structure[:2000]
    source_text = source_code[:8000] if source_code else "No disponible."

    ctx = f"""Proyecto: {name}
Descripcion: {description}
Lenguajes: {', '.join(languages)}
URL: {url}
README (extracto):
{readme_short}
Estructura de archivos:
{structure_text}"""

    ctx_full = f"""{ctx}
Codigo fuente (extracto):
{source_text}"""

    # ── LLAMADA 1: Vision general + Arquitectura + Flujo ────────
    print("[PDF] Llamada 1/3: Vision general, arquitectura y flujo...")
    p1 = f"""{ctx_full}

Genera un analisis tecnico con EXACTAMENTE estas 3 secciones:

SECCION_OVERVIEW
Escribe 4-5 parrafos detallados sobre:
- Que hace este proyecto y cual es su proposito principal
- Que problema resuelve y a quien va dirigido
- Cuales son sus funcionalidades principales (lista cada una)
- Que tecnologias y herramientas usa y por que
- Contexto general: es un bot, una API, una app web, etc.

SECCION_ARQUITECTURA
Escribe 4-5 parrafos detallados sobre:
- Tipo de arquitectura del sistema (monolitica, microservicios, MVC, etc.)
- Como estan organizados los directorios y modulos del proyecto
- Que patron de diseno sigue cada componente
- Como se comunican los componentes entre si
- Decisiones de diseno importantes que se observan en el codigo

SECCION_FLUJO
Escribe 3-4 parrafos detallados sobre:
- Como inicia la aplicacion (punto de entrada, que se carga primero)
- Flujo principal: paso a paso que ocurre cuando un usuario interactua
- Como fluyen los datos entre modulos (entrada -> procesamiento -> salida)
- Ciclo de vida de una peticion/comando tipico
- Manejo de errores y casos especiales visibles en el codigo

Se MUY especifico. Usa nombres reales de archivos, funciones y variables del codigo."""

    r1 = _call(p1, max_tokens=3000)
    time.sleep(2)

    # ── LLAMADA 2: Analisis detallado de modulos ────────────────
    print("[PDF] Llamada 2/3: Analisis detallado de modulos...")
    p2 = f"""{ctx_full}

Genera un analisis DETALLADO de cada modulo/archivo del proyecto.

SECCION_MODULOS
Para CADA archivo de codigo fuente que encuentres, describe:

**nombre_del_archivo.ext**
- Proposito: que responsabilidad tiene este archivo en el sistema
- Funciones/Clases principales: lista cada funcion o clase importante con una breve explicacion de que hace
- Variables globales o constantes importantes
- Dependencias: de que otros modulos del proyecto depende
- Se conecta con: que otros archivos lo importan o lo usan
- Notas tecnicas: cualquier detalle relevante (patrones usados, limitaciones, configuracion especial)

Analiza TODOS los archivos que aparecen en el codigo fuente proporcionado.
Se muy detallado en las funciones - explica los parametros y que retorna cada una.

SECCION_DEPENDENCIAS
Para cada dependencia/libreria externa del proyecto:
- Nombre de la dependencia
- Version (si esta disponible en requirements.txt, package.json, etc.)
- Para que se usa especificamente en este proyecto
- En que modulos se utiliza

Se especifico. Usa datos reales del codigo."""

    r2 = _call(p2, max_tokens=3500)
    time.sleep(2)

    # ── LLAMADA 3: Guia de onboarding ────────────────────────────
    print("[PDF] Llamada 3/3: Guia de onboarding para desarrolladores...")
    p3 = f"""{ctx_full}

Genera una guia practica completa para un desarrollador nuevo que se incorpora al proyecto.

SECCION_ONBOARDING
Escribe una guia detallada de onboarding para desarrolladores nuevos:
- Por donde empezar a leer el codigo (orden recomendado de archivos)
- Archivos clave que debe entender primero y por que
- Como esta organizado el proyecto y como encontrar cada cosa
- Como agregar una nueva funcionalidad (pasos generales)
- Convenciones de codigo observadas en el proyecto
- Patrones y practicas que se repiten en el codigo
- Posibles mejoras o areas de desarrollo futuro que se detectan
- Errores comunes o cosas a tener en cuenta
- Consejos practicos para contribuir al proyecto

Se muy especifico y practico. Usa datos reales del proyecto."""

    r3 = _call(p3, max_tokens=2500)

    # ── Parsear todas las secciones ─────────────────────────────
    all_text = r1 + "\n" + r2 + "\n" + r3
    section_map = _parse_sections(all_text, [
        'SECCION_OVERVIEW', 'SECCION_ARQUITECTURA', 'SECCION_FLUJO',
        'SECCION_MODULOS', 'SECCION_DEPENDENCIAS',
        'SECCION_ONBOARDING'
    ])

    print("[PDF] Respuestas recibidas. Ensamblando PDF...")

    # ── Construir PDF ───────────────────────────────────────────
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)

    section_titles = [
        "Descripcion General del Proyecto",
        "Arquitectura del Sistema",
        "Flujo de Datos y Ciclo de Vida",
        "Analisis Detallado de Modulos",
        "Dependencias y Tecnologias",
        "Estructura de Archivos",
        "Guia de Onboarding para Desarrolladores"
    ]

    # ── Portada ─────────────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 30)
    pdf.ln(40)
    pdf.cell(0, 16, text="Manual Tecnico", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(0, 14, text=_safe(name), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(8)
    pdf.set_draw_color(50, 100, 200)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Helvetica", "", 12)
    pdf.multi_cell(0, 7, text=_safe(description), align="C")
    pdf.ln(20)

    # Metadatos del proyecto
    pdf.set_font("Helvetica", "", 11)
    meta = [
        f"Lenguajes: {', '.join(languages)}",
        f"Estrellas: {stars}  |  Forks: {forks}",
        f"Ubicacion: {url}",
        "Tipo de documento: Manual tecnico para onboarding",
    ]
    for m in meta:
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 7, text=_safe(m), new_x="LMARGIN", new_y="NEXT", align="C")

    # ── Indice ──────────────────────────────────────────────────
    _add_toc(pdf, section_titles)

    # ── Secciones del analisis LLM ──────────────────────────────
    section_keys_ordered = [
        'SECCION_OVERVIEW', 'SECCION_ARQUITECTURA', 'SECCION_FLUJO',
        'SECCION_MODULOS', 'SECCION_DEPENDENCIAS'
    ]

    for i, key in enumerate(section_keys_ordered):
        content = section_map.get(key, "Informacion no disponible.")
        if not content:
            content = "Informacion no disponible."
        pdf.add_page()
        _add_section(pdf, f"{i+1}. {section_titles[i]}", content)

    # ── Estructura de archivos (generada en Python, no LLM) ────
    pdf.add_page()
    tree_content = _build_tree_text(structure_text)
    _add_section(pdf, f"6. {section_titles[5]}", tree_content)

    # ── Seccion de onboarding ───────────────────────────────────
    onboarding = section_map.get('SECCION_ONBOARDING', "Informacion no disponible.")
    if not onboarding:
        onboarding = "Informacion no disponible."
    pdf.add_page()
    _add_section(pdf, f"7. {section_titles[6]}", onboarding)

    # ── Pie de documento ────────────────────────────────────────
    pdf.add_page()
    pdf.set_font("Helvetica", "I", 10)
    pdf.ln(20)
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, text="--- Fin del Manual Tecnico ---", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, text=_safe(f"Proyecto: {name}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_x(pdf.l_margin)
    pdf.cell(0, 7, text="Generado automaticamente por Code Insight Bot", new_x="LMARGIN", new_y="NEXT", align="C")

    # ── Guardar ─────────────────────────────────────────────────
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    pdf.output(tmp.name)
    tmp.close()
    print(f"[PDF] Manual completo generado: {tmp.name}")
    return tmp.name


def _parse_sections(text, keys):
    """Parsea un texto en secciones delimitadas por las keys dadas."""
    sections = {}
    for i, key in enumerate(keys):
        start = text.find(key)
        if start == -1:
            sections[key] = ""
            continue
        content_start = text.find('\n', start)
        if content_start == -1:
            content_start = start + len(key)
        # Buscar el fin: la siguiente key que aparezca despues de esta
        end = len(text)
        for next_key in keys:
            if next_key == key:
                continue
            pos = text.find(next_key, content_start)
            if pos != -1 and pos < end:
                end = pos
        sections[key] = text[content_start:end].strip()
    return sections


def _build_tree_text(structure):
    """Formatea la estructura de archivos como un arbol legible."""
    if not structure:
        return "No disponible."
    lines = []
    for line in structure.split('\n'):
        line = line.strip()
        if not line:
            continue
        # Calcular profundidad basada en / para indentar
        depth = line.count('/')
        indent = "  " * depth
        name = line.split('/')[-1] if '/' in line else line
        prefix = "[DIR]" if '.' not in name and name not in ('Dockerfile', 'Makefile', 'README', 'LICENSE') else "     "
        lines.append(f"{indent}{prefix} {line}")
    return '\n'.join(lines) if lines else "No disponible."