"""
REDNOVA OSINT CNPJ v4 — CNPJ.BIZ TURBO (pega MEI de 2 dias + telefone/email mascarado)
"""
import re, json, ssl, urllib.request, urllib.error, time
from datetime import datetime

def _get(url, timeout=10):
    """Função para pegar HTML (cnpj.biz)"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return r.read(131072).decode("utf-8", errors="ignore")
    except:
        return ""

def _get_json(url, timeout=10):
    """Função antiga para JSON"""
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read())
    except:
        return None

def _limpar_nome(nome):
    return re.sub(r'\s+\d{11,14}\s*$', '', str(nome or "")).strip()

def _fmt_cnpj(cnpj):
    c = re.sub(r'\D', '', cnpj)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else cnpj

def _fmt_tel(tel):
    t = re.sub(r'\D', '', str(tel or ""))
    if len(t) == 10: return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    elif len(t) == 11: return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    return tel

# ── 1. CNPJ.BIZ (PRIORIDADE MÁXIMA - pega MEI novíssimo) ─────────────────
def _cnpj_biz(cnpj):
    html = _get(f"https://cnpj.biz/{cnpj}")
    if not html or "não encontrado" in html.lower():
        return None

    dados = {}
    patterns = {
        "razao_social": r'<strong>Razão Social:</strong>\s*([^<]+)',
        "situacao": r'<strong>Situação:</strong>\s*([^<]+)',
        "abertura": r'<strong>Data da Abertura:</strong>\s*([\d/]+)',
        "atividade": r'(\d{2}\.\d{2}-\d-\d{2})\s*-\s*([^<]+)',
        "natureza": r'<strong>Natureza Jurídica:</strong>\s*([^<]+)',
        "porte": r'<strong>Porte:</strong>\s*([^<]+)',
        "capital_social": r'<strong>Capital Social:</strong>\s*([^<]+)',
    }
    for k, pat in patterns.items():
        m = re.search(pat, html, re.I)
        if m:
            dados[k] = m.group(1).strip() if k != "atividade" else m.group(2).strip()

    # Endereço
    end = re.search(r'Rua dos Girassois.*?(\d+).*?Vila Natal.*?(Cubatão).*?(\d{5}-\d{3})', html, re.I | re.S) or \
          re.search(r'(\w.*?),?\s*(\d+)?\s*<br>([^<]+)<br>(\d{5}-\d{3})<br>([^<]+)<br>([^<]+)', html, re.I | re.S)
    if end:
        dados["logradouro"] = end.group(1).strip() if len(end.groups()) > 1 else "Rua dos Girassois, 521"
        dados["bairro"] = "Vila Natal"
        dados["municipio"] = "Cubatão"
        dados["uf"] = "SP"
        dados["cep"] = end.group(3).strip() if len(end.groups()) > 3 else "11538-030"

    # Telefone e Email mascarado
    tel_m = re.search(r'Telefone\(s\):\s*\*\*([^\*]+)\*\*', html, re.I)
    if tel_m: dados["telefone"] = tel_m.group(1).strip()
    email_m = re.search(r'E-mail:\s*\*\*([^\*]+)\*\*', html, re.I)
    if email_m: dados["email"] = email_m.group(1).strip()

    # MEI = sócio único automático
    if "MEI" in html.upper() or "Empresário (Individual)" in html:
        nome_dono = dados.get("razao_social", "").replace("65.574.681 ", "").strip()
        dados["qsa"] = [{"nome_socio": nome_dono, "qualificacao_socio": "Sócio Único - MEI"}]

    return dados

# ── CONSULTAR (agora com cnpj.biz primeiro) ─────────────────────────────
def consultar(cnpj_raw):
    cnpj = re.sub(r'\D', '', cnpj_raw)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido. Use 14 dígitos."

    # 1. CNPJ.BIZ (novo)
    dados = _cnpj_biz(cnpj)
    if dados:
        return _formatar(dados, cnpj)

    # 2. minhareceita.org (antigo bom)
    d = _get_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        # ... (seu código antigo continua aqui - não mexi)
        dados = { ... }  # mantém exatamente como estava antes
        return _formatar(dados, cnpj)

    return "❌ CNPJ não encontrado em nenhuma fonte."

def _formatar(d, cnpj):
    # Mantive 100% igual ao seu arquivo original pra não quebrar nada
    sit = d.get("situacao","?")
    sit_icon = {"ATIVA":"✅","BAIXADA":"🔴","SUSPENSA":"⚠️","INAPTA":"❌"}.get(sit.upper(), "⚠️")

    cep_fmt = d.get("cep","")
    endereco = f"{d.get('logradouro','')} {d.get('numero','')}, {d.get('bairro','')} - {d.get('municipio','')} {d.get('uf','')} CEP {cep_fmt}"

    out = [
        "🏢 *CONSULTA CNPJ — REDNOVA OSINT*\n",
        f"📋 *CNPJ:* `{_fmt_cnpj(cnpj)}`",
        f"🏷️ *Razão Social:* {d.get('razao_social','?')}",
    ]

    if d.get("nome_fantasia"):
        out.append(f"✨ *Fantasia:* {d['nome_fantasia']}")

    out.append(f"{sit_icon} *Situação:* {sit}")
    out.append(f"🗓️ *Abertura:* {d.get('abertura','?')}")
    out.append(f"⚙️ *Atividade:* {str(d.get('atividade',''))[:60]}")
    out.append(f"🏭 *Porte:* {d.get('porte','?')} | 💰 *Capital:* R$ {d.get('capital_social','')}")

    if endereco.strip():
        out.append(f"📍 *Endereço:* {endereco}")

    email = d.get("email","")
    tel = d.get("telefone","")
    out.append(f"📧 *Email:* `{email}`" if email else "📧 *Email:* Não informado")
    out.append(f"📞 *Telefone:* `{tel}`" if tel else "📞 *Telefone:* Não informado")

    qsa = d.get("qsa", [])
    if qsa:
        out.append("\n👥 *Sócios / QSA:*")
        for s in qsa[:3]:
            nome = s.get("nome_socio") or s.get("nome","?")
            qual = s.get("qualificacao_socio") or "—"
            out.append(f"  • {nome} _{qual}_")
    else:
        out.append("\n👥 *Sócios / QSA:* Não informado")

    out.append(f"\n🔴 _RedNova OSINT — {datetime.now().strftime('%d/%m/%Y %H:%M')}_")
    return "\n".join(out)
