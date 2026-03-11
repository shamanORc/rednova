#!/usr/bin/env python3
import os, json, re, subprocess, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, MessageHandler,
                           CallbackQueryHandler, ContextTypes, filters)
from telegram.constants import ParseMode
import osint_cnpj, osint_dominio, osint_telefone, osint_publico, ai_brain, agenda, gerar_pdf

TOKEN    = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

async def check_owner(update: Update) -> bool:
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("Acesso negado.")
        return False
    return True

MENU_TEXT = "🔴 *REDNOVA BOT*\n\nEscolha uma operação:"

def menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 OSINT", callback_data="menu_osint")],
        [InlineKeyboardButton("🛡️ Scan de Segurança", callback_data="menu_scan")],
        [InlineKeyboardButton("📋 Contratos / Agenda", callback_data="menu_agenda")],
        [InlineKeyboardButton("📄 Gerar PDF do último OSINT", callback_data="menu_pdf")],
    ])

def osint_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 OSINT COMPLETO", callback_data="osint_completo")],
        [InlineKeyboardButton("🏢 Só CNPJ", callback_data="osint_cnpj")],
        [InlineKeyboardButton("🌐 Só Domínio", callback_data="osint_dominio")],
        [InlineKeyboardButton("📞 Telefone", callback_data="osint_telefone")],
        [InlineKeyboardButton("◀️ Voltar", callback_data="menu_main")],
    ])

def agenda_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Novo contrato", callback_data="agenda_novo")],
        [InlineKeyboardButton("✅ Concluir contrato", callback_data="agenda_concluir")],
        [InlineKeyboardButton("🗑️ Remover contrato", callback_data="agenda_remover")],
        [InlineKeyboardButton("◀️ Voltar", callback_data="menu_main")],
    ])

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    await update.message.reply_text(MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=menu_keyboard())

async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "menu_main":
        await q.edit_message_text(MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=menu_keyboard())
    elif data == "menu_osint":
        await q.edit_message_text("🔍 *OSINT* — Escolha:", parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=osint_keyboard())
    elif data == "osint_completo":
        ctx.user_data["aguardando"] = "osint_completo"
        await q.edit_message_text(
            "🔴 *OSINT COMPLETO*\n\nEnvia o CNPJ ou domínio:\n`12345678000199` ou `site.com`",
            parse_mode=ParseMode.MARKDOWN)
    elif data == "osint_cnpj":
        ctx.user_data["aguardando"] = "cnpj"
        await q.edit_message_text("🏢 *CNPJ*\n\nEnvia o CNPJ:", parse_mode=ParseMode.MARKDOWN)
    elif data == "osint_dominio":
        ctx.user_data["aguardando"] = "dominio"
        await q.edit_message_text("🌐 *Domínio*\n\nEnvia o domínio:", parse_mode=ParseMode.MARKDOWN)
    elif data == "osint_telefone":
        ctx.user_data["aguardando"] = "telefone"
        await q.edit_message_text("📞 *Telefone*\n\nEnvia com DDD:", parse_mode=ParseMode.MARKDOWN)
    elif data == "menu_scan":
        ctx.user_data["aguardando"] = "scan"
        await q.edit_message_text("🛡️ *Scan*\n\nEnvia o domínio alvo:", parse_mode=ParseMode.MARKDOWN)
    elif data == "menu_pdf":
        ctx.user_data["aguardando"] = "pdf_alvo"
        await q.edit_message_text(
            "📄 *Gerar PDF*\n\nEnvia o domínio ou CNPJ para gerar o relatório:",
            parse_mode=ParseMode.MARKDOWN)

    elif data == "menu_agenda":
        texto = agenda.listar()
        await q.edit_message_text(texto, parse_mode=ParseMode.MARKDOWN,
                                   reply_markup=agenda_keyboard())
    elif data == "agenda_novo":
        ctx.user_data["aguardando"] = "agenda_novo"
        await q.edit_message_text(
            "➕ *Novo Contrato*\n\nFormato:\n`Cliente | alvo.com | prazo | valor`\n\nExemplo:\n`OleyBet | oleybet.com | 30/03/2026 | R$5000`",
            parse_mode=ParseMode.MARKDOWN)
    elif data == "agenda_concluir":
        ctx.user_data["aguardando"] = "agenda_concluir"
        texto = agenda.listar()
        await q.edit_message_text(
            f"{texto}\n\nEnvia o *número* do contrato para concluir:",
            parse_mode=ParseMode.MARKDOWN)
    elif data == "agenda_remover":
        ctx.user_data["aguardando"] = "agenda_remover"
        texto = agenda.listar()
        await q.edit_message_text(
            f"{texto}\n\nEnvia o *número* do contrato para remover:",
            parse_mode=ParseMode.MARKDOWN)

