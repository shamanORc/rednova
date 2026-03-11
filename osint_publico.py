"""
OSINT FONTES PÚBLICAS PROFUNDO — RedNova
Google Dorks · DuckDuckGo · Bing · LinkedIn · Facebook · Instagram
Emails · Telefones · Vazamentos · Subdomínios · IPs · WHOIS
"""

import re, json, socket, ssl, time, urllib.request, urllib.error
import urllib.parse, subprocess
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  SCRAPER BASE — faz requisição e retorna HTML
# ══════════════════════════════════════════════════════════════════
def _get(url: str, referer: str = None, timeout: int = 10) -> str:
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        headers = {
            "User-Agent":      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 Chrome/122.0 Safari/537.36",
            "Accept":          "text/html,application/xhtml+xml,*/*;q=0.9",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
            "Accept-Encoding": "identity",
        }
        if referer:
            headers["Referer"] = referer
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read(131072).decode("utf-8", errors="ignore")
    except Exception:
        return ""

EMAIL_RE = re.compile(
    r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}'
)
PHONE_RE = re.compile(
    r'(?:\+55\s?)?(?:\(?\d{2}\)?\s?)?(?:9\d{4}|\d{4})[\s\-]?\d{4}'
)

LIXO_EMAILS = {
    "gmail.com","hotmail.com","yahoo.com","outlook.com","icloud.com",
    "uol.com.br","bol.com.br","terra.com.br","ig.com.br","r7.com",
    "example.com","test.com","sentry.io","wixpress.com",
}

def _limpar_emails(emails: list, dominio: str = None) -> list:
    limpos = []
    vistos = set()
    for e in emails:
        e = e.lower().strip().strip(".,;")
        dom = e.split("@")[-1] if "@" in e else ""
        if (e not in vistos
                and len(e) > 6
                and "." in dom
                and not any(x in e for x in ["noreply","no-reply","pixel","track","@2x","@3x"])
                and dom not in LIXO_EMAILS):
            limpos.append(e)
            vistos.add(e)
    # Priorizar emails do domínio alvo
    if dominio:
        limpos.sort(key=lambda x: (0 if dominio in x else 1))
    return limpos[:25]


# ══════════════════════════════════════════════════════════════════
#  GOOGLE DORKS
# ══════════════════════════════════════════════════════════════════
def google_dork(query: str) -> str:
    """Busca no Google via HTML público."""
    q = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={q}&num=20&hl=pt-BR"
    html = _get(url)
    if not html:
        # Fallback DuckDuckGo
        url = f"https://html.duckduckgo.com/html/?q={q}"
        html = _get(url)
    return html

def dork_emails(dominio: str) -> list:
    """Google dork para emails do domínio."""
    emails = []
    queries = [
        f'site:{dominio} email',
        f'"{dominio}" email contact',
        f'intext:"@{dominio}"',
        f'site:{dominio} "fale conosco"',
        f'site:{dominio} "@{dominio}"',
    ]
    for q in queries[:3]:
        html = google_dork(q)
        found = EMAIL_RE.findall(html)
        emails.extend(found)
        time.sleep(1.5)
    return emails

def dork_redes(nome_empresa: str, dominio: str) -> dict:
    """Google dork para redes sociais."""
    redes = {}
    nome_enc = urllib.parse.quote(f'"{nome_empresa}"')

    buscas = {
        "linkedin":  f'site:linkedin.com/company {nome_enc}',
        "instagram": f'site:instagram.com {nome_enc}',
        "facebook":  f'site:facebook.com {nome_enc}',
        "youtube":   f'site:youtube.com {nome_enc}',
    }

    padroes = {
        "linkedin":  r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})',
        "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)',
        "facebook":  r'facebook\.com/(?:pages/[^/]+/)?([A-Za-z0-9\._\-]{2,80})',
        "youtube":   r'youtube\.com/(?:channel/|user/|@|c/)([A-Za-z0-9\._\-]{2,80})',
    }

    bases = {
        "linkedin":  "https://linkedin.com/company/",
        "instagram": "https://instagram.com/",
        "facebook":  "https://facebook.com/",
        "youtube":   "https://youtube.com/@",
    }

    for rede, query in buscas.items():
        html = google_dork(query)
        m = re.search(padroes[rede], html, re.IGNORECASE)
        if m:
            handle = m.group(1).rstrip("/").split("?")[0]
            # Filtrar handles genéricos
            if handle.lower() not in ("login","sharer","share","watch","search",
                                       "feed","home","jobs","pages"):
                redes[rede] = bases[rede] + handle
        time.sleep(1.2)

    return redes


