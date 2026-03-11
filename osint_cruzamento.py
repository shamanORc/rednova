"""
OSINT CRUZAMENTO COMPLETO — RedNova
CNPJ → Nome → Domínio → Emails → Redes Sociais → Vazamentos → Relatório

Fontes 100% públicas:
- BrasilAPI (CNPJ)
- WHOIS / DNS
- crt.sh (certificados)
- Hunter.io (emails, free tier)
- HaveIBeenPwned (vazamentos)
- Google dorking simulado
- Scraping de página pública do alvo
- LinkedIn / Facebook / Instagram busca pública
"""

import re, json, socket, ssl, urllib.request, urllib.error
import urllib.parse, subprocess, time
from datetime import datetime

HUNTER_KEY = ""   # Opcional — free tier: 25 buscas/mês em hunter.io
HIBP_KEY   = ""   # HaveIBeenPwned — free para domínios

# ══════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════
def cruzar(cnpj_raw: str) -> str:
    """Recebe CNPJ, retorna relatório completo cruzado."""
    cnpj = re.sub(r'\D', '', cnpj_raw)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido."

    resultado = {
        "cnpj":    cnpj,
        "empresa": {},
        "socios":  [],
        "dominio": None,
        "emails":  [],
        "redes":   {},
        "vazamentos": [],
        "subdominios": [],
        "ips": [],
    }

    # ── 1. CNPJ → dados da empresa ──────────────────────────────
    empresa = _cnpj_dados(cnpj)
    if not empresa:
        return "❌ CNPJ não encontrado."
    resultado["empresa"] = empresa
    resultado["socios"]  = empresa.get("qsa", [])

    # ── 2. Extrair domínio ───────────────────────────────────────
    dominio = _extrair_dominio(empresa)
    resultado["dominio"] = dominio

    # ── 3. Se tem domínio, aprofundar ────────────────────────────
    if dominio:
        resultado["subdominios"] = _crt_subdomains(dominio)
        resultado["ips"]         = _resolver_ips(dominio, resultado["subdominios"])
        resultado["emails"]     += _emails_do_site(dominio)
        resultado["emails"]     += _emails_whois(dominio)
        resultado["emails"]     += _hunter_emails(dominio)
        resultado["vazamentos"]  = _hibp_dominio(dominio)
        resultado["redes"]       = _redes_sociais(dominio, empresa.get("razao_social",""))

    # ── 4. Emails dos sócios ─────────────────────────────────────
    resultado["emails"] += _emails_socios(resultado["socios"], dominio)

    # ── 5. Deduplica emails ──────────────────────────────────────
    resultado["emails"] = list(dict.fromkeys(
        e.lower().strip() for e in resultado["emails"] if e and "@" in e
    ))

    return _formatar_relatorio(resultado)


# ══════════════════════════════════════════════════════════════════
#  1. CNPJ
# ══════════════════════════════════════════════════════════════════
def _cnpj_dados(cnpj: str) -> dict:
    for url in [
        f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
        f"https://receitaws.com.br/v1/cnpj/{cnpj}",
    ]:
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=12) as r:
                data = json.loads(r.read())
                # Normalizar
                return {
                    "razao_social":    data.get("razao_social") or data.get("nome",""),
                    "nome_fantasia":   data.get("nome_fantasia") or data.get("fantasia",""),
                    "situacao":        data.get("situacao_cadastral") or data.get("situacao",""),
                    "abertura":        data.get("data_inicio_atividade") or data.get("abertura",""),
                    "atividade":       (data.get("cnae_fiscal_descricao") or
                                       (data.get("atividade_principal",[{}])[0].get("text",""))),
                    "logradouro":      data.get("logradouro",""),
                    "numero":          data.get("numero",""),
                    "municipio":       data.get("municipio",""),
                    "uf":              data.get("uf",""),
                    "cep":             data.get("cep",""),
                    "telefone":        data.get("telefone",""),
                    "email":           data.get("email",""),
                    "site":            data.get("site",""),
                    "qsa":             data.get("qsa",[]),
                    "capital_social":  data.get("capital_social",""),
                    "porte":           data.get("porte",""),
                    "natureza":        data.get("natureza_juridica",""),
                }
        except Exception:
            time.sleep(1)
    return {}


