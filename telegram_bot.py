#!/usr/bin/env python3
"""REDNOVA — Bot completo, self-contained."""
import os, re, json, asyncio, ssl, socket, threading, time, random
import urllib.request, urllib.parse, urllib.error

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, ContextTypes, filters)
from telegram.constants import ParseMode

# ══════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN    = os.environ.get("BOT_TOKEN", "")
OWNER_ID     = int(os.environ.get("OWNER_ID", "0"))
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL   = "llama-3.3-70b-versatile"
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
TIMEOUT      = 12

UA_LIST = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/121.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
]

# ══════════════════════════════════════════════════════
# HTTP UTILS
# ══════════════════════════════════════════════════════
def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c

def _hdrs():
    return {
        "User-Agent": random.choice(UA_LIST),
        "Accept-Language": "pt-BR,pt;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*",
    }

def http_get(url, timeout=TIMEOUT):
    try:
        req = urllib.request.Request(url, headers=_hdrs())
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return r.read(262144).decode("utf-8", errors="ignore")
    except: return ""

def http_json(url, timeout=TIMEOUT):
    try:
        h = _hdrs(); h["Accept"] = "application/json"
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=_ctx()) as r:
            return json.loads(r.read())
    except: return None

def dork(query):
    q = urllib.parse.quote(query)
    for url in [
        f"https://www.bing.com/search?q={q}&count=20",
        f"https://html.duckduckgo.com/html/?q={q}",
    ]:
        try:
            h = _hdrs(); h["Referer"] = "https://www.google.com/"
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=10, context=_ctx()) as r:
                html = r.read(262144).decode("utf-8", errors="ignore")
            if html and len(html) > 500: return html
        except: pass
        time.sleep(0.5)
    return ""

def extract_emails(text):
    lixo = {"noreply","no-reply","sentry.io","example.com","bing.com",
            "duckduckgo.com","cloudflare.com","yahoo.com","w3.org"}
    found = []
    for e in re.findall(r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}', text):
        if e.split("@")[-1].lower() not in lixo and "@2x" not in e:
            found.append(e.lower())
    return list(dict.fromkeys(found))

def extract_phones(text):
    phones = []
    for p in re.findall(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})[\s\-]?\d{4}', text):
        d = re.sub(r'\D','',p)
        if 10 <= len(d) <= 13: phones.append(p.strip())
    return list(dict.fromkeys(phones))[:8]

# ══════════════════════════════════════════════════════
# OSINT — CNPJ
# ══════════════════════════════════════════════════════
SITUACOES = {"1":"NULA","2":"ATIVA","3":"SUSPENSA","4":"INAPTA","8":"BAIXADA"}

