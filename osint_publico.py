"""
REDNOVA OSINT PUBLICO v2 — Fontes completas
BrasilAPI · registro.br · crt.sh · HIBP · LinkedIn · Instagram · Facebook · JusBrasil · Google
"""
import re, json, socket, ssl, time, urllib.request, urllib.error, urllib.parse, subprocess
from datetime import datetime

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}')
PHONE_RE = re.compile(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})[\s\-]?\d{4}')
LIXO = {"gmail.com","hotmail.com","yahoo.com","outlook.com","icloud.com",
        "uol.com.br","bol.com.br","terra.com.br","ig.com.br","example.com",
        "sentry.io","wixpress.com","noreply.com"}

def _get(url, timeout=10):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0",
            "Accept": "text/html,application/xhtml+xml,*/*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read(131072).decode("utf-8", errors="ignore")
    except:
        return ""

def _get_json(url, timeout=10):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read())
    except:
        return None

# ══════════════════════════════════════════════
# CNPJ
# ══════════════════════════════════════════════
SITUACOES = {
    "1": "NULA", "2": "ATIVA", "3": "SUSPENSA",
    "4": "INAPTA", "8": "BAIXADA", "": "DESCONHECIDA"
}

def _cnpj_dados(cnpj):
    for url in [
        f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
        f"https://receitaws.com.br/v1/cnpj/{cnpj}",
    ]:
        try:
            data = _get_json(url)
            if not data:
                continue
            sit_raw = str(data.get("situacao_cadastral") or data.get("situacao",""))
            sit = SITUACOES.get(sit_raw, sit_raw) if sit_raw.isdigit() else sit_raw
            return {
                "razao_social":  data.get("razao_social") or data.get("nome",""),
                "nome_fantasia": data.get("nome_fantasia") or data.get("fantasia",""),
                "situacao":      sit,
                "abertura":      data.get("data_inicio_atividade") or data.get("abertura",""),
                "atividade":     (data.get("cnae_fiscal_descricao") or
                                  (data.get("atividade_principal",[{}])[0].get("text",""))),
                "logradouro":    data.get("logradouro",""),
                "numero":        data.get("numero",""),
                "municipio":     data.get("municipio",""),
                "uf":            data.get("uf",""),
                "cep":           data.get("cep",""),
                "telefone":      data.get("telefone",""),
                "email":         data.get("email",""),
                "qsa":           data.get("qsa",[]),
                "capital_social":data.get("capital_social",""),
                "porte":         data.get("porte",""),
            }
        except:
            time.sleep(1)
    return {}

def _extrair_dominio(empresa):
    site = empresa.get("site","") or ""
    if site:
        d = re.sub(r'https?://','',site).strip("/").split("/")[0]
        if "." in d: return d.lower()
    email = empresa.get("email","") or ""
    if "@" in email:
        dom = email.split("@")[-1]
        if dom and "." in dom and dom not in LIXO:
            return dom.lower()
    # Derivar do nome
    nome = (empresa.get("nome_fantasia") or empresa.get("razao_social","")).lower()
    nome_limpo = re.sub(r'[^a-z0-9]','', nome.split()[0]) if nome else ""
    if nome_limpo and len(nome_limpo) > 3:
        for tld in [".com.br",".com",".net",".org.br"]:
            try:
                socket.gethostbyname(f"{nome_limpo}{tld}")
                return f"{nome_limpo}{tld}"
            except: pass
    return None

