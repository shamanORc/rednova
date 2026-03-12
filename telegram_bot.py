#!/usr/bin/env python3
"""REDNOVA Telegram Bot — investigação completa via chat."""
import os, sys, json, re, asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, ContextTypes, filters)
from telegram.constants import ParseMode
from settings import BOT_TOKEN, OWNER_ID, GROQ_API_KEY, GROQ_URL, GROQ_MODEL
from investigate import investigate, detect_type
from pdf_generator import gerar as gerar_pdf
import urllib.request, urllib.error

# ── AI BRAIN ─────────────────────────────────────────────────────────────
_historico = []

SYSTEM_PROMPT = """Você é o REDNOVA — IA de segurança ofensiva e OSINT, parceiro do Rael.

PERSONALIDADE:
- Fala como um hacker experiente, direto, sem frescura
- Nunca diz "não posso ajudar" — sempre dá o caminho
- Trata o Rael como parceiro de operação, não como usuário
- Usa gírias de infosec naturalmente: "recon", "footprint", "enum", "pivot"
- Quando não sabe algo, admite e sugere onde buscar

EXPERTISE:
- Red team, pentest, bug bounty, OSINT, engenharia social
- Burp Suite, Nmap, Nuclei, SQLmap, ffuf, subfinder, Metasploit, Maltego
- WordPress, PHP, APIs REST, JWT, OAuth, OAuth2, SAML
- SQLi, XSS, IDOR, CSRF, SSRF, RCE, LFI, XXE, race conditions
- Recon passivo e ativo, fingerprinting, enum de subdomínios
- CVSS scoring, relatórios de pentest, disclosure responsável

CONTEXTO DO RAEL:
- Tem contrato ativo de red team/bug bounty no oleybet.com (100k escopo)
- Mais 10+ contratos na fila
- Usa Kali Linux como base
- Precisa de agilidade — prioriza o que tem mais chance de bounty

COMO RESPONDER:
- Direto ao ponto, sem enrolação
- Para findings: impacto real → CVSS → PoC/próximo passo → remediação
- Para recon: sequência lógica de passos, do passivo ao ativo
- Para perguntas técnicas: resposta completa com exemplos
- Use `código` para comandos, payloads e endpoints
- Markdown Telegram: *negrito*, _itálico_, `código`
- Máximo 3500 caracteres por mensagem

QUANDO RECEBER DADOS DE INVESTIGAÇÃO:
- Analisa automaticamente o que foi encontrado
- Aponta os 3 vetores mais promissores para exploração
- Sugere próximos passos específicos baseados nos dados
- Correlaciona informações (ex: email + breach + LinkedIn = engenharia social)"""

def ai_chat(mensagem, contexto=""):
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY não configurada no Railway."
    _historico.append({"role":"user","content":mensagem})
    if len(_historico) > 20: _historico[:] = _historico[-20:]
    msgs = [{"role":"system","content":SYSTEM_PROMPT}]
    if contexto:
        msgs.append({"role":"system","content":f"Contexto:\n{contexto[:2000]}"})
    msgs.extend(_historico)
    try:
        import httpx, json as _json
        payload = {"model":GROQ_MODEL,"messages":msgs,"max_tokens":800,"temperature":0.7}
        resp = httpx.post(
            GROQ_URL,
            json=payload,
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=30
        )
        data = resp.json()
        if resp.status_code != 200:
            return f"⚠️ Groq erro {resp.status_code}: {data.get('error',{}).get('message','?')[:100]}"
        texto = data["choices"][0]["message"]["content"]
        _historico.append({"role":"assistant","content":texto})
        return texto
    except Exception as e:
        return f"⚠️ Erro IA: {str(e)[:150]}"

