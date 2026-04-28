import os

from github import Github
from github import Auth

from dotenv import load_dotenv

load_dotenv()

GITHUB_API_KEY=os.getenv('GITHUB_API_KEY')

# uso de token de acceso
auth = Auth.Token(GITHUB_API_KEY)

# creacion de instancia de github
# Aumentamos el timeout para evitar errores en repositorios grandes
g = Github(auth=auth, timeout=60)

# listar repositorios de usuario
def list_repo_user(username):
    # Toma el usuario
    user = g.get_user(username)
    # retorna una lista con los repositorios del usuario
    repos = [repo.name for repo in user.get_repos()]
    return repos

# ver detalle de repositorio
def detail_repo(username, repository):
    repo = g.get_repo(f'{username}/{repository}')
    # El método keys() devuelve un objeto dict_keys, lo convertimos a lista.
    # Eliminamos el último elemento si es necesario (según la lógica original).
    list_languages = list(repo.get_languages().keys())

    det_repo = {
        'name': repo.name,
        'description': repo.description,
        'stars': repo.stargazers_count,
        'forks': repo.forks_count,
        'url': repo.html_url,
        'list_languages': list_languages
    }
    return det_repo

def get_readme(username, repository):
    try:
        repo = g.get_repo(f'{username}/{repository}')
        readme = repo.get_readme()
        return readme.decoded_content.decode('utf-8')
    except:
        return "No README found."

def get_repo_structure(username, repository):
    try:
        repo = g.get_repo(f'{username}/{repository}')
        contents = repo.get_contents("")
        structure = []
        while contents:
            file_content = contents.pop(0)
            if file_content.type == "dir":
                contents.extend(repo.get_contents(file_content.path))
            structure.append(file_content.path)
        return "\n".join(structure[:50]) # Limit to first 50 files
    except:
        return "Could not retrieve structure."