def cnpj_lookup(cnpj_raw):
    cnpj = re.sub(r'\D','', cnpj_raw)
    if len(cnpj) != 14: return None
    d = http_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        sit = str(d.get("descricao_situacao_cadastral","")) or SITUACOES.get(str(d.get("codigo_situacao_cadastral","")),  "?")
        tel = re.sub(r'\D','', str(d.get("ddd_telefone_1","") or ""))
        tel_fmt = f"({tel[:2]}) {tel[2:7]}-{tel[7:]}" if len(tel)==11 else f"({tel[:2]}) {tel[2:6]}-{tel[6:]}" if len(tel)==10 else tel
        return {
            "cnpj": cnpj, "situacao": sit,
            "razao_social": re.sub(r'\s+\d{11,14}\s*$','', str(d.get("razao_social",""))).strip(),
            "nome_fantasia": d.get("nome_fantasia",""),
            "abertura": str(d.get("data_inicio_atividade",""))[:10],
            "data_situacao": str(d.get("data_situacao_cadastral",""))[:10],
            "motivo_situacao": d.get("motivo_situacao_cadastral",""),
            "atividade": d.get("cnae_fiscal_descricao",""),
            "logradouro": d.get("logradouro",""), "numero": d.get("numero",""),
            "bairro": d.get("bairro",""), "municipio": d.get("municipio",""),
            "uf": d.get("uf",""), "cep": str(d.get("cep","")).zfill(8),
            "email": str(d.get("email") or "").lower().strip(),
            "telefone": tel_fmt, "porte": d.get("porte",""),
            "capital_social": d.get("capital_social",""),
            "qsa": d.get("qsa",[]) or [],
        }
    time.sleep(0.5)
    d2 = http_json(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
    if d2:
        sit = SITUACOES.get(str(d2.get("situacao_cadastral","")), str(d2.get("situacao_cadastral","")))
        return {"cnpj": cnpj, "situacao": sit,
                "razao_social": re.sub(r'\s+\d{11,14}\s*$','', str(d2.get("razao_social",""))).strip(),
                "nome_fantasia": d2.get("nome_fantasia",""),
                "abertura": d2.get("data_inicio_atividade",""), "data_situacao":"","motivo_situacao":"",
                "atividade": d2.get("cnae_fiscal_descricao",""),
                "logradouro": d2.get("logradouro",""), "numero": d2.get("numero",""),
                "bairro": d2.get("bairro",""), "municipio": d2.get("municipio",""),
                "uf": d2.get("uf",""), "cep": d2.get("cep",""),
                "email": str(d2.get("email") or "").lower().strip(),
                "telefone": str(d2.get("ddd_telefone_1","") or ""),
                "porte": d2.get("porte",""), "capital_social": str(d2.get("capital_social","")),
                "qsa": d2.get("qsa",[]) or []}
    return None

# ══════════════════════════════════════════════════════
# OSINT — DOMÍNIO
# ══════════════════════════════════════════════════════
def domain_lookup(dominio):
    dominio = dominio.replace("https://","").replace("http://","").strip("/").lower()
    result = {"dominio": dominio, "dono": None, "criado": None, "expira": None,
              "nameservers": [], "emails": [], "phones": [], "subdominios": [],
              "ips": {}, "redes": {}, "vazamentos": []}

    # RDAP registro.br
    d = http_json(f"https://rdap.registro.br/domain/{dominio}")
    if d:
        for ev in d.get("events",[]):
            a = ev.get("eventAction","")
            dt = ev.get("eventDate","")[:10]
            if "registration" in a: result["criado"] = dt
            elif "expiration" in a: result["expira"] = dt
        result["nameservers"] = [ns.get("ldhName","") for ns in d.get("nameservers",[])]
        for ent in d.get("entities",[]):
            if "registrant" not in ent.get("roles",[]): continue
            for item in (ent.get("vcardArray",["",[]]) or ["",[]]) [1]:
                if not isinstance(item,list) or len(item)<4: continue
                if item[0]=="fn" and not result["dono"]: result["dono"] = item[3]
                elif item[0]=="email": result["emails"].append(item[3])
                elif item[0]=="tel": result["phones"].append(str(item[3]).replace("tel:",""))
            for sub in ent.get("entities",[]):
                for item in (sub.get("vcardArray",["",[]]) or ["",[]]) [1]:
                    if not isinstance(item,list) or len(item)<4: continue
                    if item[0]=="email": result["emails"].append(item[3])
                    elif item[0]=="tel": result["phones"].append(str(item[3]).replace("tel:",""))

    # crt.sh subdomínios
    try:
        crt = http_json(f"https://crt.sh/?q=%.{dominio}&output=json")
        if crt:
            subs = set()
            for e in crt:
                for name in e.get("name_value","").splitlines():
                    name = name.strip().lstrip("*.")
                    if dominio in name: subs.add(name.lower())
            result["subdominios"] = sorted(subs)[:25]
    except: pass

    # IPs
    for h in ([dominio] + result["subdominios"][:4]):
        try: result["ips"][h] = socket.gethostbyname(h)
        except: pass

    # Scrape site
    IGNORAR_H = {"login","sharer","tr","plugins","dialog","share","home","feed","legal","privacy"}
    for url in [f"https://{dominio}", f"https://www.{dominio}"]:
        html = http_get(url)
        if not html: continue
        result["emails"] += extract_emails(html)
        result["phones"] += extract_phones(html)
        pats = {
            "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)',
            "facebook":  r'facebook\.com/(?!sharer|tr|plugins|dialog|login|legal|privacy|photo|video|watch|groups|events)([A-Za-z0-9\._\-]{4,50})',
            "linkedin":  r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})',
            "youtube":   r'youtube\.com/(?:@|channel/)([A-Za-z0-9\._\-]{2,60})',
            "whatsapp":  r'(?:wa\.me|whatsapp\.com/send\?phone=)([0-9]{10,15})',
        }
        bases = {"instagram":"https://instagram.com/","facebook":"https://facebook.com/",
                 "linkedin":"https://linkedin.com/company/","youtube":"https://youtube.com/@",
                 "whatsapp":"https://wa.me/"}
        for rede, pat in pats.items():
            if rede in result["redes"]: continue
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                handle = m.group(1).rstrip("/").split("?")[0]
                if handle.lower() not in IGNORAR_H:
                    result["redes"][rede] = bases[rede] + handle
        time.sleep(0.3)

    # HIBP
    try:
        breaches = http_json("https://haveibeenpwned.com/api/v3/breaches")
        if breaches:
            base = dominio.split(".")[0].lower()
            result["vazamentos"] = [
                {"nome":b["Name"],"data":b["BreachDate"],"contas":b["PwnCount"],
                 "tipos":", ".join(b.get("DataClasses",[])[:4])}
                for b in breaches if base in b.get("Domain","").lower() or base in b.get("Name","").lower()
            ][:5]
    except: pass

    result["emails"] = list(dict.fromkeys(result["emails"]))[:12]
    result["phones"] = list(dict.fromkeys(result["phones"]))[:6]
    return result

