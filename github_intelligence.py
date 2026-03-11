"""GitHub OSINT — repos, orgs, emails nos commits."""
import re
from web_crawler import get_json

def lookup(username):
    result = {"username": username, "perfil": {}, "repos": [], "orgs": [], "emails_commits": []}

    perfil = get_json(f"https://api.github.com/users/{username}")
    if not perfil or perfil.get("message"): return result

    result["perfil"] = {
        "nome": perfil.get("name",""), "bio": perfil.get("bio",""),
        "email": perfil.get("email",""), "empresa": perfil.get("company",""),
        "blog": perfil.get("blog",""), "repos": perfil.get("public_repos",0),
        "seguidores": perfil.get("followers",0), "criado": perfil.get("created_at","")[:10],
        "avatar": perfil.get("avatar_url",""),
    }

    repos = get_json(f"https://api.github.com/users/{username}/repos?per_page=10&sort=updated")
    if repos:
        result["repos"] = [{"nome": r["name"], "descricao": r.get("description",""),
                             "linguagem": r.get("language",""), "stars": r.get("stargazers_count",0),
                             "url": r["html_url"]} for r in repos[:10]]

    orgs = get_json(f"https://api.github.com/users/{username}/orgs")
    if orgs:
        result["orgs"] = [o["login"] for o in orgs[:5]]

    # Emails nos commits do repo mais popular
    if result["repos"]:
        repo_nome = result["repos"][0]["nome"]
        commits = get_json(f"https://api.github.com/repos/{username}/{repo_nome}/commits?per_page=5")
        if commits:
            for c in commits:
                email = (c.get("commit",{}).get("author",{}).get("email") or
                         c.get("commit",{}).get("committer",{}).get("email",""))
                if email and "@" in email and "noreply" not in email:
                    result["emails_commits"].append(email)
            result["emails_commits"] = list(dict.fromkeys(result["emails_commits"]))[:5]

    return result
