"""Gera grafo de relacionamentos em JSON para o dashboard."""
import json

def build_graph(perfil: dict, results: dict) -> dict:
    nodes = []
    edges = []
    node_ids = {}

    def add_node(nid, label, tipo, url="", score=0):
        if nid not in node_ids:
            node_ids[nid] = True
            nodes.append({"id": nid, "label": label, "type": tipo,
                          "url": url, "score": score})

    def add_edge(source, target, label=""):
        edges.append({"source": source, "target": target, "label": label})

    target = perfil.get("target", "alvo")
    add_node(f"target_{target}", target, "target")

    # Identidades
    for nome in perfil.get("identidades",[]):
        nid = f"pessoa_{nome[:20]}"
        add_node(nid, nome, "pessoa")
        add_edge(f"target_{target}", nid, "é")

    # Emails
    for email in perfil.get("emails",[])[:8]:
        nid = f"email_{email}"
        add_node(nid, email, "email")
        add_edge(f"target_{target}", nid, "email")

    # Telefones
    for tel in perfil.get("telefones",[])[:5]:
        nid = f"tel_{tel}"
        add_node(nid, tel, "telefone")
        add_edge(f"target_{target}", nid, "tel")

    # Redes sociais
    for rede, url in perfil.get("redes",{}).items():
        nid = f"rede_{rede}"
        score = perfil.get("confianca",{}).get(rede, 60)
        add_node(nid, rede.capitalize(), "rede_social", url=url, score=score)
        add_edge(f"target_{target}", nid, f"{score}%")

    # Domínios
    dom_data = results.get("dominio",{})
    if dom_data and dom_data.get("dominio"):
        dom = dom_data["dominio"]
        nid = f"dominio_{dom}"
        add_node(nid, dom, "dominio")
        add_edge(f"target_{target}", nid, "domínio")
        for sub in dom_data.get("subdominios",[])[:5]:
            sid = f"sub_{sub}"
            add_node(sid, sub, "subdominio")
            add_edge(nid, sid, "sub")

    # Empresas / CNPJ
    cnpj_data = results.get("cnpj",{})
    if cnpj_data:
        emp = cnpj_data.get("nome_fantasia") or cnpj_data.get("razao_social","")
        if emp:
            nid = f"empresa_{emp[:20]}"
            add_node(nid, emp, "empresa")
            add_edge(f"target_{target}", nid, "empresa")

    # Vazamentos
    for v in perfil.get("vazamentos",[]):
        nid = f"breach_{v.get('nome','?')}"
        add_node(nid, f"🔴 {v.get('nome','?')}", "breach")
        add_edge(f"target_{target}", nid, "vazamento")

    return {"nodes": nodes, "edges": edges}
