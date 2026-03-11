"""
REDNOVA AI BRAIN — xAI Grok Integration
O cérebro conversacional do bot.
"""

import os, json, urllib.request, urllib.error

GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
GROK_URL     = "https://api.x.ai/v1/chat/completions"
MODEL        = "grok-3-mini"

SYSTEM_PROMPT = """Você é o REDNOVA — assistente pessoal de segurança ofensiva e OSINT do Rael.

SOBRE VOCÊ:
- Especialista em red team, pentest, bug bounty e OSINT
- Conhece as ferramentas: Burp Suite, Nmap, Nuclei, Metasploit, SQLmap, ffuf, subfinder
- Entende de WordPress, PHP, APIs REST, JWT, OAuth, race conditions, SQLi, XSS, IDOR
- Fala português brasileiro, de forma direta e técnica
- É parceiro do Rael, não um robô formal

CONTEXTO DO RAEL:
- Tem contrato de red team/bug bounty ativo (oleybet.com e outros)
- Usa Kali Linux
- Tem 10+ contratos na fila — precisa de agilidade
- Gera relatórios PDF profissionais de segurança

COMO RESPONDER:
- Direto ao ponto, sem enrolação
- Use codigo para comandos e payloads
- Se pedir análise de finding: impacto, CVSS estimado, como explorar, como remediar
- Se pedir próximos passos: lista priorizada pelo que tem mais chance de bounty
- Markdown Telegram: *negrito*, _itálico_, codigo
- Máximo 3000 caracteres por resposta

COMANDOS DO BOT:
/osint <cnpj ou domínio> - OSINT completo cruzado
/cnpj <número> - consulta CNPJ
/dominio <site> - OSINT de domínio
/telefone <número> - consulta telefone
/scan <domínio> - scan de segurança
/limpar - limpa histórico
/menu - menu principal"""

_historico = []
MAX_HISTORICO = 20

def chat(mensagem, contexto_extra=None):
    global _historico

    if not GROK_API_KEY:
        return "GROK_API_KEY nao configurada. Adiciona no Render.com como variavel de ambiente."

    _historico.append({"role": "user", "content": mensagem})
    if len(_historico) > MAX_HISTORICO:
        _historico = _historico[-MAX_HISTORICO:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if contexto_extra:
        messages.append({"role": "system", "content": f"Contexto: {contexto_extra}"})
    messages.extend(_historico)

    payload = json.dumps({
        "model":       MODEL,
        "messages":    messages,
        "max_tokens":  800,
        "temperature": 0.7,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            GROK_URL,
            data=payload,
            headers={
                "Content-Type":  "application/json",
                "Authorization": f"Bearer {GROK_API_KEY}",
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())

        resposta = data["choices"][0]["message"]["content"]
        _historico.append({"role": "assistant", "content": resposta})
        return resposta

    except urllib.error.HTTPError as e:
        body = e.read().decode()
        if e.code == 401:
            return "API key invalida. Verifica GROK_API_KEY no Render."
        elif e.code == 429:
            return "Limite atingido. Aguarda 1 minuto."
        return f"Erro xAI ({e.code}): {body[:200]}"
    except Exception as ex:
        return f"Erro: {str(ex)[:200]}"

def limpar_historico():
    global _historico
    _historico = []
    return "Historico limpo."

def chat_com_findings(findings, pergunta=None):
    pergunta = pergunta or "Analisa esses findings. Prioriza pelo bounty. Para cada critico: impacto, CVSS, proximo passo."
    return chat(pergunta, findings[:2000])
