"""
OSINT registro.br — API RDAP oficial + cruzamento do dono
"""
import re, json, socket, ssl, urllib.request, urllib.error, urllib.parse, time

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

def _get_html(url, timeout=10):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0",
            "Accept": "text/html,*/*",
            "Accept-Language": "pt-BR,pt;q=0.9",
        })
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read(131072).decode("utf-8", errors="ignore")
    except:
        return ""

# ══════════════════════════════════════════
# RDAP registro.br — API oficial
# ══════════════════════════════════════════
def consultar_dominio(dominio):
    """Consulta RDAP do registro.br e extrai todos os dados."""
    resultado = {
        "dominio": dominio,
        "dono": None,
        "dono_nome": None,
        "nic_hdl": None,
        "criado": None,
        "expira": None,
        "alterado": None,
        "status": None,
        "nameservers": [],
        "emails": [],
        "telefones": [],
        "entidades": [],
    }

    # API RDAP oficial
    data = _get_json(f"https://rdap.registro.br/domain/{dominio}")
    if not data:
        return resultado

    # Status
    resultado["status"] = ", ".join(data.get("status", []))

    # Datas
    for evento in data.get("events", []):
        acao = evento.get("eventAction", "")
        data_evt = evento.get("eventDate", "")[:10]
        if "registration" in acao:
            resultado["criado"] = data_evt
        elif "expiration" in acao:
            resultado["expira"] = data_evt
        elif "last changed" in acao:
            resultado["alterado"] = data_evt

    # Nameservers
    for ns in data.get("nameservers", []):
        resultado["nameservers"].append(ns.get("ldhName", ""))

    # Entidades (dono, admin, tech)
    for entity in data.get("entities", []):
        roles = entity.get("roles", [])
        nic = entity.get("handle", "")
        nome = None
        emails_ent = []
        fones_ent = []

        # vCard
        vcard = entity.get("vcardArray", ["", []])
        if len(vcard) > 1:
            for item in vcard[1]:
                if not isinstance(item, list) or len(item) < 4:
                    continue
                tipo = item[0]
                valor = item[3] if len(item) > 3 else ""
                if tipo == "fn":
                    nome = str(valor)
                elif tipo == "email":
                    emails_ent.append(str(valor))
                elif tipo == "tel":
                    fones_ent.append(str(valor).replace("tel:",""))

        entidade = {
            "roles": roles,
            "nic": nic,
            "nome": nome,
            "emails": emails_ent,
            "telefones": fones_ent,
        }
        resultado["entidades"].append(entidade)

        # Registrant = dono
        if "registrant" in roles:
            resultado["dono_nome"] = nome
            resultado["nic_hdl"] = nic
            resultado["emails"].extend(emails_ent)
            resultado["telefones"].extend(fones_ent)

        # Subentidades (pessoa física por trás do NIC)
        for sub in entity.get("entities", []):
            sub_vcard = sub.get("vcardArray", ["", []])
            sub_nome = None
            sub_emails = []
            sub_fones = []
            if len(sub_vcard) > 1:
                for item in sub_vcard[1]:
                    if not isinstance(item, list) or len(item) < 4:
                        continue
                    tipo = item[0]
                    valor = item[3] if len(item) > 3 else ""
                    if tipo == "fn":
                        sub_nome = str(valor)
                    elif tipo == "email":
                        sub_emails.append(str(valor))
                    elif tipo == "tel":
                        sub_fones.append(str(valor).replace("tel:",""))

            if sub_nome and not resultado["dono_nome"]:
                resultado["dono_nome"] = sub_nome
            resultado["emails"].extend(sub_emails)
            resultado["telefones"].extend(sub_fones)

    # Limpar duplicatas
    resultado["emails"]    = list(dict.fromkeys(e.lower().strip() for e in resultado["emails"] if e))
    resultado["telefones"] = list(dict.fromkeys(t.strip() for t in resultado["telefones"] if t))

    return resultado