# ── FORMATAÇÃO DO RESULTADO ───────────────────────────────────────────────
def formatar_resultado(results: dict) -> list:
    """Retorna lista de mensagens (máx 4000 chars cada)."""
    perfil = results.get("perfil",{})
    target = results.get("target","?")
    tipo   = results.get("tipo","?")
    msgs   = []

    out = [f"🔴 *REDNOVA — INVESTIGAÇÃO COMPLETA*",
           f"🎯 *Alvo:* `{target}` | *Tipo:* {tipo.upper()}",
           f"⚠️ *Risk Score:* {perfil.get('risk_score',0)}/100\n"]

    # Identidades
    ids = perfil.get("identidades",[])
    if ids:
        out.append("━━━━ 👤 IDENTIDADES ━━━━")
        for n in ids: out.append(f"  • {n}")

    # CNPJ
    cnpj = results.get("cnpj",{})
    if cnpj:
        out.append("\n━━━━ 🏢 EMPRESA ━━━━")
        sit = cnpj.get("situacao","?")
        sit_i = {"ATIVA":"✅","BAIXADA":"🔴","SUSPENSA":"⚠️","INAPTA":"❌"}.get(sit.upper(),"⚠️")
        out.append(f"*CNPJ:* `{cnpj.get('cnpj','')}`")
        out.append(f"*Razão Social:* {cnpj.get('razao_social','?')}")
        if cnpj.get("nome_fantasia"): out.append(f"*Fantasia:* {cnpj['nome_fantasia']}")
        out.append(f"*Situação:* {sit_i} {sit}")
        if cnpj.get("data_situacao"): out.append(f"*Data:* {cnpj['data_situacao']}")
        if cnpj.get("motivo_situacao") and cnpj["motivo_situacao"] not in ("","*","None"):
            out.append(f"*Motivo:* {cnpj['motivo_situacao']}")
        out.append(f"*Abertura:* {cnpj.get('abertura','?')}")
        em = cnpj.get("email","")
        te = cnpj.get("telefone","")
        out.append(f"📧 *Email:* `{em}`" if em and em not in ("","none") else "📧 *Email:* —")
        out.append(f"📞 *Tel:* `{te}`" if te and te not in ("","none") else "📞 *Tel:* —")
        qsa = cnpj.get("qsa",[]) or []
        if qsa:
            out.append("*Sócios:*")
            for s in qsa[:3]:
                n = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","?")).strip()
                out.append(f"  • {n}")

    # Domínio
    dom = results.get("dominio",{})
    if dom and dom.get("dominio"):
        out.append(f"\n━━━━ 🌐 DOMÍNIO: `{dom['dominio']}` ━━━━")
        if dom.get("dono"): out.append(f"*Registrante:* {dom['dono']}")
        if dom.get("criado"): out.append(f"*Criado:* {dom['criado']} | *Expira:* {dom.get('expira','?')}")
        ips = list(dom.get("ips",{}).values())
        if ips: out.append(f"*IPs:* {' | '.join('`'+i+'`' for i in ips[:3])}")
        subs = dom.get("subdominios",[])
        if subs:
            out.append(f"*Subdomínios ({len(subs)}):* " + " | ".join(f"`{s}`" for s in subs[:5]))

    # Emails
    emails = perfil.get("emails",[])
    if emails:
        out.append(f"\n━━━━ 📧 EMAILS ({len(emails)}) ━━━━")
        for e in emails[:8]: out.append(f"  `{e}`")

    # Redes
    redes = perfil.get("redes",{})
    icons = {"instagram":"📸","facebook":"🔵","linkedin":"💼","twitter":"🐦",
             "youtube":"▶️","github":"🐙","tiktok":"🎵","telegram":"✈️",
             "whatsapp":"💬","jusbrasil":"⚖️","escavador":"🔎","linkedin_co":"💼"}
    if redes:
        out.append(f"\n━━━━ 📱 REDES SOCIAIS ━━━━")
        for rede, url in redes.items():
            if isinstance(url, list): continue
            sc = perfil.get("confianca",{}).get(rede, 60)
            out.append(f"{icons.get(rede,'•')} [{rede.capitalize()}]({url}) _{sc}%_")

    # Dono redes
    dono_redes = results.get("dono_redes",{})
    if dono_redes:
        out.append(f"\n━━━━ 👤 DONO DO DOMÍNIO ━━━━")
        for rede, url in dono_redes.items():
            if isinstance(url, list):
                for e in url[:2]: out.append(f"  📧 `{e}`")
            else:
                out.append(f"  {icons.get(rede,'•')} [{rede.capitalize()}]({url})")

    # Sócios redes
    socios_r = results.get("socios_redes",[])
    if socios_r:
        out.append(f"\n━━━━ 👥 SÓCIOS NAS REDES ━━━━")
        for sr in socios_r[:3]:
            out.append(f"*{sr['nome']}:*")
            for rede, url in sr.get("redes",{}).items():
                if isinstance(url, list): continue
                out.append(f"  {icons.get(rede,'•')} [{rede.capitalize()}]({url})")

    # Vazamentos
    vaz = perfil.get("vazamentos",[])
    out.append(f"\n━━━━ ⚠️ VAZAMENTOS ({len(vaz)}) ━━━━")
    if vaz:
        for v in vaz[:3]:
            contas = f"{v.get('contas',0):,}".replace(",",".")
            out.append(f"🔴 *{v.get('nome','?')}* ({v.get('data','?')}) — {contas} contas")
            out.append(f"   _{str(v.get('tipos') or v.get('dados',''))[:60]}_")
    else:
        out.append("  ✅ Nenhum vazamento encontrado")

    # Timeline
    timeline = perfil.get("timeline",[])
    if timeline:
        out.append(f"\n━━━━ 📅 TIMELINE ━━━━")
        for ev in timeline[-5:]:
            out.append(f"  `{ev.get('data','?')}` — {ev.get('evento','?')}")

    out.append("\n━━━━━━━━━━━━━━━━━━━━")
    out.append("🔴 _REDNOVA Intelligence · Uso confidencial_")

    texto = "\n".join(out)
    # Quebrar em chunks de 4000
    chunks = [texto[i:i+4000] for i in range(0, len(texto), 4000)]
    return chunks