async def handle_osint_completo(update: Update, ctx, entrada: str):
    msg = await update.message.reply_text("🔴 OSINT iniciado... aguarda 1-2 min.")
    try:
        digits = re.sub(r'\D', '', entrada)
        if len(digits) == 14:
            resultado = await asyncio.to_thread(osint_publico.osint_completo, digits, None, None)
        else:
            dom = entrada.replace("https://","").replace("http://","").strip("/")
            resultado = await asyncio.to_thread(osint_publico.osint_completo, None, dom, None)
        await msg.delete()
        for chunk in [resultado[i:i+4000] for i in range(0, len(resultado), 4000)]:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN,
                                             disable_web_page_preview=True)
        await update.message.reply_text("✅ OSINT concluído.", reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro: {ex}", reply_markup=menu_keyboard())

async def handle_cnpj(update: Update, ctx, cnpj: str):
    msg = await update.message.reply_text("🔍 Consultando CNPJ...")
    try:
        resultado = await asyncio.to_thread(osint_cnpj.consultar, cnpj)
        await msg.edit_text(resultado, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro: {ex}", reply_markup=menu_keyboard())

async def handle_dominio(update: Update, ctx, dominio: str):
    msg = await update.message.reply_text("🌐 Consultando domínio...")
    try:
        resultado = await asyncio.to_thread(osint_dominio.consultar, dominio)
        for chunk in [resultado[i:i+4000] for i in range(0, len(resultado), 4000)]:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        await msg.delete()
        await update.message.reply_text("✅ Concluído.", reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro: {ex}", reply_markup=menu_keyboard())

async def handle_telefone(update: Update, ctx, telefone: str):
    msg = await update.message.reply_text("📞 Consultando...")
    try:
        resultado = await asyncio.to_thread(osint_telefone.consultar, telefone)
        await msg.edit_text(resultado, parse_mode=ParseMode.MARKDOWN, reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro: {ex}", reply_markup=menu_keyboard())

async def handle_scan(update: Update, ctx, dominio: str):
    msg = await update.message.reply_text(f"🛡️ Scan em {dominio}... aguarda 3-5 min.")
    try:
        def rodar():
            r = subprocess.run(["python3", "rednova_v3.py", "-t", dominio],
                               capture_output=True, text=True, timeout=300)
            return r.stdout
        stdout = await asyncio.to_thread(rodar)
        linhas = [l for l in stdout.splitlines() if
                  any(k in l for k in ["[+]","[!]","VULN","RESUMO","Porta","Endpoint"])]
        resumo = "\n".join(linhas[-30:]) or "Scan concluído."
        await msg.edit_text(f"✅ *Scan: {dominio}*\n\n```\n{resumo[:3000]}\n```",
                            parse_mode=ParseMode.MARKDOWN, reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro: {ex}", reply_markup=menu_keyboard())

async def message_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not await check_owner(update): return
    aguardando = ctx.user_data.get("aguardando")
    texto = update.message.text.strip()

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
        await handle_pdf(update, ctx, texto)
        return
    elif aguardando == "agenda_novo":
        ctx.user_data["aguardando"] = None
        resp = agenda.adicionar(texto)
        await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=menu_keyboard())
        return
    elif aguardando == "agenda_concluir":
        ctx.user_data["aguardando"] = None
        resp = agenda.concluir(texto)
        await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=menu_keyboard())
        return
    elif aguardando == "agenda_remover":
        ctx.user_data["aguardando"] = None
        resp = agenda.remover(texto)
        await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN,
                                         reply_markup=menu_keyboard())
        return

    # Auto-detecção CNPJ
    digits = re.sub(r'\D', '', texto)
    if len(digits) == 14:
        await handle_osint_completo(update, ctx, digits)
        return

    # Auto-detecção domínio
    if re.match(r'^[a-zA-Z0-9\-]+\.[a-zA-Z]{2,}(\.[a-zA-Z]{2,})?$', texto):
        await handle_dominio(update, ctx, texto)
        return

    # IA conversacional
    await update.message.chat.send_action("typing")
    resposta = await asyncio.to_thread(ai_brain.chat, texto)
    try:
        await update.message.reply_text(resposta, parse_mode=ParseMode.MARKDOWN,
                                         disable_web_page_preview=True)
    except Exception:
        await update.message.reply_text(resposta, disable_web_page_preview=True)


async def handle_pdf(update: Update, ctx, entrada: str):
    msg = await update.message.reply_text("📄 Gerando PDF...")
    try:
        digits = re.sub(r"\D","",entrada)
        if len(digits) == 14:
            dados = await asyncio.to_thread(osint_publico.osint_completo, digits, None, None)
        else:
            dom = entrada.replace("https://","").replace("http://","").strip("/")
            dados = await asyncio.to_thread(osint_publico.osint_completo, None, dom, None)
        
        # Converter string formatada de volta pra dict básico para o PDF
        dados_dict = {"dominio": entrada, "empresa": {}, "emails": [],
                      "redes": {}, "vazamentos": [], "ips": [], "registro_br": {}}
        
        caminho = await asyncio.to_thread(gerar_pdf.pdf_do_osint, dados_dict, entrada)
        if caminho and os.path.exists(caminho):
            await msg.delete()
            with open(caminho, "rb") as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"RedNova_{entrada}.pdf",
                    caption="📄 Relatório RedNova"
                )
            os.remove(caminho)
        else:
            await msg.edit_text("❌ Erro ao gerar PDF. Verifica se reportlab está instalado.",
                                reply_markup=menu_keyboard())
    except Exception as ex:
        await msg.edit_text(f"Erro PDF: {ex}", reply_markup=menu_keyboard())

# Comandos diretos
async def cmd_menu(update, ctx):
    if not await check_owner(update): return
    await update.message.reply_text(MENU_TEXT, parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=menu_keyboard())

async def cmd_cnpj(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /cnpj 12345678000199"); return
    await handle_cnpj(update, ctx, ctx.args[0])

async def cmd_dominio(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /dominio site.com"); return
    await handle_dominio(update, ctx, ctx.args[0])

async def cmd_scan(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /scan site.com"); return
    await handle_scan(update, ctx, ctx.args[0])

async def cmd_osint(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /osint 12345678000199 ou /osint site.com"); return
    await handle_osint_completo(update, ctx, " ".join(ctx.args))

async def cmd_contrato(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text(
            "Uso: /contrato Cliente | alvo.com | prazo | valor\n"
            "Exemplo: /contrato OleyBet | oleybet.com | 30/03/2026 | R$5000")
        return
    resp = agenda.adicionar(" ".join(ctx.args))
    await update.message.reply_text(resp, parse_mode=ParseMode.MARKDOWN)

async def cmd_agenda(update, ctx):
    if not await check_owner(update): return
    await update.message.reply_text(agenda.listar(), parse_mode=ParseMode.MARKDOWN,
                                     reply_markup=agenda_keyboard())

async def cmd_limpar(update, ctx):
    if not await check_owner(update): return
    await update.message.reply_text(ai_brain.limpar_historico())

async def cmd_telefone(update, ctx):
    if not await check_owner(update): return
    if not ctx.args:
        await update.message.reply_text("Uso: /telefone 11999999999"); return
    await handle_telefone(update, ctx, ctx.args[0])

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start",    start))
    app.add_handler(CommandHandler("menu",     cmd_menu))
    app.add_handler(CommandHandler("osint",    cmd_osint))
    app.add_handler(CommandHandler("cnpj",     cmd_cnpj))
    app.add_handler(CommandHandler("dominio",  cmd_dominio))
    app.add_handler(CommandHandler("telefone", cmd_telefone))
    app.add_handler(CommandHandler("scan",     cmd_scan))
    app.add_handler(CommandHandler("contrato", cmd_contrato))
    app.add_handler(CommandHandler("agenda",   cmd_agenda))
    app.add_handler(CommandHandler("limpar",   cmd_limpar))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    print("RedNova Bot v2 iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