# ══════════════════════════════════════════════════════════════════
#  SCRAPING DIRETO DO SITE
# ══════════════════════════════════════════════════════════════════
def scrape_site(dominio: str) -> dict:
    """Scraping profundo: emails, telefones, redes, WhatsApp."""
    resultado = {"emails": [], "telefones": [], "redes": {}, "whatsapp": None}

    urls_tentar = [
        f"https://{dominio}",
        f"https://www.{dominio}",
        f"https://{dominio}/contato",
        f"https://{dominio}/contact",
        f"https://{dominio}/sobre",
        f"https://{dominio}/about",
        f"https://{dominio}/fale-conosco",
        f"https://{dominio}/quem-somos",
    ]

    todo_html = ""
    for url in urls_tentar[:5]:
        html = _get(url)
        if html:
            todo_html += html
            time.sleep(0.5)

    if not todo_html:
        return resultado

    # Emails
    resultado["emails"] = EMAIL_RE.findall(todo_html)

    # Telefones
    fones = PHONE_RE.findall(todo_html)
    resultado["telefones"] = list(set(fones))[:8]

    # WhatsApp
    wa = re.search(r'(?:wa\.me|api\.whatsapp\.com/send\?phone=)([0-9]{10,15})', todo_html)
    if wa:
        resultado["whatsapp"] = f"https://wa.me/{wa.group(1)}"

    # Redes no HTML do site
    padroes_redes = {
        "facebook":  r'(?:facebook\.com/)([A-Za-z0-9\./_\-]{2,80})',
        "instagram": r'(?:instagram\.com/)([A-Za-z0-9\._]{2,40})',
        "linkedin":  r'(?:linkedin\.com/(?:company|in)/)([A-Za-z0-9\._\-]{2,60})',
        "twitter":   r'(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,40})',
        "youtube":   r'youtube\.com/(?:channel/|user/|@|c/)([A-Za-z0-9\._\-]{2,80})',
        "tiktok":    r'tiktok\.com/@([A-Za-z0-9\._]{2,40})',
        "telegram":  r't\.me/([A-Za-z0-9_]{2,40})',
    }
    links_base = {
        "facebook":  "https://facebook.com/",
        "instagram": "https://instagram.com/",
        "linkedin":  "https://linkedin.com/company/",
        "twitter":   "https://twitter.com/",
        "youtube":   "https://youtube.com/@",
        "tiktok":    "https://tiktok.com/@",
        "telegram":  "https://t.me/",
    }
    ignorar = {"login","sharer","share","dialog","oauth","plugins",
               "legal","privacy","terms","help","support","ads"}

    for rede, pat in padroes_redes.items():
        m = re.search(pat, todo_html, re.IGNORECASE)
        if m:
            handle = m.group(1).rstrip("/").split("?")[0].split("#")[0]
            if handle.lower() not in ignorar and len(handle) > 1:
                resultado["redes"][rede] = links_base[rede] + handle

    return resultado


# ══════════════════════════════════════════════════════════════════
#  LINKEDIN PÚBLICO
# ══════════════════════════════════════════════════════════════════
def linkedin_empresa(nome: str) -> dict:
    """Busca página pública da empresa no LinkedIn."""
    resultado = {"url": None, "funcionarios": None, "setor": None}
    try:
        query = urllib.parse.quote(f"{nome} empresa")
        url = f"https://www.linkedin.com/search/results/companies/?keywords={query}"
        html = _get(url)
        m = re.search(r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})', html)
        if m:
            slug = m.group(1)
            resultado["url"] = f"https://linkedin.com/company/{slug}"
    except Exception:
        pass
    return resultado


