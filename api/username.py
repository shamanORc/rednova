import requests

sites = [
 "https://github.com/{}",
 "https://twitter.com/{}",
 "https://instagram.com/{}",
 "https://tiktok.com/@{}",
 "https://linkedin.com/in/{}"
]

def scan_username(user):

    found = []

    for s in sites:

        url = s.format(user)

        try:
            r = requests.get(url, timeout=5)

            if r.status_code == 200:
                found.append(url)

        except:
            pass

    return found