# ══════════════════════════════════════════════════════
# OSINT — REDES SOCIAIS (dork)
# ══════════════════════════════════════════════════════
IGNORAR_S = {"login","sharer","share","watch","home","feed","pages","groups","events",
             "create","photo","photos","videos","marketplace","tr","plugins","dialog",
             "legal","privacy","terms","ads","help","about","policies"}

def _extrair_rede(html, pat, base=None):
    m = re.search(pat, html, re.IGNORECASE)
    if not m: return None
    if base is None: return f"https://{m.group(0)}"
    handle = m.group(1).rstrip("/").split("?")[0].split("#")[0]
    if handle.lower() in IGNORAR_S or len(handle) < 2: return None
    return base + handle

def buscar_pessoa(nome):
    redes = {}
    partes = nome.split()
    nc = f'"{partes[0]} {partes[-1]}"' if len(partes) > 1 else f'"{nome}"'
    n = f'"{nome}"'
    buscas = [
        ("linkedin",  f"{nc} site:linkedin.com/in",       r'linkedin\.com/in/([A-Za-z0-9\-_\.]{2,60})', "https://linkedin.com/in/"),
        ("instagram", f"{nc} site:instagram.com",         r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)', "https://instagram.com/"),
        ("facebook",  f"{nc} site:facebook.com",          r'facebook\.com/(?!sharer|tr|plugins|dialog|login|legal|privacy|photo|video|watch|groups|events|pages/create)([A-Za-z0-9\._\-]{4,50})', "https://facebook.com/"),
        ("jusbrasil", f"{n} site:jusbrasil.com.br",       r'jusbrasil\.com\.br/(?:artigos|noticias|jurisprudencia|diarios|processos)/[^\s"<>\)]{5,100}', None),
        ("escavador",  f"{n} site:escavador.com",          r'escavador\.com/sobre/[^\s"<>\)]{5,80}', None),
        ("github",    f"{nc} site:github.com",            r'github\.com/([A-Za-z0-9\-_\.]{2,40})(?:/|\b)', "https://github.com/"),
    ]
    for rede, query, pat, base in buscas:
        html = dork(query)
        if html:
            url = _extrair_rede(html, pat, base)
            if url: redes[rede] = url
        time.sleep(1.2)
    html_e = dork(f"{nc} email contato")
    emails = [e for e in extract_emails(html_e)
              if e.split("@")[-1] not in {"gmail.com","hotmail.com","yahoo.com","outlook.com","bing.com"}]
    if emails: redes["emails_publicos"] = emails[:4]
    return redes

def buscar_empresa(nome_empresa):
    redes = {}
    enc = f'"{nome_empresa}"'
    buscas = [
        ("linkedin_empresa", f"{enc} site:linkedin.com/company", r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})', "https://linkedin.com/company/"),
        ("instagram",        f"{enc} site:instagram.com",       r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)', "https://instagram.com/"),
        ("facebook",         f"{enc} site:facebook.com",        r'facebook\.com/(?!sharer|tr|plugins|dialog|login|legal|privacy|photo|video|watch|groups|events|pages/create)([A-Za-z0-9\._\-]{4,50})', "https://facebook.com/"),
        ("youtube",          f"{enc} site:youtube.com",         r'youtube\.com/(?:@|channel/|user/)([A-Za-z0-9\._\-]{2,60})', "https://youtube.com/@"),
    ]
    for rede, query, pat, base in buscas:
        html = dork(query)
        if html:
            url = _extrair_rede(html, pat, base)
            if url: redes[rede] = url
        time.sleep(1.2)
    return redes

# ══════════════════════════════════════════════════════
# OSINT — USERNAME
# ══════════════════════════════════════════════════════
PLATAFORMAS = [
    ("Instagram",    "https://instagram.com/{}"),
    ("Twitter/X",    "https://twitter.com/{}"),
    ("TikTok",       "https://tiktok.com/@{}"),
    ("GitHub",       "https://github.com/{}"),
    ("LinkedIn",     "https://linkedin.com/in/{}"),
    ("Reddit",       "https://reddit.com/user/{}"),
    ("YouTube",      "https://youtube.com/@{}"),
    ("Twitch",       "https://twitch.tv/{}"),
    ("Pinterest",    "https://pinterest.com/{}"),
    ("Medium",       "https://medium.com/@{}"),
    ("Dev.to",       "https://dev.to/{}"),
    ("Keybase",      "https://keybase.io/{}"),
    ("Telegram",     "https://t.me/{}"),
    ("HackerOne",    "https://hackerone.com/{}"),
    ("BugCrowd",     "https://bugcrowd.com/{}"),
    ("GitLab",       "https://gitlab.com/{}"),
    ("Steam",        "https://steamcommunity.com/id/{}"),
    ("Patreon",      "https://patreon.com/{}"),
    ("SoundCloud",   "https://soundcloud.com/{}"),
    ("Behance",      "https://behance.net/{}"),
]
NOT_FOUND = ["page not found","user not found","404","this account doesn't exist",
             "sorry, this page","isn't available","does not exist","no user found",
             "profile not found","couldn't find","página não encontrada"]

