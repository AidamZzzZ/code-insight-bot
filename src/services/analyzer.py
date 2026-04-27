import os

from github import Github
from github import Auth

from dotenv import load_dotenv

load_dotenv()

GITHUB_API_KEY=os.getenv('GITHUB_API_KEY')

# uso de token de acceso
auth = Auth.Token(GITHUB_API_KEY)

# creacion de instancia de github
g = Github(auth=auth)

# listar repositorios de usuario
def list_repo_user(username):
    # Toma el usuario
    user = g.get_user(username)
    print(f"Repositorios de: {user.login}")
    # retorna una lista con los repositorios del usuario
    repos = [repo.name for repo in user.get_repos()]
    return repos

# ver detalle de repositorio
def detail_repo(username, repository):
    repo = g.get_repo(f'{username}/{repository}')
    print(repo, f'{username}/{repository}')
    list_languages = list(repo.get_languages().keys())[:-1]

    det_repo = {
        'name': repo.name,
        'description': repo.description,
        'stars': repo.stargazers_count,
        'forks': repo.forks_count,
        'url': repo.html_url,
        'list_languages': list_languages
    }
    return det_repo