# ── BOT HANDLERS ─────────────────────────────────────────────────────────
def menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Investigar", callback_data="investigate")],
        [InlineKeyboardButton("👤 Username", callback_data="username"),
         InlineKeyboardButton("📞 Telefone", callback_data="phone")],
        [InlineKeyboardButton("📧 Email", callback_data="email"),
         InlineKeyboardButton("🌐 Domínio", callback_data="domain")],
        [InlineKeyboardButton("🏢 CNPJ", callback_data="cnpj"),
         InlineKeyboardButton("📄 Relatório PDF", callback_data="pdf")],
        [InlineKeyboardButton("🧠 Analisar com IA", callback_data="ai_analyze")],
    ])

async def check_owner(update):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ Acesso negado.")
        return False
    return True

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    await update.message.reply_text(
        "🔴 *REDNOVA* — Plataforma de Inteligência OSINT\n\n"
        "Investiga: CNPJ · Domínio · Email · Username · Telefone · Nome\n\n"
        "Digite direto ou escolha:",
        parse_mode=ParseMode.MARKDOWN, reply_markup=menu_kb())

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    prompts = {
        "investigate": "🔍 *Investigar*\n\nEnvia qualquer alvo:\n`CNPJ · domínio · email · username · telefone · nome`",
        "username":    "👤 *Username*\n\nEnvia o username:",
        "phone":       "📞 *Telefone*\n\nEnvia com DDD: `11999999999`",
        "email":       "📧 *Email*\n\nEnvia o email:",
        "domain":      "🌐 *Domínio*\n\nEnvia o domínio: `site.com`",
        "cnpj":        "🏢 *CNPJ*\n\nEnvia o CNPJ (14 dígitos):",
        "pdf":         "📄 *Relatório PDF*\n\nEnvia o alvo para gerar o PDF:",
        "ai_analyze":  "🧠 *Análise IA*\n\nEnvia o alvo ou uma pergunta:",
    }
    if q.data in prompts:
        ctx.user_data["modo"] = q.data
        await q.edit_message_text(prompts[q.data], parse_mode=ParseMode.MARKDOWN)
    elif q.data == "menu":
        await q.edit_message_text("🔴 *REDNOVA*", parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=menu_kb())

