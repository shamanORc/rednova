"""
REDNOVA — Gerador de PDF de Relatório de Segurança
Mesmo layout dos relatórios MagicWings e PaulistinhaOT
"""
import os, re
from datetime import datetime

def gerar(dados_osint: dict, findings: list = None, alvo: str = "") -> str:
    """Gera PDF e retorna o caminho do arquivo."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.colors import HexColor, white, black
        from reportlab.lib.units import cm
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
    except ImportError:
        return None

    agora = datetime.now().strftime("%d/%m/%Y")
    nome_arquivo = f"/tmp/rednova_report_{alvo.replace('.','_')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

    doc = SimpleDocTemplate(nome_arquivo, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)

    # Cores RedNova
    VERMELHO  = HexColor("#C0392B")
    CINZA_ESC = HexColor("#2C2C2C")
    CINZA_MED = HexColor("#555555")
    CINZA_CLR = HexColor("#F5F5F5")
    BRANCO    = white

    styles = getSampleStyleSheet()

    s_titulo = ParagraphStyle("titulo", fontSize=22, textColor=VERMELHO,
                               spaceAfter=4, fontName="Helvetica-Bold")
    s_sub    = ParagraphStyle("sub", fontSize=11, textColor=CINZA_MED,
                               spaceAfter=12, fontName="Helvetica")
    s_h2     = ParagraphStyle("h2", fontSize=13, textColor=VERMELHO,
                               spaceBefore=16, spaceAfter=6, fontName="Helvetica-Bold")
    s_body   = ParagraphStyle("body", fontSize=9, textColor=CINZA_ESC,
                               spaceAfter=4, fontName="Helvetica", leading=14)
    s_code   = ParagraphStyle("code", fontSize=8, textColor=HexColor("#1a1a2e"),
                               fontName="Courier", backColor=HexColor("#f0f0f0"),
                               borderPadding=4, spaceAfter=4)
    s_footer = ParagraphStyle("footer", fontSize=7, textColor=CINZA_MED,
                               alignment=TA_CENTER, fontName="Helvetica")

    story = []

    # ── CABEÇALHO ───────────────────────────────────────────────
    story.append(Paragraph("RELATÓRIO DE SEGURANÇA", s_titulo))
    story.append(Paragraph("Vulnerability Disclosure Report — Responsible Security Research", s_sub))
    story.append(HRFlowable(width="100%", thickness=2, color=VERMELHO, spaceAfter=12))

    # Tabela de metadados
    e = dados_osint.get("empresa", {})
    empresa_nome = (e.get("nome_fantasia") or e.get("razao_social") or alvo or "—")
    meta = [
        ["Alvo", alvo or empresa_nome],
        ["Data", agora],
        ["Pesquisador", "Rednova (Rael)"],
        ["Classificação", "Confidencial"],
        ["Metodologia", "Black-Box / OSINT / Reconhecimento Ativo"],
        ["Versão", "1.0"],
    ]
    t_meta = Table(meta, colWidths=[4*cm, 13*cm])
    t_meta.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (0,-1), CINZA_CLR),
        ("TEXTCOLOR",  (0,0), (0,-1), CINZA_MED),
        ("TEXTCOLOR",  (1,0), (1,-1), CINZA_ESC),
        ("FONTNAME",   (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [BRANCO, CINZA_CLR]),
        ("GRID",       (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
        ("PADDING",    (0,0), (-1,-1), 6),
    ]))
    story.append(t_meta)
    story.append(Spacer(1, 16))

    # ── SUMÁRIO DE FINDINGS ──────────────────────────────────────
    findings = findings or []
    altos  = [f for f in findings if f.get("sev","").upper() == "ALTO"]
    medios = [f for f in findings if f.get("sev","").upper() in ("MÉDIO","MEDIO")]
    baixos = [f for f in findings if f.get("sev","").upper() in ("BAIXO","INFO","INFORMATIVO")]

    story.append(Paragraph("SUMÁRIO EXECUTIVO", s_h2))
    story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO, spaceAfter=8))

    if findings:
        sev_data = [
            ["Severidade", "Qtd", "Findings"],
            ["Alto",   str(len(altos)),  ", ".join(f["titulo"] for f in altos[:3])  or "—"],
            ["Médio",  str(len(medios)), ", ".join(f["titulo"] for f in medios[:3]) or "—"],
            ["Baixo/Info", str(len(baixos)), ", ".join(f["titulo"] for f in baixos[:3]) or "—"],
        ]
        t_sev = Table(sev_data, colWidths=[3*cm, 2*cm, 12*cm])
        t_sev.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (-1,0),  VERMELHO),
            ("TEXTCOLOR",   (0,0), (-1,0),  BRANCO),
            ("FONTNAME",    (0,0), (-1,0),  "Helvetica-Bold"),
            ("BACKGROUND",  (0,1), (-1,1),  HexColor("#FADBD8")),
            ("BACKGROUND",  (0,2), (-1,2),  HexColor("#FDEBD0")),
            ("BACKGROUND",  (0,3), (-1,3),  HexColor("#FDFEFE")),
            ("FONTNAME",    (0,1), (0,-1),  "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 9),
            ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
            ("PADDING",     (0,0), (-1,-1), 7),
        ]))
        story.append(t_sev)
    else:
        story.append(Paragraph("Nenhum finding registrado. Execute o scan e reenvie.", s_body))

    story.append(Spacer(1, 12))

    # ── DADOS OSINT ──────────────────────────────────────────────
    story.append(Paragraph("INFORMAÇÕES DO ALVO (OSINT)", s_h2))
    story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO, spaceAfter=8))

    osint_rows = []
    if e.get("razao_social"):
        razao = re.sub(r'\s+\d{11,14}\s*$','', e["razao_social"]).strip()
        osint_rows.append(["Razão Social", razao])
    if e.get("nome_fantasia"):
        osint_rows.append(["Fantasia", e["nome_fantasia"]])
    if dados_osint.get("dominio"):
        osint_rows.append(["Domínio", dados_osint["dominio"]])
    reg = dados_osint.get("registro_br", {})
    if reg.get("dono_nome"):
        osint_rows.append(["Registrante", reg["dono_nome"]])
    if reg.get("criado"):
        osint_rows.append(["Domínio criado", reg["criado"]])
    ips = dados_osint.get("ips", [])
    if ips:
        osint_rows.append(["IPs", " | ".join(x["ip"] for x in ips[:3])])
    emails = dados_osint.get("emails", [])
    if emails:
        osint_rows.append(["Emails", "\n".join(emails[:5])])
    redes = dados_osint.get("redes", {})
    if redes:
        osint_rows.append(["Redes Sociais", "\n".join(f"{k}: {v}" for k,v in list(redes.items())[:4])])
    vaz = dados_osint.get("vazamentos", [])
    if vaz:
        osint_rows.append(["Vazamentos", "\n".join(f"{v['nome']} ({v['data']})" for v in vaz[:3])])

    if osint_rows:
        t_osint = Table(osint_rows, colWidths=[4*cm, 13*cm])
        t_osint.setStyle(TableStyle([
            ("BACKGROUND",  (0,0), (0,-1), CINZA_CLR),
            ("TEXTCOLOR",   (0,0), (0,-1), CINZA_MED),
            ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("ROWBACKGROUNDS",(0,0),(-1,-1),[BRANCO, CINZA_CLR]),
            ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
            ("PADDING",     (0,0), (-1,-1), 6),
            ("VALIGN",      (0,0), (-1,-1), "TOP"),
        ]))
        story.append(t_osint)

    # ── FINDINGS DETALHADOS ──────────────────────────────────────
    if findings:
        story.append(Paragraph("ACHADOS DETALHADOS", s_h2))
        story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO, spaceAfter=8))

        cores_sev = {
            "ALTO":   HexColor("#C0392B"),
            "MÉDIO":  HexColor("#E67E22"),
            "MEDIO":  HexColor("#E67E22"),
            "BAIXO":  HexColor("#27AE60"),
            "INFO":   HexColor("#2980B9"),
        }

        for i, f in enumerate(findings, 1):
            sev = f.get("sev","INFO").upper()
            cor_sev = cores_sev.get(sev, HexColor("#888888"))
            story.append(Paragraph(f"FINDING #{i} — {f.get('titulo','?')}", s_h2))

            det_rows = [
                ["Severidade", f.get("sev","?")],
                ["Endpoint",   f.get("endpoint","?")],
            ]
            if f.get("cvss"):
                det_rows.append(["CVSS", f["cvss"]])

            t_det = Table(det_rows, colWidths=[4*cm, 13*cm])
            t_det.setStyle(TableStyle([
                ("BACKGROUND",  (0,0), (0,-1), CINZA_CLR),
                ("FONTNAME",    (0,0), (0,-1), "Helvetica-Bold"),
                ("FONTSIZE",    (0,0), (-1,-1), 8),
                ("GRID",        (0,0), (-1,-1), 0.3, HexColor("#DDDDDD")),
                ("PADDING",     (0,0), (-1,-1), 5),
            ]))
            story.append(t_det)

            if f.get("descricao"):
                story.append(Paragraph("<b>Descrição:</b>", s_body))
                story.append(Paragraph(f["descricao"], s_body))
            if f.get("impacto"):
                story.append(Paragraph("<b>Impacto:</b>", s_body))
                story.append(Paragraph(f["impacto"], s_body))
            if f.get("recomendacao"):
                story.append(Paragraph("<b>Recomendação:</b>", s_body))
                story.append(Paragraph(f["recomendacao"], s_body))
            story.append(Spacer(1, 8))

    # ── RODAPÉ ───────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=1, color=VERMELHO))
    story.append(Paragraph(
        f"Relatório gerado em {agora} | Rednova Security Research | Uso confidencial",
        s_footer
    ))

    doc.build(story)
    return nome_arquivo


def pdf_do_osint(dados_osint: dict, alvo: str = "") -> str:
    """Gera PDF só com dados OSINT, sem findings."""
    return gerar(dados_osint, findings=[], alvo=alvo)
