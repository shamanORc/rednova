#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║          REDNOVA BOT  —  Telegram OSINT + Security      ║
║   CNPJ · Domínio · Telefone · Scan · PDF · Agenda      ║
╚══════════════════════════════════════════════════════════╝
"""

import os, json, re, socket, ssl, subprocess, time, asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, ContextTypes, filters)
from telegram.constants import ParseMode

import osint_cnpj, osint_dominio, osint_telefone, osint_publico, ai_brain

TOKEN    = os.environ.get("8275943576:AAGT_d2px_-VrWUimwkGqilBZ9KTCb5y_zo")
OWNER_ID = int(os.environ.get("1006403873", "0"))  # Seu Telegram ID

# ── Segurança: só você usa ───────────────────────────────────────
async def check_owner(update: Update) -> bool:
    if update.effective_user.id != OWNER_ID:1006403873
        await update.message.reply_text("⛔ Acesso negado.")
        return False
    return True

# ── Menu principal ───────────────────────────────────────────────
MENU_TEXT = """
🔴 *REDNOVA BOT* — Central de Operações

Escolha uma operação:
"""

def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 OSINT",          callback_data="menu_osint")],
        [InlineKeyboardButton("🛡️ Scan de Segurança", callback_data="menu_scan")],
        [InlineKeyboardButton("📋 Contratos / Agenda", callback_data="menu_agenda")],
        [InlineKeyboardButton("📄 Gerar Relatório PDF", callback_data="menu_pdf")],
    ])

def osint_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 OSINT COMPLETO",callback_data="osint_completo")],
        [InlineKeyboardButton("🏢 Só CNPJ",       callback_data="osint_cnpj")],
        [InlineKeyboardButton("🌐 Só Domínio",    callback_data="osint_dominio")],
        [InlineKeyboardButton("📞 Telefone",      callback_data="osint_telefone")],
        [InlineKeyboardButton("◀️ Voltar",        callback_data="menu_main")],
    ])

# ── Handlers ─────────────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    await update.message.reply_text(
        MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_keyboard()
    )

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu_main":
        await q.edit_message_text(MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=menu_keyboard())

    elif data == "menu_osint":
        await q.edit_message_text(
            "🔍 *OSINT* — Escolha o tipo de consulta:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=osint_keyboard()
        )

    elif data == "osint_completo":
        ctx.user_data["aguardando"] = "osint_completo"
        await q.edit_message_text(
            "🔴 *OSINT COMPLETO*\n\n"
            "Envia o CNPJ para cruzar tudo:\n"
            "• Empresa + Sócios\n"
            "• Domínio + DNS + IPs\n"
            "• Emails corporativos\n"
            "• Redes sociais (FB/IG/LI/YT)\n"
            "• Telefones\n"
            "• Vazamentos\n\n"
            "`12345678000199`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "osint_cnpj":
        ctx.user_data["aguardando"] = "cnpj"
        await q.edit_message_text(
            "🏢 *Consulta CNPJ*\n\nEnvia o CNPJ (só números):\n`12345678000199`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "osint_dominio":
        ctx.user_data["aguardando"] = "dominio"
        await q.edit_message_text(
            "🌐 *Consulta Domínio*\n\nEnvia o domínio:\n`paulistinhaot.com`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "osint_telefone":
        ctx.user_data["aguardando"] = "telefone"
        await q.edit_message_text(
            "📞 *Consulta Telefone*\n\nEnvia o número com DDD:\n`11999999999`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "menu_scan":
        ctx.user_data["aguardando"] = "scan"
        await q.edit_message_text(
            "🛡️ *Scan de Segurança*\n\nEnvia o domínio alvo:\n`oleybet.bet.br`",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "menu_agenda":
        await agenda_show(q)

    elif data == "menu_pdf":
        ctx.user_data["aguardando"] = "pdf_alvo"
        await q.edit_message_text(
            "📄 *Gerar Relatório PDF*\n\nEnvia o domínio para gerar o relatório:",
            parse_mode=ParseMode.MARKDOWN
        )

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    aguardando = ctx.user_data.get("aguardando")
    texto = update.message.text.strip()

    # ── Aguardando input de menu ─────────────────────────────────
    if aguardando == "osint_completo":
        ctx.user_data["aguardando"] = None
        await handle_osint_completo(update, ctx, texto)
        return
    elif aguardando == "cnpj":
        ctx.user_data["aguardando"] = None
        await handle_cnpj(update, ctx, texto)
        return
    elif aguardando == "dominio":
        ctx.user_data["aguardando"] = None
        await handle_dominio(update, ctx, texto)
        return
    elif aguardando == "telefone":
        ctx.user_data["aguardando"] = None
        await handle_telefone(update, ctx, texto)
        return
    elif aguardando == "scan":
        ctx.user_data["aguardando"] = None
        await handle_scan(update, ctx, texto)
        return
    elif aguardando == "pdf_alvo":
        ctx.user_data["aguardando"] = None
        await handle_scan(update, ctx, texto)
        return

    # ── Detecção automática de CNPJ ──────────────────────────────
    cnpj_digits = re.sub(r'\D', '', texto)
    if len(cnpj_digits) == 14:
        await handle_osint_completo(update, ctx, cnpj_digits)
        return

    # ── Detecção automática de domínio puro ──────────────────────
    if re.match(r'^[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}$', texto.strip()):
        await handle_dominio(update, ctx, texto.strip())
        return

    # ── Resposta conversacional via Groq AI ──────────────────────
    await update.message.chat.send_action("typing")
    resposta = await asyncio.to_thread(ai_brain.chat, texto)
    try:
        await update.message.reply_text(
            resposta,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
    except Exception:
        # Fallback sem markdown se der erro de parse
        await update.message.reply_text(resposta, disable_web_page_preview=True)

# ── OSINT COMPLETO ────────────────────────────────────────────────
async def handle_osint_completo(update: Update, ctx, entrada: str):
    msg = await update.message.reply_text(
        "🔴 *OSINT COMPLETO iniciado...*\n\n"
        "⏱ Pode demorar 1-2 minutos.\n"
        "Consultando: CNPJ → Domínio → Emails → Redes → Vazamentos...",
        parse_mode=ParseMode.MARKDOWN
    )
    try:
        # Detectar se é CNPJ ou domínio
        entrada_limpa = re.sub(r'\D','', entrada)
        if len(entrada_limpa) == 14:
            resultado = await asyncio.to_thread(
                osint_publico.osint_completo, entrada_limpa, None, None
            )
        elif "." in entrada:
            resultado = await asyncio.to_thread(
                osint_publico.osint_completo, None, entrada.strip(), None
            )
        else:
            resultado = await asyncio.to_thread(
                osint_publico.osint_completo, None, None, entrada.strip()
            )

        await msg.delete()
        # Enviar em chunks se necessário
        for chunk in [resultado[i:i+4000] for i in range(0, len(resultado), 4000)]:
            await update.message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=True
            )
        await update.message.reply_text("✅ OSINT concluído.", reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"❌ Erro: {ex}", reply_markup=menu_keyboard())

# ── OSINT CNPJ ───────────────────────────────────────────────────
async def handle_cnpj(update: Update, ctx, cnpj: str):
    msg = await update.message.reply_text("🔍 Consultando CNPJ...")
    try:
        resultado = await asyncio.to_thread(osint_cnpj.consultar, cnpj)
        await msg.edit_text(resultado, parse_mode=ParseMode.MARKDOWN,
                            reply_markup=menu_keyboard())
    except Exception as e:
        await msg.edit_text(f"❌ Erro: {e}", reply_markup=menu_keyboard())

# ── OSINT Domínio ─────────────────────────────────────────────────
async def handle_dominio(update: Update, ctx, dominio: str):
    msg = await update.message.reply_text("🌐 Consultando domínio... (30-60s)")
    try:
        resultado = await asyncio.to_thread(osint_dominio.consultar, dominio)
        # Telegram tem limite de 4096 chars
        for chunk in [resultado[i:i+4000] for i in range(0,len(resultado),4000)]:
            await update.message.reply_text(
                chunk, parse_mode=ParseMode.MARKDOWN
            )
        await msg.delete()
        await update.message.reply_text("✅ Consulta concluída.",
                                         reply_markup=menu_keyboard())
    except Exception as e:
        await msg.edit_text(f"❌ Erro: {e}", reply_markup=menu_keyboard())

# ── OSINT Telefone ────────────────────────────────────────────────
async def handle_telefone(update: Update, ctx, telefone: str):
    msg = await update.message.reply_text("📞 Consultando telefone...")
    try:
        resultado = await asyncio.to_thread(osint_telefone.consultar, telefone)
        await msg.edit_text(resultado, parse_mode=ParseMode.MARKDOWN,
                            reply_markup=menu_keyboard())
    except Exception as e:
        await msg.edit_text(f"❌ Erro: {e}", reply_markup=menu_keyboard())

# ── Scan ──────────────────────────────────────────────────────────
async def handle_scan(update: Update, ctx, dominio: str):
    msg = await update.message.reply_text(
        f"🛡️ Iniciando scan em `{dominio}`...\n⏱ Aguarde 3-5 minutos.",
        parse_mode=ParseMode.MARKDOWN
    )
    try:
        def rodar_scan():
            result = subprocess.run(
                ["python3", "rednova_v3.py", "-t", dominio,
                 "--skip-pdf", "-o", f"/tmp/scan_{dominio}.json"],
                capture_output=True, text=True, timeout=300
            )
            return result.stdout, result.returncode

        stdout, code = await asyncio.to_thread(rodar_scan)

        # Extrair resumo do output
        linhas = [l for l in stdout.splitlines() if
                  any(k in l for k in ["[+]","[!]","[VULN]","RESUMO","Subdomain",
                                        "Porta","Vulnerab","Endpoint"])]
        resumo = "\n".join(linhas[-30:])

        await msg.edit_text(
            f"✅ *Scan concluído — {dominio}*\n\n```\n{resumo[:3000]}\n```",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📄 Gerar PDF do scan", callback_data=f"pdf_{dominio}")],
                [InlineKeyboardButton("◀️ Menu", callback_data="menu_main")],
            ])
        )
    except Exception as e:
        await msg.edit_text(f"❌ Erro no scan: {e}", reply_markup=menu_keyboard())

# ── Agenda ────────────────────────────────────────────────────────
AGENDA_FILE = "agenda.json"

def load_agenda():
    if os.path.exists(AGENDA_FILE):
        with open(AGENDA_FILE) as f:
            return json.load(f)
    return {"contratos": []}

def save_agenda(data):
    with open(AGENDA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def agenda_show(q):
    data = load_agenda()
    contratos = data.get("contratos", [])
    if not contratos:
        texto = "📋 *Agenda vazia*\n\nNenhum contrato cadastrado."
    else:
        texto = "📋 *Contratos ativos:*\n\n"
        for i, c in enumerate(contratos, 1):
            status = "✅" if c.get("concluido") else "⏳"
            texto += f"{status} *{i}. {c['cliente']}*\n"
            texto += f"   📌 {c.get('alvo','?')}\n"
            texto += f"   📅 Prazo: {c.get('prazo','?')}\n"
            texto += f"   💰 Valor: {c.get('valor','?')}\n\n"

    await q.edit_message_text(
        texto, parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Novo contrato", callback_data="agenda_novo")],
            [InlineKeyboardButton("◀️ Menu", callback_data="menu_main")],
        ])
    )

# ── Comandos diretos ──────────────────────────────────────────────
async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    await update.message.reply_text(
        MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
        reply_markup=menu_keyboard()
    )

async def cmd_cnpj(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: `/cnpj 12345678000199`",
                                         parse_mode=ParseMode.MARKDOWN)
        return
    await handle_cnpj(update, ctx, ctx.args[0])

async def cmd_dominio(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: `/dominio site.com`",
                                         parse_mode=ParseMode.MARKDOWN)
        return
    await handle_dominio(update, ctx, ctx.args[0])

async def cmd_limpar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    msg = ai_brain.limpar_historico()
    await update.message.reply_text(msg)

async def cmd_osint(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text(
            "Uso:\n`/osint 12345678000199` — por CNPJ\n`/osint site.com` — por domínio",
            parse_mode=ParseMode.MARKDOWN)
        return
    await handle_osint_completo(update, ctx, " ".join(ctx.args))

async def cmd_scan(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: `/scan site.com`",
                                         parse_mode=ParseMode.MARKDOWN)
        return
    await handle_scan(update, ctx, ctx.args[0])

# ── Main ──────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",   start))
    app.add_handler(CommandHandler("menu",    cmd_menu))
    app.add_handler(CommandHandler("cnpj",    cmd_cnpj))
    app.add_handler(CommandHandler("dominio", cmd_dominio))
    app.add_handler(CommandHandler("limpar",  cmd_limpar))
    app.add_handler(CommandHandler("osint",   cmd_osint))
    app.add_handler(CommandHandler("scan",    cmd_scan))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    print("🔴 RedNova Bot iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
