import whois

def lookup_domain(domain):

    w = whois.whois(domain)

    return {
        "domain": domain,
        "owner": w.name,
        "email": w.emails,
        "created": str(w.creation_date)
    }