# ══════════════════════════════════════════════════════════════════
#  INSTAGRAM PÚBLICO
# ══════════════════════════════════════════════════════════════════
def instagram_perfil(handle: str) -> dict:
    """Dados públicos do perfil Instagram."""
    dados = {"seguidores": None, "bio": None, "posts": None, "url": None}
    try:
        url = f"https://www.instagram.com/{handle}/"
        html = _get(url)
        # Seguidores
        m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
        if m:
            dados["seguidores"] = int(m.group(1))
        # Bio
        m = re.search(r'"biography":"([^"]{0,300})"', html)
        if m:
            dados["bio"] = m.group(1)
        # Posts
        m = re.search(r'"edge_owner_to_timeline_media":\{"count":(\d+)', html)
        if m:
            dados["posts"] = int(m.group(1))
        dados["url"] = url
    except Exception:
        pass
    return dados


# ══════════════════════════════════════════════════════════════════
#  FACEBOOK PÚBLICO
# ══════════════════════════════════════════════════════════════════
def facebook_pagina(handle: str) -> dict:
    """Dados públicos da página Facebook."""
    dados = {"curtidas": None, "url": None, "telefone": None, "email": None}
    try:
        url = f"https://www.facebook.com/{handle}"
        html = _get(url)
        # Curtidas/seguidores
        m = re.search(r'([\d,\.]+)\s+(?:curtidas|likes|seguidores|followers)', html, re.IGNORECASE)
        if m:
            dados["curtidas"] = m.group(1)
        # Email na página
        emails = EMAIL_RE.findall(html)
        if emails:
            dados["email"] = emails[0]
        # Telefone
        fones = PHONE_RE.findall(html)
        if fones:
            dados["telefone"] = fones[0]
        dados["url"] = url
    except Exception:
        pass
    return dados


# ══════════════════════════════════════════════════════════════════
#  EMAILS VIA PADRÕES DOS SÓCIOS
# ══════════════════════════════════════════════════════════════════
def emails_socios(socios: list, dominio: str) -> list:
    if not dominio or not socios:
        return []
    emails = []
    for s in socios[:6]:
        nome = s.get("nome_socio") or s.get("nome","")
        if not nome:
            continue
        partes = [re.sub(r'[^a-z]','', p) for p in nome.lower().split() if len(p) > 1]
        partes = [p for p in partes if p not in ('de','da','do','dos','das','e','a')]
        if len(partes) < 2:
            continue
        p, u = partes[0], partes[-1]
        for padrao in [
            f"{p}.{u}@{dominio}",
            f"{p[0]}{u}@{dominio}",
            f"{p}@{dominio}",
            f"{p}{u[0]}@{dominio}",
            f"{u}.{p}@{dominio}",
        ]:
            emails.append(padrao)
    return emails[:20]


# ══════════════════════════════════════════════════════════════════
#  VAZAMENTOS PÚBLICOS
# ══════════════════════════════════════════════════════════════════
def verificar_vazamentos(dominio: str) -> list:
    vazamentos = []
    # DeHashed public search (sem key)
    try:
        url = f"https://haveibeenpwned.com/api/v3/breaches"
        req = urllib.request.Request(url, headers={"User-Agent":"RedNova-OSINT"})
        with urllib.request.urlopen(req, timeout=10) as r:
            todos = json.loads(r.read())
        for b in todos:
            if dominio.split(".")[0].lower() in b.get("Domain","").lower():
                vazamentos.append({
                    "nome":  b.get("Name"),
                    "data":  b.get("BreachDate"),
                    "contas": b.get("PwnCount",0),
                    "dados": ", ".join(b.get("DataClasses",[])[:4]),
                })
    except Exception:
        pass
    return vazamentos[:5]