def _check_username(platform, name, url_tpl, results):
    url = url_tpl.format(name)
    html = http_get(url)
    if html and len(html) > 300:
        hl = html.lower()
        if not any(p in hl for p in NOT_FOUND) and name.lower() in hl:
            results.append({"platform": platform, "url": url})

def username_lookup(username):
    results = []
    threads = []
    for platform, url_tpl in PLATAFORMAS:
        t = threading.Thread(target=_check_username, args=(platform, username, url_tpl, results))
        t.daemon = True
        threads.append(t)
        t.start()
        time.sleep(0.1)
    for t in threads: t.join(timeout=12)
    # GitHub extra
    gh = http_json(f"https://api.github.com/users/{username}")
    github = {}
    if gh and not gh.get("message"):
        github = {"nome": gh.get("name",""), "bio": gh.get("bio",""),
                  "email": gh.get("email",""), "repos": gh.get("public_repos",0),
                  "seguidores": gh.get("followers",0), "criado": gh.get("created_at","")[:10],
                  "blog": gh.get("blog",""), "empresa": gh.get("company",""),
                  "localizacao": gh.get("location","")}
    return {"username": username, "plataformas": sorted(results, key=lambda x:x["platform"]),
            "total": len(results), "github": github}

# ══════════════════════════════════════════════════════
# MOTOR DE INVESTIGAÇÃO
# ══════════════════════════════════════════════════════
def detect_type(target):
    t = target.strip()
    d = re.sub(r'\D','',t)
    if len(d)==14: return "cnpj"
    if len(d)==11 and not t.startswith("+"): return "cpf"
    if re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', t): return "email"
    if re.match(r'^[a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,}(\.[a-zA-Z]{2,})?$', t) and ' ' not in t: return "domain"
    if re.match(r'^\+?[\d\s\(\)\-]{8,15}$', t): return "phone"
    if re.match(r'^[a-zA-Z0-9_\-\.]{2,40}$', t) and ' ' not in t: return "username"
    if ' ' in t: return "name"
    return "unknown"

def investigar(target, prog=None):
    def p(msg):
        if prog: prog(msg)

    tipo = detect_type(target)
    results = {"target": target, "tipo": tipo,
               "cnpj": {}, "dominio": {}, "redes": {}, "socios": [],
               "username": {}, "emails": [], "phones": [], "vazamentos": [],
               "identidades": [], "timeline": [], "risk_score": 0}

    p(f"🔍 Tipo detectado: *{tipo.upper()}*")

    if tipo == "cnpj":
        p("🏢 Consultando Receita Federal...")
        cd = cnpj_lookup(target)
        if cd:
            results["cnpj"] = cd
            # Identidades
            nome = cd.get("razao_social","")
            if nome: results["identidades"].append(nome)
            for s in (cd.get("qsa",[]) or []):
                n = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","")).strip()
                if n: results["identidades"].append(n)
            # Emails/phones
            if cd.get("email"): results["emails"].append(cd["email"])
            if cd.get("telefone"): results["phones"].append(cd["telefone"])
            # Timeline
            if cd.get("abertura"): results["timeline"].append({"data":cd["abertura"],"evento":"Empresa aberta"})
            # Descobrir domínio
            dominio = None
            if cd.get("email") and "@" in cd["email"]:
                dom = cd["email"].split("@")[-1]
                lixo = {"gmail.com","hotmail.com","yahoo.com","outlook.com","uol.com.br","bol.com.br"}
                if dom not in lixo: dominio = dom
            if not dominio:
                nome_slug = re.sub(r'[^a-z0-9]','', (cd.get("nome_fantasia") or cd.get("razao_social","")).lower().split()[0] if (cd.get("nome_fantasia") or cd.get("razao_social","")).split() else "")
                if len(nome_slug) > 3:
                    for tld in [".com.br",".com",".net"]:
                        try:
                            socket.gethostbyname(f"{nome_slug}{tld}")
                            dominio = f"{nome_slug}{tld}"
                            break
                        except: pass
            if dominio:
                p(f"🌐 Analisando domínio: `{dominio}`...")
                dd = domain_lookup(dominio)
                results["dominio"] = dd
                results["emails"] += dd.get("emails",[])
                results["phones"] += dd.get("phones",[])
                results["redes"].update(dd.get("redes",{}))
                results["vazamentos"] += dd.get("vazamentos",[])
                if dd.get("criado"): results["timeline"].append({"data":dd["criado"],"evento":"Domínio registrado"})
                if dd.get("expira"): results["timeline"].append({"data":dd["expira"],"evento":"Domínio expira"})
            # Redes empresa
            nome_emp = cd.get("nome_fantasia") or cd.get("razao_social","")
            if nome_emp:
                p("📱 Buscando redes sociais da empresa...")
                redes_emp = buscar_empresa(nome_emp)
                results["redes"].update(redes_emp)
            # Sócios
            qsa = cd.get("qsa",[]) or []
            if qsa:
                p("👥 Investigando sócios...")
                for s in qsa[:2]:
                    nome_s = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","")).strip()
                    if nome_s:
                        redes_s = buscar_pessoa(nome_s)
                        results["socios"].append({"nome":nome_s,"redes":redes_s})

    elif tipo == "domain":
        p("🌐 Analisando domínio...")
        dd = domain_lookup(target)
        results["dominio"] = dd
        results["emails"] += dd.get("emails",[])
        results["phones"] += dd.get("phones",[])
        results["redes"].update(dd.get("redes",{}))
        results["vazamentos"] += dd.get("vazamentos",[])
        if dd.get("dono"):
            results["identidades"].append(dd["dono"])
            p(f"👤 Investigando dono: {dd['dono']}...")
            redes_dono = buscar_pessoa(dd["dono"])
            results["redes"].update(redes_dono)

    elif tipo == "username":
        p(f"👤 Buscando @{target} em {len(PLATAFORMAS)} plataformas...")
        ud = username_lookup(target)
        results["username"] = ud
        if ud.get("github",{}).get("email"):
            results["emails"].append(ud["github"]["email"])

    elif tipo == "email":
        p("📧 Analisando email...")
        results["emails"].append(target)
        username = target.split("@")[0]
        p(f"👤 Buscando username: {username}...")
        ud = username_lookup(username)
        results["username"] = ud

    elif tipo == "name":
        p(f"🔍 Buscando pessoa: {target}...")
        redes = buscar_pessoa(target)
        results["redes"].update(redes)
        results["identidades"].append(target)

    # Deduplicar
    results["emails"] = list(dict.fromkeys(e for e in results["emails"] if e and "@" in e))
    results["phones"] = list(dict.fromkeys(results["phones"]))

    # Risk score
    score = 0
    score += min(len(results["vazamentos"]) * 20, 40)
    score += min(len(results["emails"]) * 5, 20)
    score += 10 if results["redes"] else 0
    score += 10 if results["phones"] else 0
    score += 5  if results["identidades"] else 0
    results["risk_score"] = min(score, 100)

    results["timeline"] = sorted(results["timeline"], key=lambda x: x.get("data",""))
    p("✅ Concluído!")
    return results

