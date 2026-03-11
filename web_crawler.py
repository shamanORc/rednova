"""HTTP utilities compartilhadas."""
import ssl, json, urllib.request, urllib.parse, re, time
from settings import HEADERS, TIMEOUT

def _ctx():
    c = ssl.create_default_context()
    c.check_hostname = False
    c.verify_mode = ssl.CERT_NONE
    return c

def get_html(url, extra_headers=None, timeout=None):
    try:
        h = dict(HEADERS)
        if extra_headers:
            h.update(extra_headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT, context=_ctx()) as r:
            return r.read(262144).decode("utf-8", errors="ignore")
    except:
        return ""

def get_json(url, extra_headers=None, timeout=None):
    try:
        h = dict(HEADERS)
        h["Accept"] = "application/json"
        if extra_headers:
            h.update(extra_headers)
        req = urllib.request.Request(url, headers=h)
        with urllib.request.urlopen(req, timeout=timeout or TIMEOUT, context=_ctx()) as r:
            return json.loads(r.read())
    except:
        return None

def dork(query, engine="ddg"):
    q = urllib.parse.quote(query)
    urls = [
        f"https://html.duckduckgo.com/html/?q={q}",
        f"https://www.bing.com/search?q={q}",
    ]
    for url in urls:
        html = get_html(url)
        if html and len(html) > 500:
            return html
        time.sleep(0.5)
    return ""

def extract_emails(text):
    pat = re.compile(r'[a-zA-Z0-9._%+\-]{2,40}@[a-zA-Z0-9.\-]{2,40}\.[a-zA-Z]{2,6}')
    lixo = {"noreply","no-reply","sentry.io","wixpress.com","example.com",
             "duckduckgo.com","bing.com","google.com","cloudflare.com"}
    found = []
    for e in pat.findall(text):
        dom = e.split("@")[-1].lower()
        if dom not in lixo and not any(x in e for x in ["@2x","@3x","pixel"]):
            found.append(e.lower())
    return list(dict.fromkeys(found))

def extract_phones(text):
    pat = re.compile(r'(?:\+?55\s?)?(?:\(?\d{2}\)?\s?)(?:9\d{4}|\d{4})[\s\-]?\d{4}')
    return list(dict.fromkeys(p.strip() for p in pat.findall(text)))[:10]
