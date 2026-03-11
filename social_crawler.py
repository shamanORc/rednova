"""Busca perfis sociais via dork."""
import re, time, urllib.parse
from web_crawler import dork, extract_emails

REDES = {
    "linkedin":  (r'linkedin\.com/in/([A-Za-z0-9\-_\.]{2,60})',  "https://linkedin.com/in/"),
    "linkedin_co":(r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})', "https://linkedin.com/company/"),
    "instagram": (r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)', "https://instagram.com/"),
    "facebook":  (r'facebook\.com/(?!sharer|share|tr|plugins|dialog|login|photo|video|watch|legal|privacy|groups|events|pages/create)([A-Za-z0-9\._\-]{4,50})', "https://facebook.com/"),
    "twitter":   (r'(?:twitter|x)\.com/([A-Za-z0-9_]{2,40})', "https://twitter.com/"),
    "youtube":   (r'youtube\.com/(?:@|channel/|user/)([A-Za-z0-9\._\-]{2,60})', "https://youtube.com/@"),
    "tiktok":    (r'tiktok\.com/@([A-Za-z0-9\._]{2,40})', "https://tiktok.com/@"),
    "github":    (r'github\.com/([A-Za-z0-9\-_\.]{2,40})(?:/|\b)', "https://github.com/"),
    "jusbrasil": (r'jusbrasil\.com\.br/(?:artigos|noticias|processos|diarios)/[^\s"<>]{5,100}', "https://"),
    "escavador":  (r'escavador\.com/sobre/[^\s"<>]{5,80}', "https://"),
}

IGNORAR = {"login","sharer","share","watch","home","feed","pages","groups","events",
           "create","photo","photos","videos","marketplace","tr","plugins","dialog"}

def buscar_pessoa(nome, empresa=""):
    """Busca perfis de uma pessoa por nome."""
    redes = {}
    partes = nome.split()
    nome_curto = f"{partes[0]} {partes[-1]}" if len(partes) > 1 else nome
    nc_enc = urllib.parse.quote(f'"{nome_curto}"')
    n_enc  = urllib.parse.quote(f'"{nome}"')

    queries = {
        "linkedin":   f"{nc_enc} site:linkedin.com/in",
        "instagram":  f"{nc_enc} site:instagram.com",
        "facebook":   f"{nc_enc} site:facebook.com",
        "jusbrasil":  f"{n_enc} site:jusbrasil.com.br",
        "escavador":   f"{n_enc} site:escavador.com",
        "github":     f"{nc_enc} site:github.com",
    }
    if empresa:
        queries["linkedin"] = f"{nc_enc} {urllib.parse.quote(empresa)} site:linkedin.com/in"

    for rede, query in queries.items():
        html = dork(query)
        pat, base = REDES.get(rede, (None, None))
        if not pat or not html:
            time.sleep(0.8)
            continue
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            if rede in ("jusbrasil","escavador"):
                redes[rede] = f"https://{m.group(0)}"
            else:
                handle = m.group(1).rstrip("/").split("?")[0].split("#")[0]
                if handle.lower() not in IGNORAR and len(handle) > 1:
                    redes[rede] = base + handle
        time.sleep(1)

    # Emails na busca geral
    html_g = dork(f"{nc_enc} email OR contato OR @")
    emails = extract_emails(html_g)
    if emails:
        redes["emails_publicos"] = emails[:5]

    return redes

def buscar_empresa(nome_empresa, dominio=""):
    """Busca perfis de empresa."""
    redes = {}
    enc = urllib.parse.quote(f'"{nome_empresa}"')

    queries = {
        "linkedin_co": f"{enc} site:linkedin.com/company",
        "instagram":   f"{enc} site:instagram.com",
        "facebook":    f"{enc} site:facebook.com",
        "youtube":     f"{enc} site:youtube.com",
    }

    for rede, query in queries.items():
        html = dork(query)
        pat_key = "linkedin" if rede == "linkedin_co" else rede
        pat, base = REDES.get(rede, (None, None))
        if not pat or not html:
            time.sleep(0.8)
            continue
        m = re.search(pat, html, re.IGNORECASE)
        if m:
            handle = m.group(1).rstrip("/").split("?")[0] if rede not in ("jusbrasil","escavador") else m.group(0)
            if handle.lower() not in IGNORAR and len(handle) > 1:
                redes[rede] = base + handle
        time.sleep(1)

    return redes
