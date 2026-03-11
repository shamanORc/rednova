"""OSINT de domínio — RDAP registro.br + crt.sh + DNS + Shodan"""
import re, json, socket, ssl, subprocess, time
from web_crawler import get_json, get_html, extract_emails, extract_phones

def _rdap(dominio):
    dados = {}
    d = get_json(f"https://rdap.registro.br/domain/{dominio}")
    if not d: return dados
    for ev in d.get("events",[]):
        a = ev.get("eventAction","")
        dt = ev.get("eventDate","")[:10]
        if "registration" in a: dados["criado"] = dt
        elif "expiration" in a: dados["expira"] = dt
    dados["nameservers"] = [ns.get("ldhName","") for ns in d.get("nameservers",[])]
    for ent in d.get("entities",[]):
        roles = ent.get("roles",[])
        nome, emails, fones = None, [], []
        for item in (ent.get("vcardArray",["",[]]) or ["",[]]) [1]:
            if not isinstance(item,list) or len(item)<4: continue
            if item[0]=="fn":    nome = item[3]
            elif item[0]=="email": emails.append(item[3])
            elif item[0]=="tel":   fones.append(str(item[3]).replace("tel:",""))
        for sub in ent.get("entities",[]):
            for item in (sub.get("vcardArray",["",[]]) or ["",[]]) [1]:
                if not isinstance(item,list) or len(item)<4: continue
                if item[0]=="fn" and not nome: nome = item[3]
                elif item[0]=="email": emails.append(item[3])
                elif item[0]=="tel":   fones.append(str(item[3]).replace("tel:",""))
        if "registrant" in roles:
            dados["dono"] = nome
            dados["emails"] = list(dict.fromkeys(emails))
            dados["telefones"] = list(dict.fromkeys(fones))
    return dados

def _subdominios(dominio):
    try:
        data = get_json(f"https://crt.sh/?q=%.{dominio}&output=json")
        if not data: return []
        subs = set()
        for e in data:
            for name in e.get("name_value","").splitlines():
                name = name.strip().lstrip("*.")
                if dominio in name: subs.add(name.lower())
        return sorted(subs)[:30]
    except: return []

def _ips(hosts):
    ips = {}
    for h in hosts[:8]:
        try:
            ip = socket.gethostbyname(h)
            ips[h] = ip
        except: pass
    return ips

def _scrape(dominio):
    result = {"emails":[], "phones":[], "redes":{}}
    for url in [f"https://{dominio}", f"https://www.{dominio}",
                f"https://{dominio}/contato", f"https://{dominio}/sobre"]:
        html = get_html(url)
        if html:
            result["emails"]  += extract_emails(html)
            result["phones"]  += extract_phones(html)
            # Redes
            pats = {
                "instagram": r'instagram\.com/([A-Za-z0-9\._]{2,40})(?:/|\b)',
                "facebook":  r'facebook\.com/(?!sharer|tr|plugins)([A-Za-z0-9\._\-]{4,50})',
                "linkedin":  r'linkedin\.com/company/([A-Za-z0-9\-_\.]{2,60})',
                "youtube":   r'youtube\.com/(?:@|channel/)([A-Za-z0-9\._\-]{2,60})',
                "whatsapp":  r'(?:wa\.me|whatsapp\.com/send\?phone=)([0-9]{10,15})',
            }
            ignorar = {"login","sharer","tr","plugins","dialog","share","home","feed"}
            for rede, pat in pats.items():
                if rede in result["redes"]: continue
                m = re.search(pat, html, re.IGNORECASE)
                if m:
                    handle = m.group(1).rstrip("/").split("?")[0]
                    if handle.lower() not in ignorar:
                        bases = {"instagram":"https://instagram.com/",
                                 "facebook":"https://facebook.com/",
                                 "linkedin":"https://linkedin.com/company/",
                                 "youtube":"https://youtube.com/@",
                                 "whatsapp":"https://wa.me/"}
                        result["redes"][rede] = bases[rede] + handle
        time.sleep(0.3)
    result["emails"] = list(dict.fromkeys(result["emails"]))[:15]
    result["phones"] = list(dict.fromkeys(result["phones"]))[:8]
    return result

def _hibp(dominio):
    try:
        data = get_json("https://haveibeenpwned.com/api/v3/breaches")
        if not data: return []
        base = dominio.split(".")[0].lower()
        return [{"nome":b["Name"],"data":b["BreachDate"],
                 "contas":b["PwnCount"],"tipos":", ".join(b.get("DataClasses",[])[:4])}
                for b in data if base in b.get("Domain","").lower() or base in b.get("Name","").lower()][:5]
    except: return []

def lookup(dominio):
    dominio = dominio.replace("https://","").replace("http://","").strip("/").lower()
    rdap    = _rdap(dominio)
    subs    = _subdominios(dominio)
    all_hosts = [dominio] + subs[:5]
    ips     = _ips(all_hosts)
    site    = _scrape(dominio)
    vazamentos = _hibp(dominio)

    emails = list(dict.fromkeys((rdap.get("emails",[]) + site["emails"])))
    phones = list(dict.fromkeys((rdap.get("telefones",[]) + site["phones"])))

    return {
        "dominio":     dominio,
        "dono":        rdap.get("dono"),
        "criado":      rdap.get("criado"),
        "expira":      rdap.get("expira"),
        "nameservers": rdap.get("nameservers",[]),
        "emails_rdap": rdap.get("emails",[]),
        "subdominios": subs,
        "ips":         ips,
        "emails":      emails[:15],
        "phones":      phones[:8],
        "redes":       site["redes"],
        "vazamentos":  vazamentos,
    }
