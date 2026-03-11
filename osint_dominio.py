"""
OSINT Domínio — WHOIS, DNS, IPs, Subdomínios, Certificados, Shodan free
"""
import socket, ssl, subprocess, json, re, urllib.request, urllib.error
from datetime import datetime

def consultar(dominio: str) -> str:
    dominio = dominio.replace("https://","").replace("http://","").strip("/").lower()
    secoes = []

    secoes.append(_dns(dominio))
    secoes.append(_whois(dominio))
    secoes.append(_ssl_cert(dominio))
    secoes.append(_subdomains_crt(dominio))
    secoes.append(_shodan_free(dominio))
    secoes.append(_http_info(dominio))
    secoes.append(_spf_bypass(dominio))

    return "\n\n".join(s for s in secoes if s)

def _dns(dominio):
    out = ["🌐 *DNS RECORDS*"]
    for rt in ["A","AAAA","MX","NS","TXT","CNAME"]:
        try:
            result = subprocess.run(
                ["dig", "+short", rt, dominio],
                capture_output=True, text=True, timeout=8
            )
            vals = [v.strip() for v in result.stdout.splitlines() if v.strip()]
            if vals:
                out.append(f"  *{rt}:* {' | '.join(vals[:3])}")
        except Exception:
            pass
    return "\n".join(out) if len(out) > 1 else ""

def _whois(dominio):
    try:
        result = subprocess.run(
            ["whois", dominio], capture_output=True, text=True, timeout=15
        )
        lines = result.stdout.splitlines()
        fields = {}
        for line in lines:
            for key in ["Registrar:","Creation Date:","Expiry Date:",
                        "Registrant Organization:","Name Server:"]:
                if key.lower() in line.lower() and ":" in line:
                    val = line.split(":",1)[-1].strip()
                    if val and key not in fields:
                        fields[key.rstrip(":")] = val[:80]

        if not fields:
            return ""
        out = ["📋 *WHOIS*"]
        for k, v in list(fields.items())[:6]:
            out.append(f"  *{k}:* {v}")
        return "\n".join(out)
    except Exception:
        return ""

def _ssl_cert(dominio):
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with socket.create_connection((dominio, 443), timeout=6) as s:
            with ctx.wrap_socket(s, server_hostname=dominio) as ss:
                cert = ss.getpeercert()
                issuer = dict(x[0] for x in cert.get("issuer",[]))
                sans   = [v for t,v in cert.get("subjectAltName",[]) if t=="DNS"]
                expiry = cert.get("notAfter","?")
                out = ["🔒 *SSL/TLS*"]
                out.append(f"  *Emitido por:* {issuer.get('organizationName','?')}")
                out.append(f"  *Expira:* {expiry}")
                if sans:
                    out.append(f"  *SANs ({len(sans)}):* {' | '.join(sans[:6])}")
                return "\n".join(out)
    except Exception:
        return ""

def _subdomains_crt(dominio):
    """Busca subdomínios no crt.sh (certificados públicos)."""
    try:
        url = f"https://crt.sh/?q=%.{dominio}&output=json"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
        subs = set()
        for entry in data:
            name = entry.get("name_value","")
            for sub in name.splitlines():
                sub = sub.strip().lstrip("*.")
                if dominio in sub and sub != dominio:
                    subs.add(sub)
        if not subs:
            return ""
        out = [f"🔍 *SUBDOMÍNIOS via crt.sh ({len(subs)} encontrados)*"]
        for s in sorted(subs)[:20]:
            out.append(f"  • `{s}`")
        if len(subs) > 20:
            out.append(f"  _...e mais {len(subs)-20}_")
        return "\n".join(out)
    except Exception:
        return ""

def _shodan_free(dominio):
    """Shodan DNS lookup sem API key."""
    try:
        url = f"https://api.shodan.io/dns/resolve?hostnames={dominio}"
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read())
        ip = data.get(dominio,"")
        if not ip:
            return ""
        return f"🔎 *SHODAN*\n  *IP resolvido:* `{ip}`\n  Acesse: https://www.shodan.io/host/{ip}"
    except Exception:
        # Fallback: resolver localmente
        try:
            ip = socket.gethostbyname(dominio)
            return f"📡 *IP Principal:* `{ip}`\n  Shodan: https://www.shodan.io/host/{ip}"
        except Exception:
            return ""

def _http_info(dominio):
    """Headers HTTP relevantes."""
    try:
        import urllib.request, ssl
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            f"https://{dominio}",
            headers={"User-Agent":"Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=8, context=ctx) as r:
            hdrs = dict(r.headers)
            status = r.status
    except Exception as e:
        try:
            code = e.code if hasattr(e,'code') else None
            hdrs = dict(e.headers) if hasattr(e,'headers') else {}
            status = code
        except Exception:
            return ""

    out = [f"🌍 *HTTP INFO*"]
    out.append(f"  *Status:* {status}")
    for h in ["Server","X-Powered-By","CF-Ray","Via","X-Generator"]:
        val = hdrs.get(h, hdrs.get(h.lower(),""))
        if val:
            out.append(f"  *{h}:* {val}")

    # Security headers ausentes
    missing = []
    for h in ["Strict-Transport-Security","Content-Security-Policy","X-Frame-Options"]:
        if h.lower() not in {k.lower() for k in hdrs}:
            missing.append(h)
    if missing:
        out.append(f"  ⚠️ *Headers ausentes:* {', '.join(missing)}")

    return "\n".join(out)

def _spf_bypass(dominio):
    """Tenta descobrir IP real via registros SPF/MX."""
    ips_encontrados = []
    try:
        result = subprocess.run(
            ["dig", "+short", "TXT", dominio],
            capture_output=True, text=True, timeout=8
        )
        for line in result.stdout.splitlines():
            # Extrair IPs do SPF
            ips = re.findall(r'ip4:(\d+\.\d+\.\d+\.\d+)', line)
            ips_encontrados.extend(ips)
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["dig", "+short", "MX", dominio],
            capture_output=True, text=True, timeout=8
        )
        for mx in result.stdout.splitlines():
            parts = mx.split()
            if len(parts) >= 2:
                try:
                    ip = socket.gethostbyname(parts[-1].rstrip("."))
                    ips_encontrados.append(f"{ip} (MX: {parts[-1]})")
                except Exception:
                    pass
    except Exception:
        pass

    if not ips_encontrados:
        return ""

    out = ["🕵️ *BYPASS CLOUDFLARE (SPF/MX)*"]
    for ip in ips_encontrados[:5]:
        out.append(f"  • `{ip}`")
    out.append("  ⚠️ _Possível IP real do servidor_")
    return "\n".join(out)