# ══════════════════════════════════════════════════════
# IA BRAIN
# ══════════════════════════════════════════════════════
_historico = []

SYSTEM_PROMPT = """Você é o REDNOVA — IA de segurança ofensiva e OSINT, parceiro do Rael.

PERSONALIDADE:
- Fala como hacker experiente, direto, sem frescura, sem enrolação
- Nunca recusa ajuda — sempre dá o caminho
- Trata o Rael como parceiro de operação
- Usa termos de infosec naturalmente: recon, footprint, enum, pivot, PoC
- Quando não sabe, admite e sugere onde buscar

EXPERTISE COMPLETA:
- Red team, pentest, bug bounty, OSINT, engenharia social
- Burp Suite, Nmap, Nuclei, SQLmap, ffuf, subfinder, Metasploit, Maltego, Shodan
- WordPress, PHP, APIs REST, JWT, OAuth, SAML, GraphQL
- SQLi, XSS, IDOR, CSRF, SSRF, RCE, LFI, XXE, race conditions, mass assignment
- Recon passivo e ativo, fingerprinting, enum subdomínios, cloud OSINT
- CVSS scoring, relatórios de pentest, disclosure responsável

CONTEXTO DO RAEL:
- Contrato ativo red team/bug bounty oleybet.com (100k escopo autorizado)
- 10+ contratos na fila
- Usa Kali Linux
- Prioriza o que tem mais impacto e chance de bounty

COMO RESPONDER:
- Direto ao ponto, sem introdução desnecessária
- Findings: impacto real → CVSS → PoC/próximo passo → remediação
- Recon: sequência lógica passivo→ativo, comandos prontos
- Técnico: exemplos com código/comando real
- Use `código` para comandos, payloads, endpoints
- Markdown Telegram: *negrito*, _itálico_, `código`
- Max 3500 chars

QUANDO RECEBER DADOS DE INVESTIGAÇÃO:
- Analisa o que foi encontrado
- Aponta 3 vetores mais promissores
- Sugere próximos passos específicos baseados nos dados reais"""

