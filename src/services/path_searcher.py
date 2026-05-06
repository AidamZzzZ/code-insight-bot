import os
from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR')

# buscador de carpetas de proyectos en el directorio
def list_projects(base_path):
    proyects = set()

    for root, dirs, arch in os.walk(base_path):
        if 'requirements.txt' in arch or 'venv' in arch or 'README.md' in arch or 'docker-compose.yml' in arch:
            proyects.add(root)
        
    return list(proyects)

def get_local_readme(project_path):
    # Intentar encontrar el README en el directorio del proyecto
    for file in os.listdir(project_path):
        if file.lower() == 'readme.md':
            try:
                with open(os.path.join(project_path, file), 'r', encoding='utf-8') as f:
                    return f.read()
            except:
                pass
    return "No README found locally."

def get_local_structure(project_path):
    structure = []
    # Listar archivos y carpetas, ignorando algunas carpetas comunes pesadas
    ignore = {'.git', 'venv', '__pycache__', 'node_modules'}
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d not in ignore]
        for name in files:
            rel_path = os.path.relpath(os.path.join(root, name), project_path)
            structure.append(rel_path)
            if len(structure) >= 50:
                break
        if len(structure) >= 50:
            break
    return "\n".join(structure)

def get_local_languages(project_path):
    extensions = {
        '.py': 'Python',
        '.js': 'JavaScript',
        '.html': 'HTML',
        '.css': 'CSS',
        '.cpp': 'C++',
        '.c': 'C',
        '.java': 'Java',
        '.go': 'Go',
        '.ts': 'TypeScript'
    }
    found_langs = set()
    for root, dirs, files in os.walk(project_path):
        if 'venv' in root or '.git' in root:
            continue
        for file in files:
            _, ext = os.path.splitext(file)
            if ext in extensions:
                found_langs.add(extensions[ext])
    return list(found_langs) if found_langs else ["Unknown"]


# Extensiones de archivos fuente considerados "código principal"
SOURCE_EXTENSIONS = {
    '.py', '.js', '.ts', '.jsx', '.tsx', '.go', '.java',
    '.rb', '.rs', '.php', '.c', '.cpp', '.kt', '.swift'
}
# Archivos de configuración relevantes que aportan contexto
CONFIG_FILES = {
    'package.json', 'requirements.txt', 'pyproject.toml',
    'setup.py', 'setup.cfg', 'Cargo.toml', 'go.mod',
    'pom.xml', 'build.gradle', 'Dockerfile', 'docker-compose.yml',
    '.env.example', 'config.py', 'settings.py'
}


def get_local_source_code(project_path: str, max_chars_per_file: int = 2500, max_total_chars: int = 20000) -> str:
    """Extrae el contenido real de los archivos fuente más relevantes del proyecto.

    Agrupa los archivos por directorio (módulo) y captura:
    - Archivos de configuración clave (package.json, requirements.txt, etc.)
    - Archivos de código fuente principales (limitados para no sobrepasar el contexto del LLM)

    Returns:
        Un string con secciones por módulo y fragmentos de código de cada archivo.
    """
    ignore_dirs = {'.git', 'venv', '.venv', '__pycache__', 'node_modules',
                   'dist', 'build', '.mypy_cache', '.pytest_cache', 'coverage'}

    sections = {}
    total_chars = 0

    for root, dirs, files in os.walk(project_path):
        # Filtrar directorios ignorados in-place para no descender en ellos
        dirs[:] = [d for d in dirs if d not in ignore_dirs]

        relative_module = os.path.relpath(root, project_path)
        if relative_module == '.':
            relative_module = '(raíz del proyecto)'

        for filename in sorted(files):
            filepath = os.path.join(root, filename)
            _, ext = os.path.splitext(filename)

            is_source = ext in SOURCE_EXTENSIONS
            is_config = filename in CONFIG_FILES

            if not (is_source or is_config):
                continue

            if total_chars >= max_total_chars:
                break

            try:
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
            except Exception:
                continue

            # Recortar el contenido del archivo si es muy largo
            if len(content) > max_chars_per_file:
                content = content[:max_chars_per_file] + f"\n... [archivo truncado, {len(content)} chars totales]"

            if relative_module not in sections:
                sections[relative_module] = []

            sections[relative_module].append((filename, content))
            total_chars += len(content)

        if total_chars >= max_total_chars:
            break

    # Formatear la salida en texto estructurado
    output_parts = []
    for module, files_list in sections.items():
        output_parts.append(f"\n=== MÓDULO: {module} ===")
        for fname, fcontent in files_list:
            output_parts.append(f"\n--- Archivo: {fname} ---")
            output_parts.append(fcontent)

    if not output_parts:
        return "No se encontraron archivos fuente en el proyecto."

    return "\n".join(output_parts)