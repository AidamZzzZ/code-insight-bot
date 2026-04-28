import os

from dotenv import load_dotenv
load_dotenv()

BASE_DIR = os.getenv('BASE_DIR')

# buscador de carpetas de proyectos en el directorio
def list_projects(base_path):
    proyects = set()

    for root, dirs, arch in os.walk(base_path):
        if 'requirements.txt' in arch or 'venv' in arch:
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
        