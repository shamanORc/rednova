"""Verifica username em 40+ plataformas em paralelo."""
import threading, time
from web_crawler import get_html
from settings import USERNAME_PLATFORMS

def _check(platform, username, results):
    url = platform["url"].format(username)
    html = get_html(url, timeout=8)
    found = False
    if html and len(html) > 200:
        not_found_patterns = [
            "page not found","user not found","404","this account doesn't exist",
            "sorry, this page","isn't available","does not exist","no user found",
            "profile not found","couldn't find","página não encontrada",
        ]
        html_lower = html.lower()
        if not any(p in html_lower for p in not_found_patterns):
            if username.lower() in html_lower:
                found = True
    if found:
        results.append({"platform": platform["name"], "url": url, "found": True})

def search_username(username):
    results = []
    threads = []
    for platform in USERNAME_PLATFORMS:
        t = threading.Thread(target=_check, args=(platform, username, results))
        t.daemon = True
        threads.append(t)
        t.start()
        if len(threads) % 10 == 0:
            time.sleep(0.3)
    for t in threads:
        t.join(timeout=12)
    return sorted(results, key=lambda x: x["platform"])