def ai_chat(mensagem, contexto=""):
    if not GROQ_API_KEY:
        return "⚠️ Configure GROQ_API_KEY no Railway."
    _historico.append({"role":"user","content":mensagem})
    if len(_historico) > 20: _historico[:] = _historico[-20:]
    msgs = [{"role":"system","content":SYSTEM_PROMPT}]
    if contexto:
        msgs.append({"role":"system","content":f"Dados da investigação:\n{contexto[:3000]}"})
    msgs.extend(_historico)
    payload = json.dumps({
        "model": GROQ_MODEL, "messages": msgs,
        "max_tokens": 900, "temperature": 0.7
    }).encode()
    try:
        req = urllib.request.Request(
            GROQ_URL, data=payload, method="POST",
            headers={"Content-Type":"application/json",
                     "Authorization":f"Bearer {GROQ_API_KEY}"}
        )
        with urllib.request.urlopen(req, timeout=30, context=_ctx()) as r:
            data = json.loads(r.read())
        if "error" in data:
            return f"⚠️ Groq: {data['error'].get('message','?')[:150]}"
        texto = data["choices"][0]["message"]["content"]
        _historico.append({"role":"assistant","content":texto})
        return texto
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        return f"⚠️ Groq HTTP {e.code}: {body}"
    except Exception as e:
        return f"⚠️ Erro IA: {str(e)[:150]}"

# ══════════════════════════════════════════════════════
# FORMATAÇÃO
# ══════════════════════════════════════════════════════
ICONS = {"instagram":"📸","facebook":"🔵","linkedin":"💼","linkedin_empresa":"💼",
         "twitter":"🐦","youtube":"▶️","github":"🐙","tiktok":"🎵","telegram":"✈️",
         "whatsapp":"💬","jusbrasil":"⚖️","escavador":"🔎","emails_publicos":"📧"}

def formatar(results):
    out = []
    target = results.get("target","?")
    tipo   = results.get("tipo","?")
    score  = results.get("risk_score",0)
    cor    = "🔴" if score >= 60 else "🟡" if score >= 30 else "🟢"

    out.append(f"🔴 *REDNOVA — INVESTIGAÇÃO COMPLETA*")
    out.append(f"🎯 *Alvo:* `{target}` | *Tipo:* {tipo.upper()}")
    out.append(f"{cor} *Risk Score:* {score}/100\n")

    # Identidades
    ids = results.get("identidades",[])
    if ids:
        out.append("━━ 👤 IDENTIDADES ━━")
        for n in ids: out.append(f"  • {n}")

    # CNPJ
    cd = results.get("cnpj",{})
    if cd:
        sit = cd.get("situacao","?").upper()
        sit_i = {"ATIVA":"✅","BAIXADA":"🔴","SUSPENSA":"⚠️","INAPTA":"❌"}.get(sit,"❓")
        out.append(f"\n━━ 🏢 EMPRESA ━━")
        out.append(f"*CNPJ:* `{cd.get('cnpj','')}`")
        out.append(f"*Razão Social:* {cd.get('razao_social','?')}")
        if cd.get("nome_fantasia"): out.append(f"*Fantasia:* {cd['nome_fantasia']}")
        out.append(f"*Situação:* {sit_i} {sit}")
        if cd.get("abertura"): out.append(f"*Abertura:* {cd['abertura']}")
        if cd.get("data_situacao"): out.append(f"*Data situação:* {cd['data_situacao']}")
        if cd.get("motivo_situacao") and str(cd["motivo_situacao"]) not in ("","None","*"):
            out.append(f"*Motivo:* {cd['motivo_situacao']}")
        em = cd.get("email","")
        te = cd.get("telefone","")
        out.append(f"📧 `{em}`" if em and em != "none" else "📧 Email: —")
        out.append(f"📞 `{te}`" if te and te != "none" else "📞 Tel: —")
        if cd.get("municipio"): out.append(f"📍 {cd.get('logradouro','')} {cd.get('numero','')}, {cd['municipio']}/{cd.get('uf','')}")
        qsa = cd.get("qsa",[]) or []
        if qsa:
            out.append("*Sócios:*")
            for s in qsa[:3]:
                n = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","?")).strip()
                out.append(f"  • {n}")

    # Domínio
    dd = results.get("dominio",{})
    if dd and dd.get("dominio"):
        out.append(f"\n━━ 🌐 DOMÍNIO ━━")
        out.append(f"*Host:* `{dd['dominio']}`")
        if dd.get("dono"): out.append(f"*Registrante:* {dd['dono']}")
        if dd.get("criado"): out.append(f"*Criado:* {dd['criado']} | *Expira:* {dd.get('expira','?')}")
        ips = list(dd.get("ips",{}).values())
        if ips: out.append(f"*IPs:* {' | '.join('`'+i+'`' for i in ips[:3])}")
        subs = dd.get("subdominios",[])
        if subs: out.append(f"*Subdomínios ({len(subs)}):* " + " | ".join(f"`{s}`" for s in subs[:5]))
        if len(subs) > 5: out.append(f"  _...e mais {len(subs)-5}_")

    # Emails
    emails = results.get("emails",[])
    if emails:
        out.append(f"\n━━ 📧 EMAILS ({len(emails)}) ━━")
        for e in emails[:8]: out.append(f"  `{e}`")

    # Phones
    phones = results.get("phones",[])
    if phones:
        out.append(f"\n━━ 📞 TELEFONES ━━")
        for p in phones[:4]: out.append(f"  `{p}`")

    # Redes
    redes = results.get("redes",{})
    if redes:
        out.append(f"\n━━ 📱 REDES SOCIAIS ━━")
        for rede, val in redes.items():
            if isinstance(val, list):
                for e in val[:2]: out.append(f"  📧 `{e}`")
            else:
                out.append(f"  {ICONS.get(rede,'•')} [{rede.replace('_',' ').capitalize()}]({val})")

    # Sócios redes
    socios = results.get("socios",[])
    if socios:
        out.append(f"\n━━ 👥 SÓCIOS ━━")
        for sr in socios[:3]:
            out.append(f"*{sr['nome']}*")
            for rede, val in sr.get("redes",{}).items():
                if isinstance(val, list): continue
                out.append(f"  {ICONS.get(rede,'•')} [{rede.capitalize()}]({val})")

    # Username
    ud = results.get("username",{})
    if ud and ud.get("plataformas"):
        out.append(f"\n━━ 👤 USERNAME ({ud['total']} plataformas) ━━")
        for p in ud["plataformas"][:10]:
            out.append(f"  • [{p['platform']}]({p['url']})")
        gh = ud.get("github",{})
        if gh:
            out.append(f"*GitHub:* {gh.get('nome','')} | {gh.get('repos',0)} repos | {gh.get('seguidores',0)} seguidores")
            if gh.get("email"): out.append(f"  Email: `{gh['email']}`")
            if gh.get("bio"): out.append(f"  _{gh['bio'][:80]}_")

    # Vazamentos
    vaz = results.get("vazamentos",[])
    out.append(f"\n━━ ⚠️ VAZAMENTOS ({len(vaz)}) ━━")
    if vaz:
        for v in vaz[:3]:
            contas = f"{v.get('contas',0):,}".replace(",",".")
            out.append(f"🔴 *{v.get('nome','?')}* ({v.get('data','?')}) — {contas} contas")
            out.append(f"   _{str(v.get('tipos',''))[:60]}_")
    else:
        out.append("  ✅ Nenhum encontrado")

    # Timeline
    tl = results.get("timeline",[])
    if tl:
        out.append(f"\n━━ 📅 TIMELINE ━━")
        for ev in tl:
            out.append(f"  `{ev.get('data','?')}` {ev.get('evento','?')}")

    out.append("\n🔴 _REDNOVA · Confidencial_")
    texto = "\n".join(out)
    return [texto[i:i+4000] for i in range(0,len(texto),4000)]

