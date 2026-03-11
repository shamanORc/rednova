"""CNPJ — minhareceita.org + BrasilAPI + ReceitaWS"""
import re, time
from web_crawler import get_json

SITUACOES = {"1":"NULA","2":"ATIVA","3":"SUSPENSA","4":"INAPTA","8":"BAIXADA"}

def _limpar(nome):
    return re.sub(r'\s+\d{11,14}\s*$', '', str(nome or "")).strip()

def _tel(t):
    t = re.sub(r'\D','',str(t or ""))
    if len(t)==10: return f"({t[:2]}) {t[2:6]}-{t[6:]}"
    if len(t)==11: return f"({t[:2]}) {t[2:7]}-{t[7:]}"
    return t

def lookup(cnpj_raw):
    cnpj = re.sub(r'\D','',cnpj_raw)
    if len(cnpj)!=14: return None

    # 1. minhareceita.org (email + telefone reais)
    d = get_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        sit_raw = str(d.get("descricao_situacao_cadastral",""))
        sit_num = str(d.get("codigo_situacao_cadastral",""))
        sit = sit_raw or SITUACOES.get(sit_num, sit_num)
        return {
            "cnpj": cnpj,
            "razao_social":   _limpar(d.get("razao_social","")),
            "nome_fantasia":  d.get("nome_fantasia",""),
            "situacao":       sit,
            "data_situacao":  str(d.get("data_situacao_cadastral",""))[:10],
            "motivo_situacao":d.get("motivo_situacao_cadastral",""),
            "abertura":       str(d.get("data_inicio_atividade",""))[:10],
            "atividade":      d.get("cnae_fiscal_descricao",""),
            "natureza":       d.get("natureza_juridica_descricao",""),
            "logradouro":     d.get("logradouro",""),
            "numero":         d.get("numero",""),
            "bairro":         d.get("bairro",""),
            "municipio":      d.get("municipio",""),
            "uf":             d.get("uf",""),
            "cep":            str(d.get("cep","")).zfill(8),
            "email":          str(d.get("email") or "").lower().strip(),
            "telefone":       _tel(d.get("ddd_telefone_1","")),
            "porte":          d.get("porte",""),
            "capital_social": d.get("capital_social",""),
            "qsa":            d.get("qsa",[]) or [],
        }

    # 2. BrasilAPI fallback
    time.sleep(0.5)
    d2 = get_json(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}")
    if d2:
        sit = str(d2.get("situacao_cadastral",""))
        sit = SITUACOES.get(sit, sit) if sit.isdigit() else sit
        return {
            "cnpj": cnpj,
            "razao_social":  _limpar(d2.get("razao_social","")),
            "nome_fantasia": d2.get("nome_fantasia",""),
            "situacao":      sit,
            "data_situacao": "",
            "motivo_situacao":"",
            "abertura":      d2.get("data_inicio_atividade",""),
            "atividade":     d2.get("cnae_fiscal_descricao",""),
            "natureza":      "",
            "logradouro":    d2.get("logradouro",""),
            "numero":        d2.get("numero",""),
            "bairro":        d2.get("bairro",""),
            "municipio":     d2.get("municipio",""),
            "uf":            d2.get("uf",""),
            "cep":           d2.get("cep",""),
            "email":         str(d2.get("email") or "").lower().strip(),
            "telefone":      _tel(d2.get("ddd_telefone_1","")),
            "porte":         d2.get("porte",""),
            "capital_social":str(d2.get("capital_social","")),
            "qsa":           d2.get("qsa",[]) or [],
        }
    return None
