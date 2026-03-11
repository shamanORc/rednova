import requests

def check_email(email):

    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"

    headers = {"User-Agent":"rednova"}

    r = requests.get(url, headers=headers)

    if r.status_code == 200:
        return r.json()

    return []