# ══════════════════════════════════════════════
# REGISTRO.BR
# ══════════════════════════════════════════════
def _registro_br(dominio):
    dados = {}
    try:
        result = subprocess.run(
            ["whois", "-h", "whois.registro.br", dominio],
            capture_output=True, text=True, timeout=12
        )
        txt = result.stdout
        for line in txt.splitlines():
            l = line.lower()
            if "owner:" in l:
                dados["owner"] = line.split(":",1)[-1].strip()
            elif "owner-c:" in l:
                dados["owner_c"] = line.split(":",1)[-1].strip()
            elif "country:" in l:
                dados["country"] = line.split(":",1)[-1].strip()
            elif "created:" in l:
                dados["created"] = line.split(":",1)[-1].strip()
            elif "changed:" in l:
                dados["changed"] = line.split(":",1)[-1].strip()
            elif "phone:" in l:
                dados.setdefault("phones",[]).append(line.split(":",1)[-1].strip())
            elif "e-mail:" in l or "email:" in l:
                dados.setdefault("emails",[]).append(line.split(":",1)[-1].strip())
            elif "nic-hdl-br:" in l:
                dados.setdefault("nic",[]).append(line.split(":",1)[-1].strip())
        # API JSON do registro.br
        api = _get_json(f"https://rdap.registro.br/domain/{dominio}")
        if api:
            for entity in api.get("entities",[]):
                for role in entity.get("roles",[]):
                    if role in ("registrant","administrative","technical"):
                        vcard = entity.get("vcardArray",["",{}])
                        if len(vcard) > 1:
                            for item in vcard[1]:
                                if item[0] == "fn":
                                    dados.setdefault("contatos",[]).append(item[3])
                                elif item[0] == "tel":
                                    dados.setdefault("phones",[]).append(item[3])
                                elif item[0] == "email":
                                    dados.setdefault("emails",[]).append(item[3])
    except: pass
    return dados

# ══════════════════════════════════════════════
# SUBDOMÍNIOS
# ══════════════════════════════════════════════
def _crt_subdomains(dominio):
    try:
        data = _get_json(f"https://crt.sh/?q=%.{dominio}&output=json")
        if not data: return []
        subs = set()
        for e in data:
            for name in e.get("name_value","").splitlines():
                name = name.strip().lstrip("*.")
                if dominio in name:
                    subs.add(name.lower())
        return sorted(subs)[:30]
    except: return []

# ══════════════════════════════════════════════
# SCRAPING DO SITE
# ══════════════════════════════════════════════
def _scrape_site(dominio):
    res = {"emails":[], "phones":[], "redes":{}}
    urls = [f"https://{dominio}", f"https://www.{dominio}",
            f"https://{dominio}/contato", f"https://{dominio}/sobre"]
    html_total = ""
    for url in urls[:4]:
        h = _get(url)
        if h:
            html_total += h
            time.sleep(0.5)
    if not html_total:
        return res
    res["emails"] = list(set(EMAIL_RE.findall(html_total)))
    res["phones"] = list(set(PHONE_RE.findall(html_total)))[:8]
    # WhatsApp
    wa = re.search(r'(?:wa\.me|whatsapp\.com/send\?phone=)([0-9]{10,15})', html_total)
    if wa:
        res["redes"]["whatsapp"] = f"https://wa.me/{wa.group(1)}"
    # Redes
    pats = {
        "facebook":  r'facebook\.com/(?!sharer|share|dialog|login|legal|privacy)([A-Za-z0-9\./_\-]{2,60})',
        "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)',
        "linkedin":  r'linkedin\.com/(?:company|in)/([A-Za-z0-9\._\-]{2,60})',
        "youtube":   r'youtube\.com/(?:@|channel/|user/|c/)([A-Za-z0-9\._\-]{2,60})',
        "tiktok":    r'tiktok\.com/@([A-Za-z0-9\._]{2,40})',
        "twitter":   r'(?:twitter|x)\.com/([A-Za-z0-9_]{2,40})',
    }
    bases = {
        "facebook":"https://facebook.com/","instagram":"https://instagram.com/",
        "linkedin":"https://linkedin.com/company/","youtube":"https://youtube.com/@",
        "tiktok":"https://tiktok.com/@","twitter":"https://twitter.com/",
    }
    ignorar = {"login","sharer","share","watch","home","feed","legal","privacy","terms","ads","help"}
    for rede, pat in pats.items():
        m = re.search(pat, html_total, re.IGNORECASE)
        if m:
            handle = m.group(1).rstrip("/").split("?")[0].split("#")[0]
            if handle.lower() not in ignorar and len(handle) > 1:
                res["redes"][rede] = bases[rede] + handle
    return res

