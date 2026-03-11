# 🔴 REDNOVA BOT — Passo a Passo Completo

## O QUE VOCÊ VAI PRECISAR
- Conta no Telegram
- Conta no GitHub (github.com)
- Conta no Render.com (grátis)
- Key da xAI (você já tem)

---

## PASSO 1 — Criar o Bot no Telegram (2 min)

1. Abre o Telegram
2. Busca: @BotFather
3. Manda: /newbot
4. Nome do bot: RedNova
5. Username: RedNovaOpsBot (ou qualquer nome terminando em Bot)
6. O BotFather vai te mandar um TOKEN — guarda esse token

Exemplo de token:
7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

---

## PASSO 2 — Pegar seu ID do Telegram (1 min)

1. No Telegram busca: @userinfobot
2. Manda qualquer mensagem (ex: "oi")
3. Ele responde com seu Id: 123456789
4. Guarda esse número

---

## PASSO 3 — Subir no GitHub (3 min)

1. Acessa github.com e faz login
2. Clica em "New repository"
3. Nome: rednova-bot
4. Marca: Private
5. Clica "Create repository"
6. Clica em "uploading an existing file"
7. Arrasta TODOS os arquivos da pasta rednova_bot/ para lá
8. Clica "Commit changes"

---

## PASSO 4 — Deploy no Render.com (5 min)

1. Acessa render.com
2. Cria conta com GitHub
3. Clica "New +" → "Web Service"
4. Conecta seu repositório rednova-bot
5. Configura:
   - Name: rednova-bot
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python bot.py
   - Instance Type: Free

6. Clica em "Advanced" → "Add Environment Variable"
   Adiciona as 3 variáveis:

   BOT_TOKEN   = token do BotFather
   OWNER_ID    = seu ID do Telegram (só números)
   GROK_API_KEY = sua key da xAI

7. Clica "Create Web Service"
8. Aguarda o deploy (2-3 minutos)

---

## PASSO 5 — Testar

1. Abre o Telegram
2. Busca o username do seu bot (ex: @RedNovaOpsBot)
3. Manda /start
4. Deve aparecer o menu do RedNova

---

## COMANDOS DISPONÍVEIS

/start ou /menu     — Menu principal
/osint 12345678000199  — OSINT completo por CNPJ
/osint site.com     — OSINT completo por domínio
/cnpj 12345678000199   — Só dados da empresa
/dominio site.com   — Só OSINT do domínio
/telefone 11999999999  — Consulta telefone
/scan site.com      — Scan de segurança
/limpar             — Limpa memória da conversa

Qualquer outra mensagem → resposta da IA (xAI Grok)

---

## SE TRAVAR

Render dá erro de build:
→ Verifica se o requirements.txt está no repositório

Bot não responde:
→ Verifica as 3 variáveis de ambiente no Render
→ Confere se o BOT_TOKEN está correto

IA não responde:
→ Verifica GROK_API_KEY no Render
→ Gera uma nova key em console.x.ai
