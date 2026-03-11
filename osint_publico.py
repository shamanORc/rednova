"""
REDNOVA OSINT PUBLICO v3 — AGORA COM CNPJ.BIZ + FUNDADOR COMPLETO
"""
import re, json, socket, ssl, time, urllib.request, urllib.error, urllib.parse, subprocess
from datetime import datetime
from osint_registrobr import consultar_dominio, cruzar_dono

EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}')
PHONE_RE = re.compile(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})[\s\-]?\d{4}')
LIXO = {"gmail.com","hotmail.com","yahoo.com","outlook.com","icloud.com","uol.com.br","bol.com.br","terra.com.br","ig.com.br","example.com"}

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

# ── NOVA FONTE: CNPJ.BIZ (mais rápido do Brasil) ─────────────────────
def _cnpj_biz(cnpj):
    html = _get(f"https://cnpj.biz/{cnpj}")
    if not html or "não encontrado" in html.lower():
        return {}
    dados = {}
    patterns = {
        "razao_social": r'<strong>Razão Social:</strong>\s*([^<]+)',
        "situacao": r'<strong>Situação:</strong>\s*([^<]+)',
        "abertura": r'<strong>Data da Abertura:</strong>\s*([\d/]+)',
        "atividade": r'Principal:\s*([^<]+)',
        "natureza": r'<strong>Natureza Jurídica:</strong>\s*([^<]+)',
        "porte": r'<strong>Porte:</strong>\s*([^<]+)',
        "capital_social": r'<strong>Capital Social:</strong>\s*([^<]+)',
    }
    for k, pat in patterns.items():
        m = re.search(pat, html, re.I)
        if m:
            dados[k] = m.group(1).strip()

    # Endereço
    end = re.search(r'Logradouro:\s*([^<]+).*?Bairro:\s*([^<]+).*?Município:\s*([^<]+).*?Estado:\s*([^<]+).*?CEP:\s*([^<]+)', html, re.I | re.S)
    if end:
        dados["logradouro"] = end.group(1).strip()
        dados["bairro"] = end.group(2).strip()
        dados["municipio"] = end.group(3).strip()
        dados["uf"] = end.group(4).strip()
        dados["cep"] = end.group(5).strip()

    # QSA (sócios)
    qsa_raw = re.findall(r'([A-Za-zÀ-ÿ\s\.\-]+?)\s*-\s*([A-Za-zÀ-ÿ\s]+?)(?=<br>|$)', html, re.I)
    if qsa_raw:
        dados["qsa"] = [{"nome": n.strip(), "qualificacao_socio": q.strip()} for n, q in qsa_raw]

    return dados

# ── CONSULTA CNPJ (agora com cnpj.biz + minhareceita) ─────────────────
def _cnpj_dados(cnpj):
    # 1. cnpj.biz (mais rápido para empresas novas)
    dados = _cnpj_biz(cnpj)
    if dados.get("razao_social"):
        return dados

    # 2. minhareceita.org (telefone + email completo)
    d = _get_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        return {
            "razao_social": d.get("razao_social",""),
            "nome_fantasia": d.get("nome_fantasia",""),
            "situacao": d.get("descricao_situacao_cadastral",""),
            "abertura": str(d.get("data_inicio_atividade",""))[:10],
            "atividade": d.get("cnae_fiscal_descricao",""),
            "natureza": d.get("natureza_juridica_descricao",""),
            "logradouro": d.get("logradouro",""),
            "numero": d.get("numero",""),
            "bairro": d.get("bairro",""),
            "municipio": d.get("municipio",""),
            "uf": d.get("uf",""),
            "cep": d.get("cep",""),
            "telefone": d.get("ddd_telefone_1",""),
            "email": d.get("email",""),
            "qsa": d.get("qsa",[]),
            "capital_social": d.get("capital_social",""),
            "porte": d.get("porte",""),
        }

    # 3. Fallbacks antigos
    for url in [f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}", f"https://receitaws.com.br/v1/cnpj/{cnpj}"]:
        data = _get_json(url)
        if data:
            return { ... }  # mantém seu código antigo aqui (não mudei pra não quebrar)

    return {}

# (o resto do arquivo continua igual até o final, só alterei as partes abaixo)

def osint_completo(cnpj_raw=None, dominio_raw=None, nome_raw=None):
    # ... (seu código antigo até a linha onde pega empresa)

    if cnpj_raw:
        cnpj = re.sub(r'\D','',cnpj_raw)
        dados["cnpj"] = cnpj
        empresa = _cnpj_dados(cnpj)          # ← AGORA USA CNPJ.BIZ + MINHARECEITA
        dados["empresa"] = empresa
        dados["socios"]  = empresa.get("qsa", [])

        # ── CRUZA REDES DO FUNDADOR MESMO SEM DOMÍNIO ─────────────────
        if dados["socios"]:
            socio_principal = dados["socios"][0].get("nome_socio") or dados["socios"][0].get("nome","")
            if socio_principal and len(socio_principal) > 5:
                dados["dono_nome"] = socio_principal
                dados["dono_redes"] = cruzar_dono(socio_principal)

    # ... resto do seu código continua igual (domínio, scraping, HIBP, etc.)

    # No final do _formatar, já vai aparecer tudo do fundador automaticamente.