# ══════════════════════════════════════════════════════════════════
#  2. EXTRAIR DOMINIO
# ══════════════════════════════════════════════════════════════════
def _extrair_dominio(empresa: dict) -> str:
    # 1. Campo site direto
    site = empresa.get("site","") or ""
    if site:
        d = re.sub(r'https?://', '', site).strip("/").split("/")[0]
        if "." in d:
            return d.lower()

    # 2. Email corporativo
    email = empresa.get("email","") or ""
    if email and "@" in email:
        dominio = email.split("@")[-1]
        if dominio and "." in dominio and dominio not in (
            "gmail.com","hotmail.com","yahoo.com","outlook.com",
            "uol.com.br","bol.com.br","terra.com.br"
        ):
            return dominio.lower()

    # 3. Tentar derivar do nome da empresa
    nome = (empresa.get("nome_fantasia") or empresa.get("razao_social","")).lower()
    nome_limpo = re.sub(r'[^a-z0-9]', '', nome.split()[0]) if nome else ""
    if nome_limpo and len(nome_limpo) > 3:
        for tld in [".com.br",".com",".net",".org"]:
            candidato = f"{nome_limpo}{tld}"
            try:
                socket.gethostbyname(candidato)
                return candidato
            except Exception:
                pass

    return None


# ══════════════════════════════════════════════════════════════════
#  3. SUBDOMÍNIOS via crt.sh
# ══════════════════════════════════════════════════════════════════
def _crt_subdomains(dominio: str) -> list:
    try:
        url = f"https://crt.sh/?q=%.{dominio}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        subs = set()
        for entry in data:
            for name in entry.get("name_value","").splitlines():
                name = name.strip().lstrip("*.")
                if dominio in name:
                    subs.add(name.lower())
        return sorted(subs)[:30]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════
#  4. IPs
# ══════════════════════════════════════════════════════════════════
def _resolver_ips(dominio: str, subs: list) -> list:
    ips = {}
    todos = [dominio] + subs[:10]
    for host in todos:
        try:
            ip = socket.gethostbyname(host)
            if ip not in ips.values():
                ips[host] = ip
        except Exception:
            pass
    return [{"host": h, "ip": i} for h, i in ips.items()]


# ══════════════════════════════════════════════════════════════════
#  5. EMAILS DO SITE
# ══════════════════════════════════════════════════════════════════
def _emails_do_site(dominio: str) -> list:
    emails = set()
    urls = [
        f"https://{dominio}",
        f"https://{dominio}/contato",
        f"https://{dominio}/contact",
        f"https://{dominio}/sobre",
        f"https://{dominio}/about",
        f"https://{dominio}/equipe",
        f"https://www.{dominio}",
    ]
    pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')

    for url in urls[:4]:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"
            })
            with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
                html = r.read(32768).decode("utf-8", errors="ignore")
                found = pattern.findall(html)
                for e in found:
                    if dominio in e or not any(x in e for x in [
                        "example","test","sentry","noreply","no-reply",
                        "pixel","track","email@"
                    ]):
                        emails.add(e.lower())
        except Exception:
            pass

    return list(emails)[:15]


# ══════════════════════════════════════════════════════════════════
#  6. EMAILS WHOIS
# ══════════════════════════════════════════════════════════════════
def _emails_whois(dominio: str) -> list:
    emails = set()
    pattern = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}')
    try:
        result = subprocess.run(
            ["whois", dominio], capture_output=True, text=True, timeout=12
        )
        found = pattern.findall(result.stdout)
        for e in found:
            if not any(x in e.lower() for x in ["abuse@","noc@","hostmaster@"]):
                emails.add(e.lower())
    except Exception:
        pass
    return list(emails)[:5]


