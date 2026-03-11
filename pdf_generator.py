"""Gerador de PDF profissional."""
import os, re
from datetime import datetime

def gerar(results: dict) -> str:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable, PageBreak)
        from reportlab.lib.enums import TA_CENTER
    except ImportError:
        return None

    perfil   = results.get("perfil", {})
    target   = results.get("target", "alvo")
    tipo     = results.get("tipo", "")
    agora    = datetime.now().strftime("%d/%m/%Y %H:%M")
    filename = f"/tmp/rednova_{re.sub(r'[^a-z0-9]','_',target.lower())}_{datetime.now().strftime('%Y%m%d%H%M')}.pdf"

    VERMELHO  = HexColor("#C0392B")
    CINZA_ESC = HexColor("#2C2C2C")
    CINZA_MED = HexColor("#777777")
    CINZA_CLR = HexColor("#F5F5F5")
    LARANJA   = HexColor("#E67E22")
    VERDE     = HexColor("#27AE60")
    AZUL      = HexColor("#2980B9")

    doc = SimpleDocTemplate(filename, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()

    S = lambda name, **kw: ParagraphStyle(name, **kw)
    s_titulo = S("t", fontSize=22, textColor=VERMELHO, fontName="Helvetica-Bold", spaceAfter=2)
    s_sub    = S("s", fontSize=10, textColor=CINZA_MED, fontName="Helvetica", spaceAfter=10)
    s_h2     = S("h2", fontSize=13, textColor=VERMELHO, fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=5)
    s_body   = S("b", fontSize=9,  textColor=CINZA_ESC, fontName="Helvetica", leading=14, spaceAfter=3)
    s_footer = S("f", fontSize=7,  textColor=CINZA_MED, fontName="Helvetica", alignment=TA_CENTER)
    s_badge  = S("badge", fontSize=9, fontName="Helvetica-Bold")

    def hr(): return HRFlowable(width="100%", thickness=1, color=VERMELHO, spaceAfter=8)
    def sp(h=8): return Spacer(1, h)
    def tbl(data, cols, style_extra=[]):
        t = Table(data, colWidths=cols)
        base = [
            ("BACKGROUND",(0,0),(0,-1), CINZA_CLR),
            ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),9),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("PADDING",(0,0),(-1,-1),6),
            ("VALIGN",(0,0),(-1,-1),"TOP"),
        ]
        t.setStyle(TableStyle(base + style_extra))
        return t

    story = []

    # ── CAPA ────────────────────────────────────────
    story += [
        Paragraph("REDNOVA", s_titulo),
        Paragraph("Intelligence Investigation Report", s_sub),
        hr(),
        tbl([
            ["Alvo",         target],
            ["Tipo",         tipo.upper()],
            ["Data",         agora],
            ["Pesquisador",  "REDNOVA / Rael"],
            ["Classificação","CONFIDENCIAL"],
            ["Risk Score",   f"{perfil.get('risk_score',0)}/100"],
        ], [4*cm, 13*cm]),
        sp(16),
    ]

    # ── IDENTIDADES ──────────────────────────────────
    identidades = perfil.get("identidades",[])
    if identidades:
        story += [Paragraph("IDENTIDADES ENCONTRADAS", s_h2), hr()]
        for nome in identidades:
            story.append(Paragraph(f"👤 {nome}", s_body))
        story.append(sp())

    # ── CNPJ ─────────────────────────────────────────
    cnpj = results.get("cnpj",{})
    if cnpj:
        story += [Paragraph("DADOS DA EMPRESA (CNPJ)", s_h2), hr()]
        sit = cnpj.get("situacao","?")
        rows = [
            ["CNPJ", f"{cnpj.get('cnpj','')}"],
            ["Razão Social", cnpj.get("razao_social","?")],
            ["Fantasia", cnpj.get("nome_fantasia","—")],
            ["Situação", f"{sit}"],
            ["Abertura", cnpj.get("abertura","?")],
            ["Atividade", str(cnpj.get("atividade",""))[:60]],
            ["Endereço", f"{cnpj.get('logradouro','')} {cnpj.get('numero','')}, {cnpj.get('municipio','')} - {cnpj.get('uf','')}"],
            ["Email", cnpj.get("email","—")],
            ["Telefone", cnpj.get("telefone","—")],
        ]
        story.append(tbl(rows, [4*cm, 13*cm]))
        qsa = cnpj.get("qsa",[]) or []
        if qsa:
            story += [sp(8), Paragraph("Sócios (QSA):", s_body)]
            for s in qsa[:5]:
                nome_s = re.sub(r'\s+\d{11,14}\s*$','', s.get("nome_socio") or s.get("nome","?")).strip()
                story.append(Paragraph(f"  • {nome_s}", s_body))
        story.append(sp())

    # ── DOMÍNIO ──────────────────────────────────────
    dom = results.get("dominio",{})
    if dom and dom.get("dominio"):
        story += [Paragraph("INTELIGÊNCIA DE DOMÍNIO", s_h2), hr()]
        rows = [
            ["Domínio", dom.get("dominio","?")],
            ["Registrante", dom.get("dono","—")],
            ["Criado", dom.get("criado","—")],
            ["Expira", dom.get("expira","—")],
            ["Nameservers", " | ".join(dom.get("nameservers",[])[:2])],
            ["IPs", " | ".join(list(dom.get("ips",{}).values())[:3])],
            ["Subdomínios", str(len(dom.get("subdominios",[])))],
        ]
        story.append(tbl(rows, [4*cm, 13*cm]))
        subs = dom.get("subdominios",[])
        if subs:
            story += [sp(4), Paragraph(f"Subdomínios: {', '.join(subs[:10])}", s_body)]
        story.append(sp())

    # ── EMAILS ───────────────────────────────────────
    emails = perfil.get("emails",[])
    if emails:
        story += [Paragraph(f"EMAILS ENCONTRADOS ({len(emails)})", s_h2), hr()]
        for e in emails[:10]:
            story.append(Paragraph(f"📧 {e}", s_body))
        story.append(sp())

    # ── REDES SOCIAIS ─────────────────────────────────
    redes = perfil.get("redes",{})
    if redes:
        story += [Paragraph("REDES SOCIAIS", s_h2), hr()]
        icons = {"instagram":"📸","facebook":"🔵","linkedin":"💼","twitter":"🐦",
                 "youtube":"▶️","github":"🐙","tiktok":"🎵","telegram":"✈️",
                 "whatsapp":"💬","jusbrasil":"⚖️","escavador":"🔎"}
        rows = []
        for rede, url in redes.items():
            score = perfil.get("confianca",{}).get(rede, 60)
            icon = icons.get(rede,"•")
            rows.append([f"{icon} {rede.capitalize()}", url, f"{score}%"])
        t = Table([["Rede","URL","Confiança"]] + rows, colWidths=[4*cm, 10*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),VERMELHO),
            ("TEXTCOLOR",(0,0),(-1,0),white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("PADDING",(0,0),(-1,-1),5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[white, CINZA_CLR]),
        ]))
        story.append(t)
        story.append(sp())

    # ── VAZAMENTOS ────────────────────────────────────
    vaz = perfil.get("vazamentos",[])
    if vaz:
        story += [Paragraph("VAZAMENTOS DE DADOS", s_h2), hr()]
        rows = [["Nome","Data","Contas","Dados Expostos"]]
        for v in vaz:
            contas = f"{v.get('contas',0):,}".replace(",",".")
            rows.append([v.get("nome","?"), v.get("data","?"), contas,
                         str(v.get("tipos") or v.get("dados",""))[:40]])
        t = Table(rows, colWidths=[4*cm, 2.5*cm, 2.5*cm, 8*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),VERMELHO),
            ("TEXTCOLOR",(0,0),(-1,0),white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("PADDING",(0,0),(-1,-1),5),
        ]))
        story.append(t)
        story.append(sp())

    # ── TIMELINE ─────────────────────────────────────
    timeline = perfil.get("timeline",[])
    if timeline:
        story += [Paragraph("TIMELINE", s_h2), hr()]
        rows = [["Data","Evento","Tipo"]]
        for ev in timeline:
            rows.append([ev.get("data","?"), ev.get("evento","?"), ev.get("tipo","?").upper()])
        t = Table(rows, colWidths=[3*cm, 11*cm, 3*cm])
        t.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0),CINZA_ESC),
            ("TEXTCOLOR",(0,0),(-1,0),white),
            ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
            ("FONTSIZE",(0,0),(-1,-1),8),
            ("GRID",(0,0),(-1,-1),0.3,HexColor("#DDDDDD")),
            ("PADDING",(0,0),(-1,-1),5),
            ("ROWBACKGROUNDS",(0,1),(-1,-1),[white, CINZA_CLR]),
        ]))
        story.append(t)
        story.append(sp())

    # ── RODAPÉ ────────────────────────────────────────
    story += [
        sp(20),
        HRFlowable(width="100%", thickness=2, color=VERMELHO),
        Paragraph(f"REDNOVA Intelligence Platform | {agora} | CONFIDENCIAL", s_footer),
        Paragraph("Uso exclusivo para pesquisa autorizada de segurança.", s_footer),
    ]

    doc.build(story)
    return filename