# ══════════════════════════════════════════════════════════════════
#  DNS PROFUNDO
# ══════════════════════════════════════════════════════════════════
def dns_profundo(dominio: str) -> dict:
    resultado = {"registros": {}, "ip_real": None, "spf": [], "mx": []}

    for rt in ["A","AAAA","MX","NS","TXT","CNAME","SOA"]:
        try:
            r = subprocess.run(
                ["dig","+short", rt, dominio],
                capture_output=True, text=True, timeout=8
            )
            vals = [v.strip() for v in r.stdout.splitlines() if v.strip()]
            if vals:
                resultado["registros"][rt] = vals

                if rt == "MX":
                    resultado["mx"] = vals
                elif rt == "TXT":
                    for v in vals:
                        if "spf" in v.lower() or "ip4:" in v.lower():
                            resultado["spf"].append(v)
                            # Extrair IPs do SPF
                            ips = re.findall(r'ip4:(\d+\.\d+\.\d+\.\d+)', v)
                            if ips:
                                resultado["ip_real"] = ips[0]
        except Exception:
            pass

    # Se não achou IP real via SPF, tentar via MX
    if not resultado["ip_real"] and resultado["mx"]:
        for mx in resultado["mx"]:
            partes = mx.split()
            host = partes[-1].rstrip(".") if partes else ""
            if host:
                try:
                    ip = socket.gethostbyname(host)
                    resultado["ip_real"] = ip
                    break
                except Exception:
                    pass

    return resultado


# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT COMPLETO
# ══════════════════════════════════════════════════════════════════
def osint_completo(cnpj_raw: str = None, dominio_raw: str = None,
                   nome_raw: str = None) -> str:
    """
    Aceita CNPJ, domínio ou nome de empresa.
    Cruza tudo e retorna relatório completo.
    """
    from osint_cnpj import consultar as _cnpj_api, limpar_cnpj

    dados = {
        "cnpj":       None,
        "empresa":    {},
        "socios":     [],
        "dominio":    None,
        "dns":        {},
        "subdominios":[],
        "ips":        [],
        "emails":     [],
        "telefones":  [],
        "redes":      {},
        "instagram":  {},
        "facebook":   {},
        "linkedin":   {},
        "vazamentos": [],
    }

    # ── Pegar dados empresa via CNPJ ─────────────────────────────
    if cnpj_raw:
        from osint_cruzamento import _cnpj_dados, _extrair_dominio
        cnpj = limpar_cnpj(cnpj_raw)
        dados["cnpj"] = cnpj
        empresa = _cnpj_dados(cnpj)
        dados["empresa"] = empresa
        dados["socios"]  = empresa.get("qsa",[])
        dominio = dominio_raw or _extrair_dominio(empresa)
        dados["dominio"] = dominio
        if empresa.get("email"):
            dados["emails"].append(empresa["email"])
        if empresa.get("telefone"):
            dados["telefones"].append(empresa["telefone"])

    elif dominio_raw:
        dados["dominio"] = dominio_raw.replace("https://","").replace("http://","").strip("/")

    nome_empresa = (dados["empresa"].get("nome_fantasia") or
                    dados["empresa"].get("razao_social") or
                    nome_raw or "")

    dominio = dados["dominio"]

    # ── DNS profundo ─────────────────────────────────────────────
    if dominio:
        print(f"  [DNS] {dominio}")
        dados["dns"] = dns_profundo(dominio)

        # ── Subdomínios ──────────────────────────────────────────
        print(f"  [CRT] subdomínios...")
        from osint_cruzamento import _crt_subdomains, _resolver_ips
        dados["subdominios"] = _crt_subdomains(dominio)
        dados["ips"]         = _resolver_ips(dominio, dados["subdominios"])

        # ── Scraping profundo do site ────────────────────────────
        print(f"  [SITE] scraping...")
        site_data = scrape_site(dominio)
        dados["emails"]    += site_data["emails"]
        dados["telefones"] += site_data["telefones"]
        dados["redes"].update(site_data["redes"])
        if site_data.get("whatsapp"):
            dados["redes"]["whatsapp"] = site_data["whatsapp"]

        # ── Google dorks ─────────────────────────────────────────
        print(f"  [DORK] emails...")
        dados["emails"] += dork_emails(dominio)

        # ── Vazamentos ───────────────────────────────────────────
        print(f"  [HIBP] vazamentos...")
        dados["vazamentos"] = verificar_vazamentos(dominio)

    # ── Redes via Google dork ─────────────────────────────────────
    if nome_empresa:
        print(f"  [REDES] {nome_empresa}...")
        redes_dork = dork_redes(nome_empresa, dominio or "")
        for k, v in redes_dork.items():
            if k not in dados["redes"]:
                dados["redes"][k] = v

    # ── Detalhes Instagram ────────────────────────────────────────
    if "instagram" in dados["redes"]:
        handle = dados["redes"]["instagram"].split("instagram.com/")[-1].rstrip("/")
        print(f"  [IG] @{handle}...")
        dados["instagram"] = instagram_perfil(handle)

    # ── Detalhes Facebook ─────────────────────────────────────────
    if "facebook" in dados["redes"]:
        handle = dados["redes"]["facebook"].split("facebook.com/")[-1].rstrip("/")
        print(f"  [FB] {handle}...")
        fb = facebook_pagina(handle)
        dados["facebook"] = fb
        if fb.get("email"):
            dados["emails"].append(fb["email"])
        if fb.get("telefone"):
            dados["telefones"].append(fb["telefone"])

    # ── Emails dos sócios ─────────────────────────────────────────
    if dominio and dados["socios"]:
        dados["emails"] += emails_socios(dados["socios"], dominio)

    # ── Limpar e deduplicar ───────────────────────────────────────
    dados["emails"]    = _limpar_emails(dados["emails"], dominio)
    dados["telefones"] = list(dict.fromkeys(dados["telefones"]))[:8]

    return _formatar_completo(dados)