# ══════════════════════════════════════════════
# GOOGLE/DUCKDUCKGO DORK
# ══════════════════════════════════════════════
def _dork(query):
    q = urllib.parse.quote(query)
    for url in [
        f"https://html.duckduckgo.com/html/?q={q}",
        f"https://www.bing.com/search?q={q}",
    ]:
        h = _get(url)
        if h and len(h) > 500:
            return h
    return ""

def _dork_redes(nome, dominio=""):
    redes = {}
    buscas = {
        "linkedin":  f'"{nome}" site:linkedin.com/company',
        "instagram": f'"{nome}" site:instagram.com',
        "facebook":  f'"{nome}" site:facebook.com',
    }
    pats = {
        "linkedin":  r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})',
        "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})',
        "facebook":  r'facebook\.com/([A-Za-z0-9\._/\-]{2,80})',
    }
    bases = {
        "linkedin":"https://linkedin.com/company/",
        "instagram":"https://instagram.com/",
        "facebook":"https://facebook.com/",
    }
    ignorar = {"login","sharer","share","watch","home","feed","pages","groups","events"}
    for rede, query in buscas.items():
        html = _dork(query)
        m = re.search(pats[rede], html, re.IGNORECASE)
        if m:
            handle = m.group(1).rstrip("/").split("?")[0]
            if handle.lower() not in ignorar:
                redes[rede] = bases[rede] + handle
        time.sleep(1)
    return redes

def _dork_pessoa(nome):
    """Busca pessoa por nome — JusBrasil, LinkedIn, emprego."""
    resultado = {}
    # JusBrasil
    html = _dork(f'"{nome}" site:jusbrasil.com.br')
    m = re.search(r'jusbrasil\.com\.br/(?:artigos|noticias|jurisprudencia|diarios)/[^\s"<>]{5,80}', html)
    if m:
        resultado["jusbrasil"] = f"https://{m.group(0)}"
    # LinkedIn pessoal
    html2 = _dork(f'"{nome}" site:linkedin.com/in')
    m2 = re.search(r'linkedin\.com/in/([A-Za-z0-9\-_\.]{2,60})', html2)
    if m2:
        resultado["linkedin_pessoal"] = f"https://linkedin.com/in/{m2.group(1)}"
    # Empregos
    html3 = _dork(f'"{nome}" currículo OR emprego OR trabalha')
    if nome.lower() in html3.lower():
        resultado["mencoes_emprego"] = "Encontradas menções públicas"
    return resultado

# ══════════════════════════════════════════════
# INSTAGRAM PÚBLICO
# ══════════════════════════════════════════════
def _instagram_info(handle):
    dados = {}
    try:
        url = f"https://www.instagram.com/{handle}/?__a=1&__d=dis"
        html = _get(url)
        m = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
        if m: dados["seguidores"] = f"{int(m.group(1)):,}".replace(",",".")
        m2 = re.search(r'"biography":"([^"]{0,200})"', html)
        if m2: dados["bio"] = m2.group(1)
        m3 = re.search(r'"full_name":"([^"]{0,80})"', html)
        if m3: dados["nome"] = m3.group(1)
    except: pass
    return dados

# ══════════════════════════════════════════════
# HIBP VAZAMENTOS
# ══════════════════════════════════════════════
def _hibp(dominio):
    vazamentos = []
    try:
        # Buscar na lista pública de breaches e filtrar pelo domínio
        data = _get_json("https://haveibeenpwned.com/api/v3/breaches")
        if data:
            nome_base = dominio.split(".")[0].lower()
            for b in data:
                bd = b.get("Domain","").lower()
                bn = b.get("Name","").lower()
                if nome_base in bd or nome_base in bn:
                    vazamentos.append({
                        "nome":   b.get("Name","?"),
                        "data":   b.get("BreachDate","?"),
                        "contas": b.get("PwnCount",0),
                        "dados":  ", ".join(b.get("DataClasses",[])[:4]),
                    })
    except: pass
    return vazamentos[:5]