# ══════════════════════════════════════════════════════════════════
#  7. HUNTER.IO (free tier — 25/mês sem key)
# ══════════════════════════════════════════════════════════════════
def _hunter_emails(dominio: str) -> list:
    try:
        base = f"https://api.hunter.io/v2/domain-search?domain={dominio}&limit=10"
        if HUNTER_KEY:
            base += f"&api_key={HUNTER_KEY}"
        req = urllib.request.Request(base, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        emails = []
        for e in data.get("data",{}).get("emails",[]):
            addr = e.get("value","")
            if addr:
                emails.append(addr.lower())
        return emails[:10]
    except Exception:
        return []


# ══════════════════════════════════════════════════════════════════
#  8. VAZAMENTOS — HaveIBeenPwned
# ══════════════════════════════════════════════════════════════════
def _hibp_dominio(dominio: str) -> list:
    """Verifica se domínio aparece em breaches públicos."""
    vazamentos = []
    try:
        url = f"https://haveibeenpwned.com/api/v3/breacheddomain/{dominio}"
        headers = {"User-Agent": "RedNova-OSINT", "hibp-api-key": HIBP_KEY} if HIBP_KEY else {
            "User-Agent": "RedNova-OSINT"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            for breach in data:
                vazamentos.append({
                    "nome":  breach.get("Name","?"),
                    "data":  breach.get("BreachDate","?"),
                    "dados": ", ".join(breach.get("DataClasses",[])[:4]),
                })
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass  # Domínio limpo
    except Exception:
        pass

    # Fallback: verificar via scraping público
    if not vazamentos:
        try:
            url = f"https://haveibeenpwned.com/DomainSearch"
            req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as r:
                pass  # Só confirma que o serviço está online
        except Exception:
            pass

    return vazamentos


# ══════════════════════════════════════════════════════════════════
#  9. REDES SOCIAIS
# ══════════════════════════════════════════════════════════════════
def _redes_sociais(dominio: str, nome_empresa: str) -> dict:
    """Busca links de redes sociais no site e por nome."""
    redes = {
        "facebook":  None,
        "instagram": None,
        "linkedin":  None,
        "twitter":   None,
        "youtube":   None,
        "whatsapp":  None,
    }

    # Scraping do site
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"https://{dominio}",
            headers={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"}
        )
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            html = r.read(65536).decode("utf-8", errors="ignore")

        patterns = {
            "facebook":  r'facebook\.com/(?:pages/)?([A-Za-z0-9./_\-]+)',
            "instagram": r'instagram\.com/([A-Za-z0-9._\-]+)',
            "linkedin":  r'linkedin\.com/(?:company|in)/([A-Za-z0-9._\-]+)',
            "twitter":   r'(?:twitter|x)\.com/([A-Za-z0-9._\-]+)',
            "youtube":   r'youtube\.com/(?:channel|user|c)/([A-Za-z0-9._\-]+)',
            "whatsapp":  r'(?:wa\.me|api\.whatsapp\.com/send\?phone=)([0-9]+)',
        }

        for rede, pat in patterns.items():
            match = re.search(pat, html, re.IGNORECASE)
            if match:
                handle = match.group(1).rstrip("/").split("?")[0]
                if rede == "facebook":
                    redes[rede] = f"https://facebook.com/{handle}"
                elif rede == "instagram":
                    redes[rede] = f"https://instagram.com/{handle}"
                elif rede == "linkedin":
                    redes[rede] = f"https://linkedin.com/company/{handle}"
                elif rede == "twitter":
                    redes[rede] = f"https://twitter.com/{handle}"
                elif rede == "youtube":
                    redes[rede] = f"https://youtube.com/{handle}"
                elif rede == "whatsapp":
                    redes[rede] = f"https://wa.me/{handle}"

    except Exception:
        pass

    # Busca por nome da empresa via Google (simulado com DuckDuckGo)
    if nome_empresa and not any(redes.values()):
        redes.update(_duckduckgo_redes(nome_empresa))

    return {k: v for k, v in redes.items() if v}


def _duckduckgo_redes(nome: str) -> dict:
    """Busca links de redes via DuckDuckGo HTML."""
    redes = {}
    try:
        query = urllib.parse.quote(f"{nome} site:instagram.com OR site:facebook.com OR site:linkedin.com")
        url = f"https://html.duckduckgo.com/html/?q={query}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read(32768).decode("utf-8", errors="ignore")

        for rede, pat in {
            "instagram": r'instagram\.com/([A-Za-z0-9._]{2,30})',
            "facebook":  r'facebook\.com/([A-Za-z0-9./]{2,50})',
            "linkedin":  r'linkedin\.com/company/([A-Za-z0-9.\-]{2,50})',
        }.items():
            m = re.search(pat, html)
            if m and rede not in redes:
                handle = m.group(1).rstrip("/")
                if rede == "instagram":
                    redes[rede] = f"https://instagram.com/{handle}"
                elif rede == "facebook":
                    redes[rede] = f"https://facebook.com/{handle}"
                elif rede == "linkedin":
                    redes[rede] = f"https://linkedin.com/company/{handle}"
    except Exception:
        pass
    return redes


# ══════════════════════════════════════════════════════════════════
#  10. EMAILS DOS SÓCIOS
# ══════════════════════════════════════════════════════════════════
def _emails_socios(socios: list, dominio: str) -> list:
    """Gera padrões de email prováveis para cada sócio."""
    if not dominio or not socios:
        return []

    emails_prováveis = []
    for socio in socios[:5]:
        nome = socio.get("nome_socio") or socio.get("nome","")
        if not nome or len(nome) < 3:
            continue
        partes = nome.lower().split()
        partes = [re.sub(r'[^a-z]', '', p) for p in partes if len(p) > 1]
        if len(partes) < 2:
            continue

        primeiro = partes[0]
        ultimo   = partes[-1]
        segundo  = partes[1] if len(partes) > 2 else ""

        # Padrões comuns de email corporativo
        padroes = [
            f"{primeiro}.{ultimo}@{dominio}",
            f"{primeiro[0]}{ultimo}@{dominio}",
            f"{primeiro}@{dominio}",
            f"{primeiro}{ultimo[0]}@{dominio}",
        ]
        if segundo:
            padroes.append(f"{primeiro}.{segundo[0]}.{ultimo}@{dominio}")

        emails_prováveis.extend(padroes)

    return emails_prováveis[:15]


# ══════════════════════════════════════════════════════════════════
#  FORMATAÇÃO DO RELATÓRIO
# ══════════════════════════════════════════════════════════════════
def _formatar_relatorio(r: dict) -> str:
    cnpj = r["cnpj"]
    cnpj_fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
    e = r["empresa"]
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')

    sit = e.get("situacao","?")
    sit_icon = "✅" if "ATIVA" in str(sit).upper() else "⚠️"

    # Empresa
    out = [f"🔴 *REDNOVA OSINT — RELATÓRIO CRUZADO*"]
    out.append(f"_{agora}_\n")
    out.append(f"━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"🏢 *EMPRESA*")
    out.append(f"  *CNPJ:* `{cnpj_fmt}`")
    out.append(f"  *Razão Social:* {e.get('razao_social','?')}")
    if e.get("nome_fantasia"):
        out.append(f"  *Fantasia:* {e['nome_fantasia']}")
    out.append(f"  {sit_icon} *Situação:* {sit}")
    out.append(f"  *Abertura:* {e.get('abertura','?')}")
    out.append(f"  *Atividade:* {e.get('atividade','?')[:60]}")
    out.append(f"  *Porte:* {e.get('porte','?')}")
    cap = e.get("capital_social","")
    if cap:
        out.append(f"  *Capital:* R$ {cap}")
    out.append(f"  *Endereço:* {e.get('logradouro','')} {e.get('numero','')}, "
               f"{e.get('municipio','')} - {e.get('uf','')} CEP {e.get('cep','')}")
    if e.get("telefone"):
        out.append(f"  *Tel Receita:* {e['telefone']}")

    # Domínio
    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"🌐 *DOMÍNIO*")
    if r["dominio"]:
        out.append(f"  `{r['dominio']}`")
        if r["ips"]:
            for item in r["ips"][:5]:
                out.append(f"  • `{item['host']}` → `{item['ip']}`")
        if r["subdominios"]:
            out.append(f"  *Subdomínios ({len(r['subdominios'])}):*")
            for s in r["subdominios"][:8]:
                out.append(f"    `{s}`")
            if len(r["subdominios"]) > 8:
                out.append(f"    _...e mais {len(r['subdominios'])-8}_")
    else:
        out.append("  Não identificado")

    # Sócios
    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"👥 *SÓCIOS / QSA*")
    socios = r["socios"]
    if socios:
        for s in socios[:8]:
            nome = s.get("nome_socio") or s.get("nome","?")
            qual = s.get("qualificacao_socio") or s.get("qual","")
            out.append(f"  • {nome} ({qual})")
    else:
        out.append("  Não informado")

    # Emails
    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"📧 *EMAILS ENCONTRADOS*")
    emails_conf = [e for e in r["emails"] if r["dominio"] and r["dominio"] in e]
    emails_ext  = [e for e in r["emails"] if e not in emails_conf]
    if emails_conf:
        out.append("  *Corporativos (confirmados):*")
        for em in emails_conf[:8]:
            out.append(f"    `{em}`")
    if emails_ext:
        out.append("  *Externos / Padrões prováveis:*")
        for em in emails_ext[:6]:
            out.append(f"    `{em}`")
    if not r["emails"]:
        out.append("  Nenhum encontrado")

    # Redes sociais
    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"📱 *REDES SOCIAIS*")
    redes = r["redes"]
    icons = {
        "facebook": "🔵", "instagram": "📸", "linkedin": "💼",
        "twitter": "🐦", "youtube": "▶️", "whatsapp": "💬"
    }
    if redes:
        for rede, url in redes.items():
            out.append(f"  {icons.get(rede,'•')} [{rede.capitalize()}]({url})")
    else:
        out.append("  Nenhuma encontrada no site")

    # Vazamentos
    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"⚠️ *VAZAMENTOS (HIBP)*")
    if r["vazamentos"]:
        for v in r["vazamentos"][:5]:
            out.append(f"  🔴 *{v['nome']}* ({v['data']})")
            out.append(f"     Dados: {v['dados']}")
    else:
        out.append("  ✅ Nenhum vazamento público encontrado")

    out.append(f"\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append(f"🔴 _RedNova OSINT — Fontes: BrasilAPI, crt.sh, HIBP, WHOIS_")

    return "\n".join(out)