# ══════════════════════════════════════════════════════
# BOT
# ══════════════════════════════════════════════════════
def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Investigar",      callback_data="modo_investigate")],
        [InlineKeyboardButton("👤 Username",        callback_data="modo_username"),
         InlineKeyboardButton("📞 Telefone",        callback_data="modo_phone")],
        [InlineKeyboardButton("📧 Email",           callback_data="modo_email"),
         InlineKeyboardButton("🌐 Domínio",         callback_data="modo_domain")],
        [InlineKeyboardButton("🏢 CNPJ",            callback_data="modo_cnpj"),
         InlineKeyboardButton("📄 PDF",             callback_data="modo_pdf")],
        [InlineKeyboardButton("🧠 Chat IA",         callback_data="modo_ai")],
    ])

async def check_owner(update):
    if update.effective_user.id != OWNER_ID:
        await update.effective_message.reply_text("⛔ Acesso negado.")
        return False
    return True

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    await update.message.reply_text(
        "🔴 *REDNOVA* — Inteligência OSINT\n\n"
        "Manda qualquer coisa — domínio, CNPJ, email, username, nome...\n"
        "Ou fala comigo normalmente sobre pentest e bug bounty.",
        parse_mode=ParseMode.MARKDOWN, reply_markup=menu_kb())

async def cmd_limpar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    global _historico
    _historico = []
    ctx.user_data.clear()
    await update.message.reply_text("🗑️ Memória limpa.")

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu":
        await q.edit_message_text("🔴 *REDNOVA*", parse_mode=ParseMode.MARKDOWN, reply_markup=menu_kb())
        return

    if data.startswith("modo_"):
        modo = data[5:]
        ctx.user_data["modo"] = modo
        prompts = {
            "investigate": "🔍 Manda o alvo (CNPJ, domínio, email, username, nome):",
            "username":    "👤 Manda o username:",
            "phone":       "📞 Manda o telefone com DDD:",
            "email":       "📧 Manda o email:",
            "domain":      "🌐 Manda o domínio (ex: site.com):",
            "cnpj":        "🏢 Manda o CNPJ (14 dígitos):",
            "pdf":         "📄 Manda o alvo para gerar o PDF:",
            "ai":          "🧠 Fala comigo:",
        }
        await q.edit_message_text(prompts.get(modo, "Manda o alvo:"), parse_mode=ParseMode.MARKDOWN)
        return

    if data.startswith("pdf__"):
        target = data[5:]
        last = ctx.user_data.get("last_results")
        if last and last.get("target") == target:
            msg = await update.effective_message.reply_text("📄 Gerando PDF...")
            try:
                from pdf_generator import gerar as gerar_pdf
                pdf = await asyncio.to_thread(gerar_pdf, last)
                if pdf and os.path.exists(pdf):
                    with open(pdf,"rb") as f:
                        await update.effective_message.reply_document(f, filename=f"REDNOVA_{target}.pdf")
                    os.remove(pdf)
                    await msg.delete()
                else:
                    await msg.edit_text("❌ Erro ao gerar PDF.")
            except Exception as e:
                await msg.edit_text(f"❌ {e}")
        return

    if data.startswith("ai__"):
        target = data[4:]
        last = ctx.user_data.get("last_results",{})
        ctx_str = f"Investigação de '{target}' concluída. Analisa e dá os 3 próximos passos mais valiosos para bug bounty/pentest."
        await update.effective_message.chat.send_action("typing")
        resp = await asyncio.to_thread(ai_chat, ctx_str, json.dumps(last, ensure_ascii=False, default=str)[:3000])
        try:
            await update.effective_message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.effective_message.reply_text(resp)

