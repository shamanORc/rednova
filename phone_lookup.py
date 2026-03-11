"""Análise de telefone — DDD, operadora, tipo."""
import re
from web_crawler import dork, extract_emails

DDD_CIDADES = {
    "11":"São Paulo/SP","12":"São José dos Campos/SP","13":"Santos/SP","14":"Bauru/SP",
    "15":"Sorocaba/SP","16":"Ribeirão Preto/SP","17":"São José do Rio Preto/SP",
    "18":"Presidente Prudente/SP","19":"Campinas/SP","21":"Rio de Janeiro/RJ",
    "22":"Campos dos Goytacazes/RJ","24":"Volta Redonda/RJ","27":"Vitória/ES",
    "28":"Cachoeiro de Itapemirim/ES","31":"Belo Horizonte/MG","32":"Juiz de Fora/MG",
    "33":"Governador Valadares/MG","34":"Uberlândia/MG","35":"Poços de Caldas/MG",
    "37":"Divinópolis/MG","38":"Montes Claros/MG","41":"Curitiba/PR","42":"Ponta Grossa/PR",
    "43":"Londrina/PR","44":"Maringá/PR","45":"Foz do Iguaçu/PR","46":"Francisco Beltrão/PR",
    "47":"Joinville/SC","48":"Florianópolis/SC","49":"Chapecó/SC","51":"Porto Alegre/RS",
    "53":"Pelotas/RS","54":"Caxias do Sul/RS","55":"Santa Maria/RS","61":"Brasília/DF",
    "62":"Goiânia/GO","63":"Palmas/TO","64":"Rio Verde/GO","65":"Cuiabá/MT",
    "66":"Rondonópolis/MT","67":"Campo Grande/MS","68":"Rio Branco/AC","69":"Porto Velho/RO",
    "71":"Salvador/BA","73":"Ilhéus/BA","74":"Juazeiro/BA","75":"Feira de Santana/BA",
    "77":"Vitória da Conquista/BA","79":"Aracaju/SE","81":"Recife/PE","82":"Maceió/AL",
    "83":"João Pessoa/PB","84":"Natal/RN","85":"Fortaleza/CE","86":"Teresina/PI",
    "87":"Caruaru/PE","88":"Juazeiro do Norte/CE","89":"Picos/PI","91":"Belém/PA",
    "92":"Manaus/AM","93":"Santarém/PA","94":"Marabá/PA","95":"Boa Vista/RR",
    "96":"Macapá/AP","97":"Coari/AM","98":"São Luís/MA","99":"Imperatriz/MA",
}

def lookup(telefone_raw):
    digits = re.sub(r'\D','', telefone_raw)
    if len(digits) < 10: return None

    # Remove 55 do início
    if digits.startswith("55") and len(digits) >= 12:
        digits = digits[2:]

    ddd   = digits[:2]
    resto = digits[2:]
    tipo  = "Celular" if resto.startswith("9") and len(resto)==9 else "Fixo"

    resultado = {
        "telefone_raw": telefone_raw,
        "digits":       digits,
        "ddd":          ddd,
        "cidade":       DDD_CIDADES.get(ddd, "Desconhecida"),
        "tipo":         tipo,
        "mencoes":      [],
        "emails":       [],
        "nomes":        [],
        "links":        [],
    }

    # Busca pública do número
    for query in [f'"{telefone_raw}"', f'"{ddd}) {resto[:5]}"']:
        html = dork(query)
        if not html: continue
        resultado["emails"] += extract_emails(html)
        # Nomes próximos ao número
        idx = html.lower().find(ddd + resto[:4])
        if idx > 0:
            trecho = html[max(0,idx-200):idx+200]
            nomes = re.findall(r'[A-Z][a-záéíóúãõâêîôûàèìòùç]{2,}\s+[A-Z][a-záéíóúãõâêîôûàèìòùç]{2,}(?:\s+[A-Z][a-záéíóúãõâêîôûàèìòùç]{2,})?', trecho)
            resultado["nomes"] += nomes[:3]
        # Links
        links = re.findall(r'https?://[^\s"<>]{10,80}', html)
        resultado["links"] += [l for l in links if any(x in l for x in ["wa.me","zap","whatsapp"])][:3]

    resultado["emails"] = list(dict.fromkeys(resultado["emails"]))[:5]
    resultado["nomes"]  = list(dict.fromkeys(resultado["nomes"]))[:5]
    return resultado
