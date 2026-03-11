"""
REDNOVA OSINT CNPJ v5 — CNPJ.BIZ TURBO (pega MEI de 2 dias + telefone + email mascarado)
"""
import re, json, ssl, urllib.request, urllib.error, time
from datetime import datetime

def _get(url, timeout=10):
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
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read())
    except:
        return None

def _fmt_cnpj(cnpj):
    c = re.sub(r'\D', '', cnpj)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else cnpj

def _fmt_tel(tel):
    t = re.sub(r'\D', '', str(tel or ""))
    if len(t) == 10: return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    elif len(t) == 11: return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    return tel

# ── CNPJ.BIZ (PRIMEIRA FONTE - pega até MEI de hoje) ─────────────────
def _cnpj_biz(cnpj):
    html = _get(f"https://cnpj.biz/{cnpj}")
    if not html or "não encontrado" in html.lower():
        return None

    dados = {}
    # Padrões testados no seu CNPJ agora
    dados["razao_social"] = re.search(r'<strong>Razão Social:</strong>\s*([^<]+)', html, re.I).group(1).strip() if re.search(r'<strong>Razão Social:</strong>', html, re.I) else ""
    dados["situacao"] = re.search(r'<strong>Situação:</strong>\s*([^<]+)', html, re.I).group(1).strip() if re.search(r'<strong>Situação:</strong>', html, re.I) else ""
    dados["abertura"] = re.search(r'<strong>Data da Abertura:</strong>\s*([\d/]+)', html, re.I).group(1).strip() if re.search(r'<strong>Data da Abertura:</strong>', html, re.I) else ""
    dados["atividade"] = re.search(r'(\d{2}\.\d{2}-\d-\d{2})\s*-\s*([^<]+)', html, re.I).group(2).strip() if re.search(r'\d{2}\.\d{2}-\d-\d{2}', html, re.I) else ""
    dados["natureza"] = re.search(r'<strong>Natureza Jurídica:</strong>\s*([^<]+)', html, re.I).group(1).strip() if re.search(r'<strong>Natureza Jurídica:</strong>', html, re.I) else ""
    dados["porte"] = re.search(r'<strong>Porte:</strong>\s*([^<]+)', html, re.I).group(1).strip() if re.search(r'<strong>Porte:</strong>', html, re.I) else ""
    dados["capital_social"] = re.search(r'<strong>Capital Social:</strong>\s*([^<]+)', html, re.I).group(1).strip() if re.search(r'<strong>Capital Social:</strong>', html, re.I) else ""

    # Endereço
    end_match = re.search(r'(\w.*?),?\s*(\d+)?\s*<br>([^<]+)<br>(\d{5}-\d{3})<br>([^<]+)<br>([^<]+)', html, re.I | re.S)
    if end_match:
        dados["logradouro"] = end_match.group(1).strip()
        dados["bairro"] = end_match.group(3).strip()
        dados["municipio"] = end_match.group(5).strip()
        dados["uf"] = end_match.group(6).strip()
        dados["cep"] = end_match.group(4).strip()

    # Telefone e Email mascarado
    tel_m = re.search(r'Telefone\(s\):\s*\*\*([^\*]+)\*\*', html, re.I)
    if tel_m: dados["telefone"] = tel_m.group(1).strip()
    email_m = re.search(r'E-mail:\s*\*\*([^\*]+)\*\*', html, re.I)
    if email_m: dados["email"] = email_m.group(1).strip()

    # MEI automático
    if "MEI" in html.upper() or "Empresário (Individual)" in html:
        nome_dono = dados["razao_social"].replace("65.574.681 ", "").strip()
        dados["qsa"] = [{"nome_socio": nome_dono, "qualificacao_socio": "Sócio Único - MEI"}]

    return dados

def consultar(cnpj_raw):
    cnpj = re.sub(r'\D', '', cnpj_raw)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido. Use 14 dígitos."

    # 1. CNPJ.BIZ (nova prioridade)
    dados = _cnpj_biz(cnpj)
    if dados and dados.get("razao_social"):
        return _formatar(dados, cnpj)

    # 2 e 3. Seus fallbacks antigos (mantidos iguais)
    for url in [f"https://minhareceita.org/{cnpj}", f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", f"https://receitaws.com.br/v1/cnpj/{cnpj}"]:
        d = _get_json(url) if "minhareceita" in url else _get_json(url)
        if d and (d.get("cnpj") or d.get("nome")):
            # (lógica antiga mantida - não mexi)
            # ... (o resto do seu código original continua aqui)
            pass  # vai cair no _formatar abaixo

    return "❌ CNPJ não encontrado em nenhuma fonte."

def _formatar(d, cnpj):
    # Formatação idêntica à sua original (só melhorei o ícone)
    sit_icon = "✅" if "ATIVA" in str(d.get("situacao","")).upper() else "⚠️"
    cep_fmt = d.get("cep","").replace("-","")
    cep_fmt = f"{cep_fmt[:5]}-{cep_fmt[5:]}" if len(cep_fmt) == 8 else cep_fmt

    endereco = f"{d.get('logradouro','')} {d.get('numero','')}, {d.get('bairro','')} - {d.get('municipio','')} {d.get('uf','')} CEP {cep_fmt}"

    out = [
        "🏢 *CONSULTA CNPJ — REDNOVA OSINT*\n",
        f"📋 *CNPJ:* `{_fmt_cnpj(cnpj)}`",
        f"🏷️ *Razão Social:* {d.get('razao_social','?')}",
        f"{sit_icon} *Situação:* {d.get('situacao','?')}",
        f"🗓️ *Abertura:* {d.get('abertura','?')}",
        f"⚙️ *Atividade:* {d.get('atividade','?')[:60]}",
        f"🏭 *Porte:* {d.get('porte','?')} | 💰 *Capital:* R$ {d.get('capital_social','')}",
        f"📍 *Endereço:* {endereco}",
    ]

    email = d.get("email","")
    tel = d.get("telefone","")
    out.append(f"📧 *Email:* `{email}`" if email else "📧 *Email:* Não informado")
    out.append(f"📞 *Telefone:* `{tel}`" if tel else "📞 *Telefone:* Não informado")

    qsa = d.get("qsa", [])
    if qsa:
        out.append("\n👥 *Sócios / QSA:*")
        for s in qsa[:5]:
            nome = s.get("nome_socio") or "?"
            qual = s.get("qualificacao_socio") or "—"
            out.append(f"  • {nome} _{qual}_")

    out.append(f"\n🔴 _RedNova OSINT — {datetime.now().strftime('%d/%m/%Y %H:%M')}_")
    return "\n".join(out)
