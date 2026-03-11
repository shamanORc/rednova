"""
OSINT CNPJ — Consulta Receita Federal via API pública
APIs: BrasilAPI (gratuita, sem key)
"""
import re
import json
import urllib.request
import urllib.error

def limpar_cnpj(cnpj: str) -> str:
    return re.sub(r'\D', '', cnpj)

def consultar(cnpj_raw: str) -> str:
    cnpj = limpar_cnpj(cnpj_raw)
    if len(cnpj) != 14:
        return "❌ CNPJ inválido. Envie 14 dígitos."

    resultado = _brasilapi(cnpj)
    if not resultado:
        resultado = _receitaws(cnpj)
    if not resultado:
        return "❌ CNPJ não encontrado nas bases públicas."

    return _formatar(resultado, cnpj)

def _brasilapi(cnpj: str) -> dict:
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception:
        return None

def _receitaws(cnpj: str) -> dict:
    url = f"https://receitaws.com.br/v1/cnpj/{cnpj}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            # Normalizar para formato BrasilAPI
            return {
                "razao_social":        data.get("nome",""),
                "nome_fantasia":       data.get("fantasia",""),
                "situacao_cadastral":  data.get("situacao",""),
                "cnae_fiscal_descricao": data.get("atividade_principal",[{}])[0].get("text",""),
                "logradouro":          data.get("logradouro",""),
                "numero":              data.get("numero",""),
                "municipio":           data.get("municipio",""),
                "uf":                  data.get("uf",""),
                "cep":                 data.get("cep",""),
                "telefone":            data.get("telefone",""),
                "email":               data.get("email",""),
                "data_inicio_atividade": data.get("abertura",""),
                "qsa":                 [{"nome_socio": s.get("nome",""),
                                         "qualificacao_socio": s.get("qual","")}
                                        for s in data.get("qsa",[])],
                "capital_social":      data.get("capital_social",""),
                "natureza_juridica":   data.get("natureza_juridica",""),
                "porte":               data.get("porte",""),
            }
    except Exception:
        return None

def _formatar(d: dict, cnpj: str) -> str:
    cnpj_fmt = f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

    sit = d.get("situacao_cadastral","?")
    sit_icon = "✅" if "ATIVA" in str(sit).upper() else "❌"

    socios = d.get("qsa", [])
    socios_txt = ""
    for s in socios[:5]:
        nome = s.get("nome_socio", s.get("nome","?"))
        qual = s.get("qualificacao_socio", s.get("qual",""))
        socios_txt += f"  • {nome} ({qual})\n"
    if not socios_txt:
        socios_txt = "  Não informado\n"

    endereco = (f"{d.get('logradouro','')} {d.get('numero','')}, "
                f"{d.get('municipio','')} - {d.get('uf','')} "
                f"CEP: {d.get('cep','')}")

    return f"""🏢 *CONSULTA CNPJ — REDNOVA OSINT*

📋 *CNPJ:* `{cnpj_fmt}`
🏷️ *Razão Social:* {d.get('razao_social','?')}
🏪 *Fantasia:* {d.get('nome_fantasia') or 'Não informado'}
{sit_icon} *Situação:* {sit}
📅 *Abertura:* {d.get('data_inicio_atividade','?')}

🏭 *Atividade:* {d.get('cnae_fiscal_descricao','?')}
⚖️ *Natureza:* {d.get('natureza_juridica','?')}
🏢 *Porte:* {d.get('porte','?')}
💰 *Capital Social:* R$ {d.get('capital_social','?')}

📍 *Endereço:*
  {endereco}

📞 *Telefone:* {d.get('telefone') or 'Não informado'}
📧 *Email:* {d.get('email') or 'Não informado'}

👥 *Sócios / QSA:*
{socios_txt}
🔴 _RedNova OSINT — {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}_"""