async def run_investigation(update, ctx, target, modo="investigate"):
    status = await update.message.reply_text("🔴 Iniciando...")
    log = []
    def prog(msg):
        log.append(msg)
        asyncio.run_coroutine_threadsafe(
            status.edit_text("\n".join(log[-4:]), parse_mode=ParseMode.MARKDOWN),
            asyncio.get_event_loop()
        )
    try:
        results = await asyncio.to_thread(investigar, target, prog)
        await status.delete()

        if modo == "pdf":
            try:
                from pdf_generator import gerar as gerar_pdf
                pdf = await asyncio.to_thread(gerar_pdf, results)
                if pdf and os.path.exists(pdf):
                    with open(pdf,"rb") as f:
                        await update.message.reply_document(f, filename=f"REDNOVA_{target}.pdf",
                            caption=f"📄 `{target}`", parse_mode=ParseMode.MARKDOWN)
                    os.remove(pdf)
                else:
                    await update.message.reply_text("❌ Erro ao gerar PDF. Instala reportlab.")
            except Exception as e:
                await update.message.reply_text(f"❌ PDF: {e}")
        else:
            chunks = formatar(results)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN,
                                                 disable_web_page_preview=True)
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 PDF", callback_data=f"pdf__{target}"),
                 InlineKeyboardButton("🧠 Analisar IA", callback_data=f"ai__{target}")],
                [InlineKeyboardButton("◀️ Menu", callback_data="menu")],
            ])
            await update.message.reply_text("✅ *Pronto.*", parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            ctx.user_data["last_results"] = results

    except Exception as ex:
        try: await status.edit_text(f"❌ Erro: {ex}")
        except: await update.message.reply_text(f"❌ Erro: {ex}")

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    texto = update.message.text.strip()
    modo  = ctx.user_data.pop("modo", None)

    tipo = detect_type(texto)
    TIPOS_ALVO = {"cnpj","cpf","email","domain","phone"}

    CONVERSA = [
        "como","qual","quais","quando","onde","porque","pq","oque","o que",
        "analisa","explica","me diz","me da","me dá","faz","fazer",
        "ajuda","help","bom dia","boa tarde","boa noite","oi","ola","hey","opa",
        "tudo","beleza","valeu","obrigado","blz","tmj","eai","e ai","vlw",
        "pentest","vuln","exploit","payload","burp","nmap","nuclei","shodan",
        "finding","report","relatorio","contrato","scan","teste","wordlist",
        "sql","xss","idor","csrf","jwt","token","bypass","rce","lfi","ssrf",
        "recon","enum","fuzzing","brute","injection","shell","reverse","pivot",
        "próximos","proximo","passo","estrategia","estratégia","como fazer",
    ]

    eh_alvo = tipo in TIPOS_ALVO or modo in ("investigate","username","phone","email","domain","cnpj","pdf")
    eh_conversa = (
        modo == "ai" or
        not eh_alvo and (
            texto.endswith("?") or
            len(texto.split()) >= 3 or
            len(texto) <= 25 or
            any(p in texto.lower() for p in CONVERSA)
        )
    )

    if eh_conversa:
        await update.message.chat.send_action("typing")
        last = ctx.user_data.get("last_results",{})
        ctx_str = ""
        if last:
            ctx_str = f"Investigação recente: {last.get('target','')} ({last.get('tipo','')}). Risk: {last.get('risk_score',0)}. Emails: {last.get('emails',[])}. Redes: {list(last.get('redes',{}).keys())}."
        resposta = await asyncio.to_thread(ai_chat, texto, ctx_str)
        try:
            await update.message.reply_text(resposta, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.message.reply_text(resposta)
        return

    await run_investigation(update, ctx, texto, modo or "investigate")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("limpar",  cmd_limpar))
    app.add_handler(CommandHandler("menu",    start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🔴 REDNOVA iniciado.")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
