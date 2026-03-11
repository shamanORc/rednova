from api.username import scan_username
from api.email import check_email
from api.domain import lookup_domain

def investigate(target):

    result = {}

    if "@" in target:
        result["breach"] = check_email(target)

    if "." in target:
        result["domain"] = lookup_domain(target)

    result["social"] = scan_username(target)

    return result
