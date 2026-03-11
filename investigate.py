"""Motor principal de investigação — detecta tipo e despacha módulos."""
import re, sys, os

import cnpj_lookup, domain_intelligence, email_breach_lookup
import phone_lookup, username_discovery, github_intelligence
import social_crawler
import correlation_engine, graph_engine

def detect_type(target: str) -> str:
    t = target.strip()
    digits = re.sub(r'\D','',t)
    if len(digits) == 14: return "cnpj"
    if len(digits) == 11 and not t.startswith("+"): return "cpf"
    if re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', t): return "email"
    if re.match(r'^[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(\.[a-zA-Z]{2,})?$', t): return "domain"
    if re.match(r'^\+?[\d\s\(\)\-]{8,15}$', t): return "phone"
    if re.match(r'^[a-zA-Z0-9_\-\.]{2,40}$', t) and ' ' not in t: return "username"
    if ' ' in t: return "name"
    return "unknown"

def investigate(target: str, progress_cb=None) -> dict:
    """
    Roda investigação completa.
    progress_cb: função(msg) chamada durante a execução
    """
    def prog(msg):
        if progress_cb: progress_cb(msg)

    tipo = detect_type(target)
    results = {"target": target, "tipo": tipo}

    prog(f"🔍 Tipo detectado: {tipo.upper()}")

    # ── CNPJ ────────────────────────────────────────
    if tipo == "cnpj":
        prog("🏢 Consultando Receita Federal...")
        cnpj_data = cnpj_lookup.lookup(target)
        results["cnpj"] = cnpj_data or {}

        if cnpj_data:
            # Descobrir domínio
            email = cnpj_data.get("email","")
            dominio = None
            if email and "@" in email:
                dom = email.split("@")[-1]
                lixo = {"gmail.com","hotmail.com","yahoo.com","outlook.com","uol.com.br","bol.com.br"}
                if dom not in lixo:
                    dominio = dom
            if not dominio:
                nome = cnpj_data.get("nome_fantasia") or cnpj_data.get("razao_social","")
                nome_limpo = re.sub(r'[^a-z0-9]','', nome.lower().split()[0]) if nome else ""
                if nome_limpo and len(nome_limpo) > 3:
                    import socket
                    for tld in [".com.br",".com",".net"]:
                        try:
                            socket.gethostbyname(f"{nome_limpo}{tld}")
                            dominio = f"{nome_limpo}{tld}"
                            break
                        except: pass

            if dominio:
                prog(f"🌐 Analisando domínio: {dominio}...")
                results["dominio"] = domain_intelligence.lookup(dominio)
            else:
                results["dominio"] = {}

            # Redes sociais da empresa
            nome_emp = cnpj_data.get("nome_fantasia") or cnpj_data.get("razao_social","")
            if nome_emp:
                prog("📱 Buscando redes sociais...")
                results["cnpj_redes"] = {"redes": social_crawler.buscar_empresa(nome_emp, dominio or "")}

            # Sócios nas redes
            socios = cnpj_data.get("qsa",[]) or []
            if socios:
                prog("👤 Investigando sócios...")
                results["socios_redes"] = []
                for s in socios[:3]:
                    nome_s = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","")).strip()
                    if nome_s:
                        redes_s = social_crawler.buscar_pessoa(nome_s, nome_emp)
                        results["socios_redes"].append({"nome": nome_s, "redes": redes_s})

    # ── DOMÍNIO ──────────────────────────────────────
    elif tipo == "domain":
        prog("🌐 Analisando domínio...")
        results["dominio"] = domain_intelligence.lookup(target)
        dono = results["dominio"].get("dono")
        if dono:
            prog(f"👤 Investigando dono: {dono}...")
            results["dono_redes"] = social_crawler.buscar_pessoa(dono)

    # ── EMAIL ────────────────────────────────────────
    elif tipo == "email":
        prog("📧 Analisando email...")
        results["email"] = email_breach_lookup.lookup(target)
        # Username do email
        username = target.split("@")[0]
        prog(f"🔍 Buscando username: {username}...")
        results["username"] = username_discovery.lookup(username)
        results["github"]   = github_intelligence.lookup(username)

    # ── TELEFONE ─────────────────────────────────────
    elif tipo == "phone":
        prog("📞 Analisando telefone...")
        results["phone"] = phone_lookup.lookup(target)

    # ── USERNAME ─────────────────────────────────────
    elif tipo == "username":
        prog(f"👤 Buscando @{target} em 40+ plataformas...")
        results["username"] = username_discovery.lookup(target)
        prog("🐙 GitHub intelligence...")
        results["github"]   = github_intelligence.lookup(target)

    # ── NOME ─────────────────────────────────────────
    elif tipo == "name":
        prog(f"🔍 Buscando pessoa: {target}...")
        results["pessoa"] = social_crawler.buscar_pessoa(target)

    # ── CPF ──────────────────────────────────────────
    elif tipo == "cpf":
        prog("🪪 CPF detectado — apenas fontes públicas disponíveis...")
        results["cpf"] = {"nota": "Consulta via fontes públicas apenas.", "digits": re.sub(r'\D','',target)}

    # Correlação final
    prog("🧠 Correlacionando dados...")
    perfil = correlation_engine.correlate(results)
    results["perfil"] = perfil

    # Grafo
    prog("🕸️ Gerando grafo...")
    results["grafo"] = graph_engine.build_graph(perfil, results)

    prog("✅ Investigação concluída!")
    return results
