"""
REDNOVA OSINT CNPJ v3
Fontes: minhareceita.org (email+tel completo) → BrasilAPI → ReceitaWS
"""
import re, json, ssl, urllib.request, urllib.error, time
from datetime import datetime

SITUACOES = {
    "1": "NULA", "2": "ATIVA", "3": "SUSPENSA",
    "4": "INAPTA", "8": "BAIXADA"
}

MOTIVOS = {
    "01": "Extinção Por Encerramento Liquidação Voluntária",
    "02": "Incorporação",
    "03": "Fusão",
}

def _get_json(url, headers=None, timeout=10):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        h = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
        if headers:
            h.update(headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as r:
            return json.loads(r.read())
    except:
        return None

def _limpar_nome(nome):
    """Remove CPF colado na razão social."""
    return re.sub(r'\s+\d{11,14}\s*$', '', str(nome or "")).strip()

def _fmt_cnpj(cnpj):
    c = re.sub(r'\D', '', cnpj)
    return f"{c[:2]}.{c[2:5]}.{c[5:8]}/{c[8:12]}-{c[12:]}" if len(c) == 14 else cnpj

def _fmt_tel(tel):
    t = re.sub(r'\D', '', str(tel or ""))
    if len(t) == 10:
        return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    elif len(t) == 11:
        return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    return tel

def consultar(cnpj_raw):
    cnpj = re.sub(r'\D', '', cnpj_raw)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido. Use 14 dígitos."

    dados = None

    # 1. minhareceita.org — retorna email e telefone da Receita Federal
    d = _get_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        sit_raw = str(d.get("descricao_situacao_cadastral") or "")
        sit_num = str(d.get("codigo_situacao_cadastral") or "")
        sit = sit_raw or SITUACOES.get(sit_num, sit_num)

        # telefone: campo ddd_telefone_1
        tel_raw = str(d.get("ddd_telefone_1") or "")
        tel = _fmt_tel(tel_raw) if tel_raw and tel_raw != "None" else ""

        dados = {
            "razao_social":  _limpar_nome(d.get("razao_social","")),
            "nome_fantasia": d.get("nome_fantasia",""),
            "situacao":      sit,
            "data_situacao": d.get("data_situacao_cadastral","")[:10] if d.get("data_situacao_cadastral") else "",
            "motivo_situacao": d.get("motivo_situacao_cadastral",""),
            "abertura":      str(d.get("data_inicio_atividade",""))[:10],
            "atividade":     d.get("cnae_fiscal_descricao",""),
            "natureza":      d.get("natureza_juridica_descricao",""),
            "logradouro":    d.get("logradouro",""),
            "numero":        d.get("numero",""),
            "complemento":   d.get("complemento",""),
            "bairro":        d.get("bairro",""),
            "municipio":     d.get("municipio",""),
            "uf":            d.get("uf",""),
            "cep":           str(d.get("cep","")).zfill(8),
            "email":         str(d.get("email") or "").lower().strip(),
            "telefone":      tel,
            "porte":         d.get("porte",""),
            "capital_social":d.get("capital_social",""),
            "qsa":           d.get("qsa",[]) or [],
        }

    # 2. BrasilAPI como fallback
    if not dados:
        time.sleep(0.5)
        d2 = _get_json(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
        if d2:
            sit_raw = str(d2.get("situacao_cadastral",""))
            sit = SITUACOES.get(sit_raw, sit_raw) if sit_raw.isdigit() else sit_raw
            dados = {
                "razao_social":  _limpar_nome(d2.get("razao_social","")),
                "nome_fantasia": d2.get("nome_fantasia",""),
                "situacao":      sit,
                "data_situacao": "",
                "motivo_situacao": "",
                "abertura":      d2.get("data_inicio_atividade",""),
                "atividade":     d2.get("cnae_fiscal_descricao",""),
                "natureza":      "",
                "logradouro":    d2.get("logradouro",""),
                "numero":        d2.get("numero",""),
                "complemento":   d2.get("complemento",""),
                "bairro":        d2.get("bairro",""),
                "municipio":     d2.get("municipio",""),
                "uf":            d2.get("uf",""),
                "cep":           d2.get("cep",""),
                "email":         str(d2.get("email") or "").lower().strip(),
                "telefone":      d2.get("ddd_telefone_1",""),
                "porte":         d2.get("porte",""),
                "capital_social":str(d2.get("capital_social","")),
                "qsa":           d2.get("qsa",[]) or [],
            }

    # 3. ReceitaWS como último fallback
    if not dados:
        time.sleep(1)
        d3 = _get_json(f"https://receitaws.com.br/v1/cnpj/{cnpj}")
        if d3 and d3.get("status") != "ERROR":
            sit = str(d3.get("situacao","?"))
            dados = {
                "razao_social":  _limpar_nome(d3.get("nome","")),
                "nome_fantasia": d3.get("fantasia",""),
                "situacao":      sit,
                "data_situacao": "",
                "motivo_situacao": "",
                "abertura":      d3.get("abertura",""),
                "atividade":     (d3.get("atividade_principal",[{}])[0].get("text","") if d3.get("atividade_principal") else ""),
                "natureza":      d3.get("natureza_juridica",""),
                "logradouro":    d3.get("logradouro",""),
                "numero":        d3.get("numero",""),
                "complemento":   d3.get("complemento",""),
                "bairro":        d3.get("bairro",""),
                "municipio":     d3.get("municipio",""),
                "uf":            d3.get("uf",""),
                "cep":           d3.get("cep",""),
                "email":         str(d3.get("email") or "").lower().strip(),
                "telefone":      d3.get("telefone",""),
                "porte":         d3.get("porte",""),
                "capital_social":d3.get("capital_social",""),
                "qsa":           d3.get("qsa",[]) or [],
            }

    if not dados:
        return "❌ CNPJ não encontrado em nenhuma fonte."

    return _formatar(dados, cnpj)


def _formatar(d, cnpj):
    sit = d.get("situacao","?")
    sit_icon = {"ATIVA":"✅","BAIXADA":"🔴","SUSPENSA":"⚠️","INAPTA":"❌"}.get(
        sit.upper() if sit else "", "⚠️")

    cep = d.get("cep","").replace("-","").replace(".","")
    cep_fmt = f"{cep[:5]}-{cep[5:]}" if len(cep) == 8 else cep

    end_parts = [
        d.get("logradouro",""),
        d.get("numero",""),
        d.get("complemento",""),
        d.get("bairro",""),
        d.get("municipio",""),
        d.get("uf",""),
        cep_fmt,
    ]
    endereco = ", ".join(p for p in end_parts if p and p not in ("*","**","***","****","*****","********"))

    cap = d.get("capital_social","")
    try:
        cap_fmt = f"R$ {float(str(cap).replace(',','.')) :,.2f}".replace(",","X").replace(".",",").replace("X",".")
    except:
        cap_fmt = f"R$ {cap}"

    out = [
        "🏢 *CONSULTA CNPJ — REDNOVA OSINT*\n",
        f"📋 *CNPJ:* `{_fmt_cnpj(cnpj)}`",
        f"🏷️ *Razão Social:* {d.get('razao_social','?')}",
    ]

    if d.get("nome_fantasia") and d["nome_fantasia"] not in ("","None","*","**"):
        out.append(f"✨ *Fantasia:* {d['nome_fantasia']}")

    out.append(f"{sit_icon} *Situação:* {sit}")

    if d.get("data_situacao"):
        out.append(f"📅 *Data Situação:* {d['data_situacao']}")
    if d.get("motivo_situacao") and d["motivo_situacao"] not in ("","None","*"):
        out.append(f"📝 *Motivo:* {d['motivo_situacao']}")

    out.append(f"🗓️ *Abertura:* {d.get('abertura','?')}")

    if d.get("atividade") and d["atividade"] not in ("","*","**","****","********"):
        out.append(f"⚙️ *Atividade:* {str(d['atividade'])[:60]}")
    if d.get("natureza") and d["natureza"] not in ("","*","None"):
        out.append(f"⚖️ *Natureza:* {d['natureza']}")

    out.append(f"🏭 *Porte:* {d.get('porte','?')} | 💰 *Capital:* {cap_fmt}")

    if endereco:
        out.append(f"📍 *Endereço:* {endereco}")

    # Email e telefone — FONTE PRINCIPAL DE VALOR
    email = d.get("email","")
    tel   = d.get("telefone","")

    if email and email not in ("","none","nan","*","**"):
        out.append(f"📧 *Email:* `{email}`")
    else:
        out.append("📧 *Email:* Não informado")

    if tel and tel not in ("","none","nan","*","**"):
        out.append(f"📞 *Telefone:* `{tel}`")
    else:
        out.append("📞 *Telefone:* Não informado")

    # Sócios
    qsa = [s for s in (d.get("qsa") or []) if isinstance(s, dict)]
    if qsa:
        out.append("\n👥 *Sócios / QSA:*")
        for s in qsa[:5]:
            nome_s = _limpar_nome(s.get("nome_socio") or s.get("nome") or "?")
            qual_s = s.get("qualificacao_socio") or s.get("qual","")
            out.append(f"  • {nome_s} _{qual_s}_")
    else:
        out.append("\n👥 *Sócios / QSA:* Não informado")

    out.append(f"\n🔴 _RedNova OSINT — {datetime.now().strftime('%d/%m/%Y %H:%M')}_")
    return "\n".join(out)