# ══════════════════════════════════════════════
# EMAILS DOS SÓCIOS
# ══════════════════════════════════════════════
def _emails_socios(socios, dominio):
    if not dominio or not socios: return []
    emails = []
    for s in socios[:5]:
        nome = s.get("nome_socio") or s.get("nome","")
        if not nome: continue
        partes = [re.sub(r'[^a-z]','',p) for p in nome.lower().split()
                  if len(p)>1 and p not in ('de','da','do','dos','das','e','a')]
        if len(partes) < 2: continue
        p, u = partes[0], partes[-1]
        for pad in [f"{p}.{u}@{dominio}", f"{p[0]}{u}@{dominio}",
                    f"{p}@{dominio}", f"{u}.{p}@{dominio}"]:
            emails.append(pad)
    return emails[:12]

# ══════════════════════════════════════════════
# CRUZAR TELEFONE COM CNPJ
# ══════════════════════════════════════════════
def _cruzar_telefone(telefone, empresa):
    """Tenta identificar titular do telefone via dados do CNPJ."""
    if not telefone or not empresa: return None
    tel_limpo = re.sub(r'\D','',telefone)
    tel_empresa = re.sub(r'\D','', empresa.get("telefone",""))
    if tel_limpo and tel_empresa and tel_limpo[-8:] == tel_empresa[-8:]:
        nome = empresa.get("razao_social","")
        socios = empresa.get("qsa",[])
        titular = socios[0].get("nome_socio","") if socios else nome
        return f"⚠️ *Provável titular:* {titular} (cruzado com CNPJ)"
    return None

# ══════════════════════════════════════════════
# ENTRY POINT PRINCIPAL
# ══════════════════════════════════════════════
def osint_completo(cnpj_raw=None, dominio_raw=None, nome_raw=None):
    dados = {
        "cnpj": None, "empresa": {}, "socios": [],
        "dominio": None, "registro_br": {},
        "subdominios": [], "ips": [],
        "emails": [], "phones": [],
        "redes": {}, "instagram": {},
        "pessoa": {}, "vazamentos": [],
    }

    # 1. CNPJ
    if cnpj_raw:
        cnpj = re.sub(r'\D','',cnpj_raw)
        dados["cnpj"] = cnpj
        empresa = _cnpj_dados(cnpj)
        dados["empresa"] = empresa
        dados["socios"]  = empresa.get("qsa",[])
        if empresa.get("email"):
            dados["emails"].append(empresa["email"])
        if empresa.get("telefone"):
            dados["phones"].append(empresa["telefone"])
        dominio = dominio_raw or _extrair_dominio(empresa)
        dados["dominio"] = dominio
    elif dominio_raw:
        dominio = dominio_raw.replace("https://","").replace("http://","").strip("/").lower()
        dados["dominio"] = dominio
    else:
        dominio = None

    nome_empresa = (dados["empresa"].get("nome_fantasia") or
                    dados["empresa"].get("razao_social") or nome_raw or "")

    # 2. Registro.br + WHOIS
    if dominio:
        dados["registro_br"] = _registro_br(dominio)
        # Pegar emails/phones do whois
        for e in dados["registro_br"].get("emails",[]):
            dados["emails"].append(e)
        for p in dados["registro_br"].get("phones",[]):
            dados["phones"].append(p)

    # 3. Subdomínios
    if dominio:
        dados["subdominios"] = _crt_subdomains(dominio)
        # IPs
        for host in [dominio] + dados["subdominios"][:5]:
            try:
                ip = socket.gethostbyname(host)
                dados["ips"].append({"host":host,"ip":ip})
            except: pass

    # 4. Scraping do site
    if dominio:
        site = _scrape_site(dominio)
        dados["emails"]  += site["emails"]
        dados["phones"]  += site["phones"]
        dados["redes"].update(site["redes"])

    # 5. Redes via dork
    if nome_empresa:
        redes_dork = _dork_redes(nome_empresa, dominio or "")
        for k,v in redes_dork.items():
            if k not in dados["redes"]:
                dados["redes"][k] = v

    # 6. Instagram info
    if "instagram" in dados["redes"]:
        handle = dados["redes"]["instagram"].split("instagram.com/")[-1].rstrip("/")
        ig = _instagram_info(handle)
        if ig: dados["instagram"] = ig

    # 7. Emails dos sócios
    if dominio and dados["socios"]:
        dados["emails"] += _emails_socios(dados["socios"], dominio)

    # 8. Busca pessoa (sócios)
    if dados["socios"]:
        socio_principal = (dados["socios"][0].get("nome_socio") or
                           dados["socios"][0].get("nome",""))
        if socio_principal:
            dados["pessoa"] = _dork_pessoa(socio_principal)

    # 9. Vazamentos
    if dominio:
        dados["vazamentos"] = _hibp(dominio)

    # 10. Limpar
    emails_vistos = set()
    emails_limpos = []
    for e in dados["emails"]:
        e = e.lower().strip().strip(".,;")
        dom_e = e.split("@")[-1] if "@" in e else ""
        if (e not in emails_vistos and len(e) > 6 and "." in dom_e
                and dom_e not in LIXO
                and not any(x in e for x in ["noreply","no-reply","pixel","@2x","@3x"])):
            emails_limpos.append(e)
            emails_vistos.add(e)
    dados["emails"] = emails_limpos[:20]
    dados["phones"] = list(dict.fromkeys(p.strip() for p in dados["phones"] if p.strip()))[:8]

    return _formatar(dados)