# ══════════════════════════════════════════
# CRUZAR DONO — redes sociais, JusBrasil etc
# ══════════════════════════════════════════
def cruzar_dono(nome):
    """Dado o nome do dono, busca em fontes públicas."""
    if not nome or len(nome) < 5:
        return {}

    resultado = {}
    nome_enc = urllib.parse.quote(f'"{nome}"')

    # DuckDuckGo dork para cada rede
    # Usar primeiro + último nome para busca mais precisa
    partes_nome = nome.split()
    nome_curto = partes_nome[0] + " " + partes_nome[-1] if len(partes_nome) > 1 else nome
    nome_curto_enc = urllib.parse.quote(f'"{nome_curto}"')

    buscas = {
        "linkedin":  f"{nome_curto_enc} site:linkedin.com/in",
        "instagram": f"{nome_curto_enc} site:instagram.com",
        "facebook":  f"{nome_curto_enc} site:facebook.com",
        "jusbrasil": f"{nome_enc} site:jusbrasil.com.br",
        "escavador":  f"{nome_enc} site:escavador.com",
    }

    pats = {
        "linkedin":  r'linkedin\.com/in/([A-Za-z0-9\-_\.]{2,60})',
        "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)',
        "facebook":  r'facebook\.com/(?!sharer|share|groups|events|pages/create|tr|plugins|dialog|login|legal|privacy|photo|video|watch)([A-Za-z0-9\._\-]{4,50})',
        "jusbrasil": r'jusbrasil\.com\.br/(?:artigos|noticias|jurisprudencia|diarios|processos)/[^\s"<>]{5,100}',
        "escavador":  r'escavador\.com/sobre/[^\s"<>]{5,80}',
    }

    bases = {
        "linkedin":  "https://linkedin.com/in/",
        "instagram": "https://instagram.com/",
        "facebook":  "https://facebook.com/",
    }

    ignorar = {"login","sharer","share","watch","home","feed","groups","events",
               "pages","create","photo","photos","videos","marketplace"}

    for rede, query in buscas.items():
        try:
            q = urllib.parse.quote(query)
            html = _get_html(f"https://html.duckduckgo.com/html/?q={q}")
            if not html:
                html = _get_html(f"https://www.bing.com/search?q={q}")

            m = re.search(pats[rede], html, re.IGNORECASE)
            if m:
                if rede in ("jusbrasil", "escavador"):
                    resultado[rede] = f"https://{m.group(0)}"
                else:
                    handle = m.group(1).rstrip("/").split("?")[0].split("#")[0]
                    if handle.lower() not in ignorar and len(handle) > 1:
                        resultado[rede] = bases[rede] + handle
            time.sleep(1.2)
        except:
            pass

    # Busca geral — empregos, menções
    try:
        html_geral = _get_html(
            f"https://html.duckduckgo.com/html/?q={nome_enc}+emprego+OR+empresa+OR+sócio"
        )
        # Emails na busca
        EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}')
        emails = EMAIL_RE.findall(html_geral)
        lixo = {"gmail.com","hotmail.com","yahoo.com","duckduckgo.com","bing.com"}
        emails_limpos = [e.lower() for e in emails if e.split("@")[-1] not in lixo]
        if emails_limpos:
            resultado["emails_encontrados"] = list(dict.fromkeys(emails_limpos))[:5]
    except:
        pass

    return resultado


# ══════════════════════════════════════════
# FORMATAR SEÇÃO REGISTRO.BR
# ══════════════════════════════════════════
def formatar_secao(reg, cruzamento):
    out = []

    if reg.get("dono_nome"):
        out.append(f"*Registrante:* {reg['dono_nome']}")
    if reg.get("nic_hdl"):
        out.append(f"*NIC-BR:* `{reg['nic_hdl']}`")
    if reg.get("criado"):
        out.append(f"*Criado:* {reg['criado']} | *Expira:* {reg.get('expira','?')}")
    if reg.get("nameservers"):
        out.append(f"*NS:* {' | '.join(reg['nameservers'][:2])}")
    if reg.get("emails"):
        for e in reg["emails"][:3]:
            out.append(f"*Email:* `{e}`")
    if reg.get("telefones"):
        for t in reg["telefones"][:3]:
            out.append(f"*Tel:* `{t}`")

    # Cruzamento do dono
    if cruzamento:
        out.append("\n*🔍 Dono nas redes:*")
        icons = {
            "linkedin":"💼","instagram":"📸","facebook":"🔵",
            "jusbrasil":"⚖️","escavador":"🔎"
        }
        for rede, url in cruzamento.items():
            if rede == "emails_encontrados":
                for e in url[:3]:
                    out.append(f"  📧 `{e}`")
            else:
                out.append(f"  {icons.get(rede,'•')} [{rede.capitalize()}]({url})")

    return "\n".join(out) if out else "Dados não disponíveis via RDAP"