# ══════════════════════════════════════════════════════════════════
#  FORMATAÇÃO FINAL
# ══════════════════════════════════════════════════════════════════
def _formatar_completo(d: dict) -> str:
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    e = d.get("empresa",{})
    cnpj = d.get("cnpj","")
    cnpj_fmt = (f"`{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}`"
                if cnpj and len(cnpj)==14 else "—")

    sit = e.get("situacao","")
    sit_icon = "✅" if "ATIVA" in str(sit).upper() else ("⚠️" if sit else "")
    out = []

    out.append("🔴 *REDNOVA — OSINT COMPLETO*")
    out.append(f"_{agora}_")

    # ── Empresa ──────────────────────────────────────────────────
    if e:
        out.append("\n━━━━ 🏢 EMPRESA ━━━━")
        out.append(f"*CNPJ:* {cnpj_fmt}")
        out.append(f"*Razão Social:* {e.get('razao_social','?')}")
        if e.get("nome_fantasia"):
            out.append(f"*Fantasia:* {e['nome_fantasia']}")
        if sit:
            out.append(f"*Situação:* {sit_icon} {sit}")
        out.append(f"*Abertura:* {e.get('abertura','?')}")
        out.append(f"*Atividade:* {str(e.get('atividade','?'))[:70]}")
        out.append(f"*Porte:* {e.get('porte','?')} | *Capital:* R$ {e.get('capital_social','?')}")
        end = f"{e.get('logradouro','')} {e.get('numero','')}, {e.get('municipio','')} - {e.get('uf','')}".strip(", ")
        if end.strip():
            out.append(f"*Endereço:* {end}")

    # ── Sócios ───────────────────────────────────────────────────
    socios = d.get("socios",[])
    if socios:
        out.append("\n━━━━ 👥 SÓCIOS ━━━━")
        for s in socios[:6]:
            nome = s.get("nome_socio") or s.get("nome","?")
            qual = s.get("qualificacao_socio") or s.get("qual","")
            out.append(f"• {nome} _{qual}_")

    # ── Domínio / DNS / IPs ───────────────────────────────────────
    dom = d.get("dominio")
    if dom:
        out.append(f"\n━━━━ 🌐 DOMÍNIO: `{dom}` ━━━━")
        dns = d.get("dns",{})
        reg = dns.get("registros",{})
        if reg.get("A"):
            out.append(f"*IP:* `{'` | `'.join(reg['A'][:3])}`")
        if reg.get("NS"):
            out.append(f"*NS:* {' | '.join(reg['NS'][:3])}")
        if reg.get("MX"):
            out.append(f"*MX:* {' | '.join(reg['MX'][:2])}")
        if dns.get("ip_real"):
            out.append(f"⚠️ *IP REAL (bypass CDN):* `{dns['ip_real']}`")
        subs = d.get("subdominios",[])
        if subs:
            out.append(f"*Subdomínios ({len(subs)}):* " +
                       " | ".join(f"`{s}`" for s in subs[:6]) +
                       (f" _+{len(subs)-6} mais_" if len(subs)>6 else ""))

    # ── Emails ───────────────────────────────────────────────────
    emails = d.get("emails",[])
    if emails:
        out.append(f"\n━━━━ 📧 EMAILS ({len(emails)}) ━━━━")
        # Separar corporativos e externos
        corp = [e for e in emails if dom and dom in e]
        ext  = [e for e in emails if e not in corp]
        if corp:
            out.append("*Corporativos:*")
            for em in corp[:8]:
                out.append(f"  `{em}`")
        if ext:
            out.append("*Outros / Padrões:*")
            for em in ext[:6]:
                out.append(f"  `{em}`")
    else:
        out.append("\n📧 *Emails:* Nenhum encontrado")

    # ── Telefones ────────────────────────────────────────────────
    fones = d.get("telefones",[])
    if fones:
        out.append(f"\n━━━━ 📞 TELEFONES ━━━━")
        for f in fones[:5]:
            out.append(f"  `{f}`")

    # ── Redes Sociais ─────────────────────────────────────────────
    redes = d.get("redes",{})
    icons = {
        "facebook":"🔵","instagram":"📸","linkedin":"💼",
        "twitter":"🐦","youtube":"▶️","whatsapp":"💬",
        "tiktok":"🎵","telegram":"✈️"
    }
    if redes:
        out.append(f"\n━━━━ 📱 REDES SOCIAIS ━━━━")
        for rede, url in redes.items():
            out.append(f"{icons.get(rede,'•')} [{rede.capitalize()}]({url})")

        # Detalhes Instagram
        ig = d.get("instagram",{})
        if ig.get("seguidores"):
            seg = f"{ig['seguidores']:,}".replace(",",".")
            out.append(f"\n  📸 *Instagram:* {seg} seguidores"
                       + (f" · {ig['posts']} posts" if ig.get('posts') else ""))
            if ig.get("bio"):
                bio = ig['bio'][:100]
                out.append(f"  Bio: _{bio}_")

        # Detalhes Facebook
        fb = d.get("facebook",{})
        if fb.get("curtidas"):
            out.append(f"  🔵 *Facebook:* {fb['curtidas']} curtidas/seguidores")

    # ── Vazamentos ───────────────────────────────────────────────
    vaz = d.get("vazamentos",[])
    out.append(f"\n━━━━ ⚠️ VAZAMENTOS ━━━━")
    if vaz:
        for v in vaz:
            contas = f"{v.get('contas',0):,}".replace(",",".")
            out.append(f"🔴 *{v['nome']}* ({v['data']}) — {contas} contas")
            out.append(f"   Dados: _{v['dados']}_")
    else:
        out.append("✅ Nenhum vazamento encontrado")

    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append("🔴 _RedNova OSINT · BrasilAPI · crt.sh · HIBP · DNS · Scraping público_")

    return "\n".join(out)