async def run_investigation(update, ctx, target, modo="investigate"):
    log_msgs = []
    async def progress(msg):
        log_msgs.append(msg)
        try: await status_msg.edit_text("\n".join(log_msgs[-5:]))
        except: pass

    status_msg = await update.message.reply_text("🔴 Iniciando investigação...")

    try:
        def sync_investigate():
            return investigate(target, progress_cb=lambda m: asyncio.get_event_loop().call_soon_threadsafe(
                lambda: asyncio.ensure_future(progress(m))))

        results = await asyncio.to_thread(investigate, target)
        await status_msg.delete()

        if modo == "pdf":
            pdf_path = await asyncio.to_thread(gerar_pdf, results)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    await update.message.reply_document(
                        document=f, filename=f"REDNOVA_{target}.pdf",
                        caption=f"📄 Relatório: `{target}`",
                        parse_mode=ParseMode.MARKDOWN)
                os.remove(pdf_path)
            else:
                await update.message.reply_text("❌ Erro ao gerar PDF. Verifica se reportlab está instalado.")
        else:
            chunks = formatar_resultado(results)
            for chunk in chunks:
                await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN,
                                                 disable_web_page_preview=True)

            # Botões pós-investigação
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Gerar PDF", callback_data=f"pdf__{target}"),
                 InlineKeyboardButton("🧠 Analisar IA", callback_data=f"ai__{target}")],
                [InlineKeyboardButton("◀️ Menu", callback_data="menu")],
            ])
            await update.message.reply_text("✅ *Investigação concluída.*", 
                                             parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
            # Salva resultado no contexto
            ctx.user_data["last_results"] = results

    except Exception as ex:
        await status_msg.edit_text(f"❌ Erro: {ex}", reply_markup=menu_kb())

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    texto = update.message.text.strip()
    modo  = ctx.user_data.get("modo", "investigate")
    ctx.user_data["modo"] = None

    # Auto-detectar sem modo
    tipo = detect_type(texto)

    # Tipos que são claramente alvos de investigação
    TIPOS_ALVO = {"cnpj","cpf","email","domain","phone"}

    # Palavras/padrões que indicam conversa
    PALAVRAS_CONVERSA = [
        "como","qual","quais","quando","onde","porque","pq","oque","o que",
        "analisa","explica","me diz","faz","fazer","proximo","passo",
        "ajuda","help","bom dia","boa tarde","boa noite","oi","ola","hey",
        "tudo","beleza","valeu","obrigado","blz","tmj","e ai","eai","opa",
        "pentest","vuln","exploit","payload","burp","nmap","nuclei",
        "finding","report","relatorio","contrato","agenda","scan","teste",
        "sql","xss","idor","csrf","jwt","token","bypass","rce","lfi",
        "recon","enum","fuzzing","brute","injection","shell","reverse",
    ]

    eh_conversa = (
        modo == "ai_analyze" or
        tipo not in TIPOS_ALVO and (
            tipo == "unknown" or
            len(texto) <= 20 or
            len(texto.split()) >= 3 or
            texto.endswith("?") or
            any(p in texto.lower() for p in PALAVRAS_CONVERSA)
        )
    )

    if eh_conversa:
        await update.message.chat.send_action("typing")
        last = ctx.user_data.get("last_results", {})
        contexto = f"Ultimo alvo: {last.get('target','')}" if last else ""
        resposta = await asyncio.to_thread(ai_chat, texto, contexto)
        try:
            await update.message.reply_text(resposta, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.message.reply_text(resposta)
        return

    await run_investigation(update, ctx, texto, modo or "investigate")

async def inline_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data.startswith("pdf__"):
        target = data[5:]
        last = ctx.user_data.get("last_results")
        if last and last.get("target") == target:
            msg = await update.effective_message.reply_text("📄 Gerando PDF...")
            pdf_path = await asyncio.to_thread(gerar_pdf, last)
            if pdf_path and os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    await update.effective_message.reply_document(
                        document=f, filename=f"REDNOVA_{target}.pdf")
                os.remove(pdf_path)
                await msg.delete()
            else:
                await msg.edit_text("❌ Erro ao gerar PDF.")
        else:
            ctx.user_data["modo"] = "pdf"
            await q.edit_message_text(f"📄 Re-investigando `{target}` para gerar PDF...",
                                       parse_mode=ParseMode.MARKDOWN)
            fake_update = update
            class FakeMsg:
                text = target
                async def reply_text(self, *a, **kw): return await update.effective_message.reply_text(*a,**kw)
                async def reply_document(self, *a, **kw): return await update.effective_message.reply_document(*a,**kw)
                @property
                def chat(self): return update.effective_message.chat
            fake_update.message = FakeMsg()
            await run_investigation(fake_update, ctx, target, "pdf")

    elif data.startswith("ai__"):
        target = data[4:]
        last = ctx.user_data.get("last_results",{})
        ctx_str = f"Investigação de {target} concluída. Analisa os dados e dá os próximos passos mais valiosos para bug bounty."
        await update.effective_message.chat.send_action("typing")
        resp = await asyncio.to_thread(ai_chat, ctx_str, str(last.get("perfil",{}))[:2000])
        try:
            await update.effective_message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)
        except:
            await update.effective_message.reply_text(resp)

    elif data == "menu":
        await q.edit_message_text("🔴 *REDNOVA*", parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=menu_kb())
    else:
        await button(update, ctx)

async def cmd_investigate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /investigate <alvo>"); return
    await run_investigation(update, ctx, " ".join(ctx.args))

async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /report <alvo>"); return
    await run_investigation(update, ctx, " ".join(ctx.args), "pdf")

async def cmd_limpar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    global _historico
    _historico = []
    ctx.user_data.clear()
    await update.message.reply_text("🗑️ Histórico e contexto limpos.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("investigate", cmd_investigate))
    app.add_handler(CommandHandler("report",      cmd_report))
    app.add_handler(CommandHandler("limpar",      cmd_limpar))
    app.add_handler(CallbackQueryHandler(inline_button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("🔴 REDNOVA Bot iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
