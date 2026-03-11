"""Email breach + username derivation."""
import re, hashlib
from web_crawler import get_json, get_html, dork, extract_emails

def lookup(email):
    resultado = {"email": email, "breaches": [], "dominios": [], "username_guess": []}

    # Domínio do email
    if "@" in email:
        dom = email.split("@")[-1]
        resultado["dominios"].append(dom)

    # HIBP breaches list pública (sem key)
    try:
        data = get_json("https://haveibeenpwned.com/api/v3/breaches")
        if data:
            nome_local = email.split("@")[0].lower()
            # Só conseguimos checar por domínio sem key
            dom_email = email.split("@")[-1].lower() if "@" in email else ""
            for b in data:
                if dom_email and dom_email in b.get("Domain","").lower():
                    resultado["breaches"].append({
                        "nome": b["Name"], "data": b["BreachDate"],
                        "contas": b["PwnCount"],
                        "tipos": ", ".join(b.get("DataClasses",[])[:4])
                    })
    except: pass

    # Busca pública do email
    html = dork(f'"{email}"')
    if html:
        emails_rel = extract_emails(html)
        resultado["emails_relacionados"] = [e for e in emails_rel if e != email][:5]

    # Derivar usernames do email
    local = email.split("@")[0] if "@" in email else email
    variantes = [local, local.replace(".",""), local.replace("_",""),
                 local.split(".")[0] if "." in local else local]
    resultado["username_guess"] = list(dict.fromkeys(variantes))[:4]

    return resultado
