"""Username OSINT — multi-plataforma + GitHub."""
from username_universe import search_username
from web_crawler import get_json, get_html, dork
import re

def lookup(username):
    # Busca em todas as plataformas
    plataformas = search_username(username)

    # GitHub detalhado
    github_data = {}
    gh = get_json(f"https://api.github.com/users/{username}")
    if gh and not gh.get("message"):
        github_data = {
            "nome":       gh.get("name",""),
            "bio":        gh.get("bio",""),
            "empresa":    gh.get("company",""),
            "blog":       gh.get("blog",""),
            "email":      gh.get("email",""),
            "repos":      gh.get("public_repos",0),
            "seguidores": gh.get("followers",0),
            "criado":     gh.get("created_at","")[:10],
            "localizacao":gh.get("location",""),
        }

    return {
        "username": username,
        "plataformas": plataformas,
        "total_encontrado": len(plataformas),
        "github": github_data,
    }
