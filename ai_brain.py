"""REDNOVA AI BRAIN — Groq (gratuito)"""
import os, json, urllib.request, urllib.error

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL     = "https://api.groq.com/openai/v1/chat/completions"
MODEL        = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Você é o REDNOVA — assistente pessoal de segurança ofensiva e OSINT do Rael.

- Especialista em red team, pentest, bug bounty e OSINT
- Ferramentas: Burp Suite, Nmap, Nuclei, SQLmap, ffuf, subfinder
- Fala português brasileiro, direto e técnico
- É parceiro do Rael, não um robô formal

CONTEXTO:
- Rael tem contratos de red team/bug bounty ativos
- Usa Kali Linux, tem 10+ contratos na fila
- Gera relatórios PDF profissionais

COMO RESPONDER:
- Direto ao ponto, sem enrolação
- Use codigo para comandos
- Análise de finding: impacto, CVSS, como explorar, como remediar
- Próximos passos: priorizado por chance de bounty
- Máximo 3000 caracteres

COMANDOS DO BOT:
/osint <cnpj ou domínio> — OSINT completo
/cnpj, /dominio, /telefone, /scan, /agenda, /contrato, /limpar, /menu"""

_historico = []
MAX_HISTORICO = 20

def chat(mensagem, contexto_extra=None):
    global _historico

    if not GROQ_API_KEY:
        return ("⚠️ GROQ_API_KEY não configurada.\n\n"
                "1. Acessa console.groq.com\n"
                "2. Cria key gratuita\n"
                "3. Adiciona GROQ_API_KEY no Railway → Variables")

    _historico.append({"role": "user", "content": mensagem})
    if len(_historico) > MAX_HISTORICO:
        _historico = _historico[-MAX_HISTORICO:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if contexto_extra:
        messages.append({"role": "system", "content": f"Contexto: {contexto_extra}"})
    messages.extend(_historico)

    payload = json.dumps({
        "model": MODEL,
        "messages": messages,
        "max_tokens": 800,
        "temperature": 0.7,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(
            GROQ_URL, data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
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
            return "API key inválida. Verifica GROQ_API_KEY no Railway."
        elif e.code == 429:
            return "Limite atingido. Aguarda 1 minuto."
        return f"Erro Groq ({e.code}): {body[:200]}"
    except Exception as ex:
        return f"Erro: {str(ex)[:200]}"

def limpar_historico():
    global _historico
    _historico = []
    return "Histórico limpo."

def chat_com_findings(findings, pergunta=None):
    pergunta = pergunta or "Analisa esses findings. Prioriza por bounty. Para cada crítico: impacto, CVSS, próximo passo."
    return chat(pergunta, findings[:2000])
