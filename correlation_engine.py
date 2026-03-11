"""Correlaciona todos os dados coletados e monta o perfil unificado."""
import re

def correlate(results: dict) -> dict:
    """
    Recebe o dict com resultados de todos os módulos OSINT
    e retorna um perfil consolidado com scores de confiança.
    """
    perfil = {
        "target":     results.get("target",""),
        "tipo":       results.get("tipo",""),
        "identidades": [],
        "emails":     [],
        "telefones":  [],
        "dominios":   [],
        "empresas":   [],
        "redes":      {},
        "vazamentos": [],
        "timeline":   [],
        "risk_score": 0,
        "confianca":  {},
    }

    # Agregar emails de todas as fontes
    emails = set()
    for fonte in ["cnpj","dominio","email","phone","github"]:
        d = results.get(fonte, {})
        if isinstance(d, dict):
            emails.update(d.get("emails", []) or [])
            emails.update(d.get("emails_commits", []) or [])
            emails.update(d.get("emails_rdap", []) or [])
            if d.get("email"): emails.add(d["email"])
            if d.get("perfil",{}).get("email"): emails.add(d["perfil"]["email"])
    perfil["emails"] = [e for e in emails if e and "@" in e and len(e) > 5]

    # Agregar telefones
    phones = set()
    for fonte in ["cnpj","dominio","phone"]:
        d = results.get(fonte, {})
        if isinstance(d, dict):
            phones.update(d.get("phones", []) or [])
            phones.update(d.get("telefones", []) or [])
            if d.get("telefone"): phones.add(d["telefone"])
    perfil["telefones"] = [p for p in phones if p and len(re.sub(r'\D','',p)) >= 8]

    # Agregar redes sociais
    for fonte in ["cnpj_redes","dominio","username"]:
        d = results.get(fonte, {})
        if isinstance(d, dict):
            for k, v in d.get("redes",{}).items():
                if k not in perfil["redes"]:
                    perfil["redes"][k] = v
            plats = d.get("plataformas",[])
            for p in (plats or []):
                rede = p.get("platform","").lower().replace("/","_").replace(" ","_")
                if rede and p.get("url") and rede not in perfil["redes"]:
                    perfil["redes"][rede] = p["url"]

    # Agregar vazamentos
    for fonte in ["cnpj","dominio","email"]:
        d = results.get(fonte, {})
        if isinstance(d, dict):
            perfil["vazamentos"] += d.get("vazamentos", []) or []
            perfil["vazamentos"] += d.get("breaches", []) or []

    # Identidades (nomes de sócios, dono de domínio, etc)
    identidades = set()
    cnpj_data = results.get("cnpj",{})
    if cnpj_data:
        nome = cnpj_data.get("razao_social","")
        if nome: identidades.add(nome)
        for s in (cnpj_data.get("qsa",[]) or []):
            n = s.get("nome_socio") or s.get("nome","")
            if n: identidades.add(re.sub(r'\s+\d{11,14}\s*$','',n).strip())
    dom_data = results.get("dominio",{})
    if dom_data and dom_data.get("dono"):
        identidades.add(dom_data["dono"])
    perfil["identidades"] = list(identidades)

    # Timeline
    timeline = []
    if cnpj_data and cnpj_data.get("abertura"):
        timeline.append({"data": cnpj_data["abertura"], "evento": "Empresa aberta", "tipo": "empresa"})
    if cnpj_data and cnpj_data.get("data_situacao") and cnpj_data.get("situacao") != "ATIVA":
        timeline.append({"data": cnpj_data["data_situacao"],
                         "evento": f"Empresa {cnpj_data.get('situacao','?')}", "tipo": "empresa"})
    if dom_data and dom_data.get("criado"):
        timeline.append({"data": dom_data["criado"], "evento": "Domínio registrado", "tipo": "dominio"})
    if dom_data and dom_data.get("expira"):
        timeline.append({"data": dom_data["expira"], "evento": "Domínio expira", "tipo": "dominio"})
    gh = results.get("github",{}).get("perfil",{})
    if gh and gh.get("criado"):
        timeline.append({"data": gh["criado"], "evento": "GitHub criado", "tipo": "github"})
    for v in perfil["vazamentos"]:
        if v.get("data"):
            timeline.append({"data": v["data"], "evento": f"Vazamento: {v.get('nome','?')}", "tipo": "breach"})
    perfil["timeline"] = sorted(timeline, key=lambda x: x.get("data",""), reverse=False)

    # Risk score
    score = 0
    score += min(len(perfil["vazamentos"]) * 20, 40)
    score += min(len(perfil["emails"]) * 5, 20)
    score += 10 if perfil["redes"] else 0
    score += 10 if perfil["telefones"] else 0
    score += 5  if perfil["identidades"] else 0
    perfil["risk_score"] = min(score, 100)

    # Confiança por rede
    for rede in perfil["redes"]:
        if rede in ("linkedin","github","twitter"):
            perfil["confianca"][rede] = 90
        elif rede in ("instagram","facebook","tiktok"):
            perfil["confianca"][rede] = 75
        else:
            perfil["confianca"][rede] = 60

    return perfil
