# ── 1. CNPJ.BIZ TURBO (agora pega MEI novo + telefone/email mascarado + QSA automático) ──
def _cnpj_biz(cnpj):
    html = _get(f"https://cnpj.biz/{cnpj}")
    if not html or "não encontrado" in html.lower():
        return {}

    dados = {}
    patterns = {
        "razao_social": r'<strong>Razão Social:</strong>\s*([^<]+?)(?=\s*Clique|<strong>)',
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
    end_match = re.search(r'(\w.*?),?\s*(\d+)?\s*<br>([^<]+)<br>(\d{5}-\d{3})<br>([^<]+)<br>([^<]+)', html, re.I)
    if end_match:
        dados["logradouro"] = end_match.group(1).strip()
        dados["numero"] = end_match.group(2) or ""
        dados["bairro"] = end_match.group(3).strip()
        dados["cep"] = end_match.group(4).strip()
        dados["municipio"] = end_match.group(5).strip()
        dados["uf"] = end_match.group(6).strip()

    # Telefone e Email (mesmo mascarado)
    tel_m = re.search(r'Telefone:\s*\*\*([^\*]+)\*\*', html, re.I)
    if tel_m: dados["telefone"] = tel_m.group(1).strip()
    email_m = re.search(r'Email:\s*\*\*([^\*]+)\*\*', html, re.I)
    if email_m: dados["email"] = email_m.group(1).strip()

    # QSA automático para MEI (o próprio dono)
    if "Empresário (Individual)" in html or "MEI" in html.upper():
        nome_dono = dados.get("razao_social", "").replace("65.574.681 ", "").strip()
        dados["qsa"] = [{"nome": nome_dono or dados.get("razao_social",""), "qualificacao_socio": "Sócio Único - MEI"}]

    return dados

# ── 2. _cnpj_dados (sempre prioriza cnpj.biz) ──
def _cnpj_dados(cnpj):
    dados = _cnpj_biz(cnpj)
    if dados.get("razao_social"):
        return dados

    # fallbacks antigos (mantém exatamente como você tinha)
    d = _get_json(f"https://minhareceita.org/{cnpj}")
    if d and d.get("cnpj"):
        # ... (seu código antigo aqui)
        return { ... }  # deixa como estava antes

    return {}
