"""
OSINT Telefone — DDD, operadora, tipo, região
Dados públicos ANATEL + tabelas brasileiras
"""
import re

# Tabela DDD → Estado/Cidade (ANATEL)
DDD_ESTADOS = {
    "11":"SP - São Paulo","12":"SP - Vale do Paraíba","13":"SP - Baixada Santista",
    "14":"SP - Bauru","15":"SP - Sorocaba","16":"SP - Ribeirão Preto",
    "17":"SP - São José do Rio Preto","18":"SP - Presidente Prudente","19":"SP - Campinas",
    "21":"RJ - Rio de Janeiro","22":"RJ - Interior","24":"RJ/MG - Volta Redonda",
    "27":"ES - Vitória","28":"ES - Interior",
    "31":"MG - Belo Horizonte","32":"MG - Juiz de Fora","33":"MG - Governador Valadares",
    "34":"MG - Uberlândia","35":"MG - Poços de Caldas","37":"MG - Divinópolis",
    "38":"MG - Montes Claros",
    "41":"PR - Curitiba","42":"PR - Ponta Grossa","43":"PR - Londrina",
    "44":"PR - Maringá","45":"PR - Cascavel","46":"PR - Francisco Beltrão",
    "47":"SC - Joinville","48":"SC - Florianópolis","49":"SC - Chapecó",
    "51":"RS - Porto Alegre","53":"RS - Pelotas","54":"RS - Caxias do Sul","55":"RS - Santa Maria",
    "61":"DF - Brasília","62":"GO - Goiânia","63":"TO - Palmas","64":"GO - Rio Verde",
    "65":"MT - Cuiabá","66":"MT - Rondonópolis","67":"MS - Campo Grande","68":"AC - Rio Branco",
    "69":"RO - Porto Velho",
    "71":"BA - Salvador","73":"BA - Ilhéus","74":"BA - Juazeiro","75":"BA - Feira de Santana",
    "77":"BA - Vitória da Conquista","79":"SE - Aracaju",
    "81":"PE - Recife","82":"AL - Maceió","83":"PB - João Pessoa","84":"RN - Natal",
    "85":"CE - Fortaleza","86":"PI - Teresina","87":"PE - Caruaru","88":"CE - Juazeiro do Norte",
    "89":"PI - Picos",
    "91":"PA - Belém","92":"AM - Manaus","93":"PA - Santarém","94":"PA - Marabá",
    "95":"RR - Boa Vista","96":"AP - Macapá","97":"AM - Interior","98":"MA - São Luís","99":"MA - Interior",
}

# Prefixos de operadora (primeiros dígitos após DDD)
OPERADORAS_MOVEL = {
    ("9","6"):  "Claro",
    ("9","7"):  "TIM",
    ("9","8"):  "Vivo",
    ("9","9"):  "Vivo",
    ("9","4"):  "TIM",
    ("9","5"):  "Claro",
    ("9","3"):  "Oi",
    ("9","2"):  "Nextel/Claro",
}

def consultar(telefone_raw: str) -> str:
    # Limpar
    tel = re.sub(r'\D', '', telefone_raw)

    # Remover +55 se vier
    if tel.startswith("55") and len(tel) > 11:
        tel = tel[2:]

    if len(tel) < 10 or len(tel) > 11:
        return "❌ Número inválido. Envie com DDD: `11999999999`"

    ddd    = tel[:2]
    numero = tel[2:]
    tipo   = _tipo(numero)
    estado = DDD_ESTADOS.get(ddd, "DDD não identificado")
    op     = _operadora(numero)
    formatted = _formatar_numero(ddd, numero)

    resultado = f"""📞 *CONSULTA TELEFONE — REDNOVA OSINT*

📱 *Número:* `{formatted}`
🗺️ *DDD {ddd}:* {estado}
📶 *Tipo:* {tipo}
📡 *Operadora (estimada):* {op}
🔢 *Dígitos:* {len(numero)}

ℹ️ _Dados baseados em tabelas ANATEL públicas._
_Para rastreamento avançado, use com CNPJ cruzado._

🔴 _RedNova OSINT — {__import__('datetime').datetime.now().strftime('%d/%m/%Y %H:%M')}_"""

    return resultado

def _tipo(numero: str) -> str:
    if len(numero) == 9 and numero[0] == "9":
        return "📱 Celular (9 dígitos)"
    elif len(numero) == 8:
        return "☎️ Fixo (8 dígitos)"
    elif numero.startswith("0800"):
        return "📞 0800 (gratuito)"
    elif numero.startswith("0300") or numero.startswith("0500"):
        return "📞 Serviço especial"
    return "❓ Indeterminado"

def _operadora(numero: str) -> str:
    if len(numero) == 9:
        # Celular — tentar identificar pelo 2º dígito
        segundo = numero[1] if len(numero) > 1 else ""
        mapa = {
            "6": "Claro",
            "7": "TIM",
            "8": "Vivo / TIM",
            "9": "Vivo",
            "4": "TIM / Claro",
            "5": "Claro / TIM",
            "3": "Oi",
            "2": "Claro",
            "1": "Vivo",
        }
        return mapa.get(segundo, "Não identificada")
    return "Fixo — consultar operadora local"

def _formatar_numero(ddd: str, numero: str) -> str:
    if len(numero) == 9:
        return f"({ddd}) {numero[:5]}-{numero[5:]}"
    elif len(numero) == 8:
        return f"({ddd}) {numero[:4]}-{numero[4:]}"
    return f"({ddd}) {numero}"