# ══════════════════════════════════════════════
# FORMATAÇÃO
# ══════════════════════════════════════════════
def _formatar(d):
    agora = datetime.now().strftime('%d/%m/%Y %H:%M')
    e = d.get("empresa",{})
    cnpj = d.get("cnpj","")
    cnpj_fmt = (f"`{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}`"
                if cnpj and len(cnpj)==14 else "—")
    sit = e.get("situacao","")
    sit_icon = {"ATIVA":"✅","BAIXADA":"🔴","SUSPENSA":"⚠️","INAPTA":"❌"}.get(sit,"⚠️")
    out = ["🔴 *REDNOVA — OSINT COMPLETO*", f"_{agora}_"]

    # Empresa
    if e:
        out.append("\n━━━━ 🏢 EMPRESA ━━━━")
        out.append(f"*CNPJ:* {cnpj_fmt}")
        out.append(f"*Razão Social:* {e.get('razao_social','?')}")
        if e.get("nome_fantasia"):
            out.append(f"*Fantasia:* {e['nome_fantasia']}")
        if sit:
            out.append(f"*Situação:* {sit_icon} {sit}")
        out.append(f"*Abertura:* {e.get('abertura','?')}")
        out.append(f"*Atividade:* {str(e.get('atividade',''))[:70]}")
        out.append(f"*Porte:* {e.get('porte','?')} | *Capital:* R$ {e.get('capital_social','?')}")
        end = f"{e.get('logradouro','')} {e.get('numero','')}, {e.get('municipio','')} - {e.get('uf','')}".strip(", ")
        if end.strip():
            out.append(f"*Endereço:* {end}")

    # Sócios
    socios = d.get("socios",[])
    if socios:
        out.append("\n━━━━ 👥 SÓCIOS ━━━━")
        for s in socios[:5]:
            nome = s.get("nome_socio") or s.get("nome","?")
            qual = s.get("qualificacao_socio") or s.get("qual","")
            out.append(f"• {nome} _{qual}_")

    # Domínio
    dom = d.get("dominio")
    if dom:
        out.append(f"\n━━━━ 🌐 DOMÍNIO: `{dom}` ━━━━")
        reg = d.get("registro_br",{})
        if reg.get("owner"):
            out.append(f"*Dono (registro.br):* {reg['owner']}")
        if reg.get("contatos"):
            out.append(f"*Contatos:* {' | '.join(reg['contatos'][:3])}")
        if reg.get("created"):
            out.append(f"*Criado:* {reg['created']}")
        ips_unicos = list({x["ip"]: x for x in d.get("ips",[])}.values())
        if ips_unicos:
            ips_txt = " | ".join("`" + x["ip"] + "`" for x in ips_unicos[:3])
            out.append(f"*IPs:* {ips_txt}")
        subs = d.get("subdominios",[])
        if subs:
            out.append(f"*Subdomínios ({len(subs)}):* " +
                       " | ".join(f"`{s}`" for s in subs[:5]) +
                       (f" _+{len(subs)-5} mais_" if len(subs)>5 else ""))

    # Emails
    emails = d.get("emails",[])
    out.append(f"\n━━━━ 📧 EMAILS ({len(emails)}) ━━━━")
    if emails:
        corp = [x for x in emails if dom and dom in x]
        ext  = [x for x in emails if x not in corp]
        if corp:
            out.append("*Corporativos:*")
            for em in corp[:6]: out.append(f"  `{em}`")
        if ext:
            out.append("*Outros / Prováveis:*")
            for em in ext[:6]: out.append(f"  `{em}`")
    else:
        out.append("  Nenhum encontrado")

    # Telefones
    phones = d.get("phones",[])
    if phones:
        out.append(f"\n━━━━ 📞 TELEFONES ━━━━")
        for p in phones[:5]:
            cruzamento = _cruzar_telefone(p, d.get("empresa",{}))
            out.append(f"  `{p}`")
            if cruzamento:
                out.append(f"  {cruzamento}")

    # Redes
    redes = d.get("redes",{})
    icons = {"facebook":"🔵","instagram":"📸","linkedin":"💼","twitter":"🐦",
             "youtube":"▶️","whatsapp":"💬","tiktok":"🎵","telegram":"✈️"}
    if redes:
        out.append(f"\n━━━━ 📱 REDES SOCIAIS ━━━━")
        for rede, url in redes.items():
            out.append(f"{icons.get(rede,'•')} [{rede.capitalize()}]({url})")
        ig = d.get("instagram",{})
        if ig.get("seguidores"):
            out.append(f"  📊 Seguidores: {ig['seguidores']}"
                       + (f" · {ig.get('posts','')} posts" if ig.get("posts") else ""))
            if ig.get("bio"):
                out.append(f"  Bio: _{ig['bio'][:100]}_")

    # Pessoa / Sócio
    pessoa = d.get("pessoa",{})
    if pessoa:
        out.append(f"\n━━━━ 🔍 SÓCIO PRINCIPAL ━━━━")
        if pessoa.get("linkedin_pessoal"):
            out.append(f"💼 [LinkedIn]({pessoa['linkedin_pessoal']})")
        if pessoa.get("jusbrasil"):
            out.append(f"⚖️ [JusBrasil]({pessoa['jusbrasil']})")
        if pessoa.get("mencoes_emprego"):
            out.append(f"💼 {pessoa['mencoes_emprego']}")

    # Vazamentos
    vaz = d.get("vazamentos",[])
    out.append(f"\n━━━━ ⚠️ VAZAMENTOS ━━━━")
    if vaz:
        for v in vaz:
            contas = f"{v.get('contas',0):,}".replace(",",".")
            out.append(f"🔴 *{v['nome']}* ({v['data']}) — {contas} contas")
            out.append(f"   _{v['dados']}_")
    else:
        out.append("✅ Nenhum vazamento encontrado")

    out.append("\n━━━━━━━━━━━━━━━━━━━━━━")
    out.append("🔴 _RedNova · BrasilAPI · registro.br · crt.sh · HIBP · DuckDuckGo_")
    return "\n".join(out)
