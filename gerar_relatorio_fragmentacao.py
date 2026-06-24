from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from coletar_dados import coletar_tudo

print("Conectando ao DB2 e coletando dados...")
_db = coletar_tudo()

dados = [
    {
        "schema":             t[0],
        "tabela":             t[1],
        "total_linhas":       t[2],
        "paginas_usadas":     t[3],
        "paginas_alocadas":   t[4],
        "overflow":           t[5],
        "pct_fragmentacao":   t[6],
        "ultima_estatistica": t[8],
    }
    for t in _db["tabelas"]
]

usuarios_db = [
    {
        "grantee": u[0], "tipo": u[1],
        "dbadm": u[2],  "secadm": u[3],   "dataaccess": u[4],  "accessctrl": u[5],
        "connect": u[6], "createtab": u[7], "bindadd": u[8],    "implschema": u[9],
        "load": u[10],   "nofence": u[11],  "sqladm": u[12],    "wlmadm": u[13],
        "explain": u[14],
    }
    for u in _db["usuarios_db"]
]

permissoes_tabela = [
    {
        "grantee": p[0], "tipo": p[1], "schema": p[2], "tabela": p[3],
        "select": p[4],  "insert": p[5], "update": p[6], "delete": p[7],
        "alter": p[8],   "index": p[9],  "ref": p[10],   "control": p[11],
    }
    for p in _db["perm_tabela"]
]

if _db["backups"]:
    _b = _db["backups"][0]
    _tipo_map = {"Full": "F", "Incremental": "I", "Delta": "D"}
    backup = {
        "inicio": _b[2],
        "fim":    _b[3],
        "tipo":   _tipo_map.get(_b[1], _b[1]),
        "local":  _b[4],
        "status": _b[5],
    }
else:
    backup = {"inicio": "", "fim": "", "tipo": "F", "local": "", "status": "N/D"}

print(f"Dados coletados: {len(dados)} tabela(s).")

def formatar_timestamp(ts):
    return datetime.strptime(ts, "%Y%m%d%H%M%S").strftime("%d/%m/%Y %H:%M:%S")

OUTPUT = "/Users/jorgehbchaves/Dev/db2/relatorio_fragmentacao.pdf"

doc = SimpleDocTemplate(
    OUTPUT,
    pagesize=A4,
    rightMargin=2*cm,
    leftMargin=2*cm,
    topMargin=2.5*cm,
    bottomMargin=2*cm,
)

styles = getSampleStyleSheet()

style_title = ParagraphStyle(
    "titulo",
    parent=styles["Title"],
    fontSize=18,
    textColor=colors.HexColor("#1a3a5c"),
    spaceAfter=4,
    alignment=TA_CENTER,
)
style_subtitle = ParagraphStyle(
    "subtitulo",
    parent=styles["Normal"],
    fontSize=10,
    textColor=colors.HexColor("#555555"),
    spaceAfter=2,
    alignment=TA_CENTER,
)
style_section = ParagraphStyle(
    "secao",
    parent=styles["Heading2"],
    fontSize=12,
    textColor=colors.HexColor("#1a3a5c"),
    spaceBefore=14,
    spaceAfter=6,
)
style_note = ParagraphStyle(
    "nota",
    parent=styles["Normal"],
    fontSize=8,
    textColor=colors.HexColor("#777777"),
    spaceAfter=4,
)

def status_fragmentacao(pct):
    if pct == 0:
        return ("Ótimo", colors.HexColor("#27ae60"))
    elif pct < 20:
        return ("Bom", colors.HexColor("#2ecc71"))
    elif pct < 40:
        return ("Atenção", colors.HexColor("#f39c12"))
    else:
        return ("Crítico", colors.HexColor("#e74c3c"))

story = []

story.append(Paragraph("Relatório de Fragmentação de Tabelas", style_title))
story.append(Paragraph(f"Banco de Dados: DB2 LUW (TESTDB)", style_subtitle))
story.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}", style_subtitle))
story.append(Spacer(1, 0.3*cm))
story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1a3a5c")))
story.append(Spacer(1, 0.5*cm))

# Resumo executivo
story.append(Paragraph("Resumo Executivo", style_section))

total_tabelas = len(dados)
criticas = sum(1 for d in dados if d["pct_fragmentacao"] >= 40)
atencao = sum(1 for d in dados if 20 <= d["pct_fragmentacao"] < 40)
saudaveis = total_tabelas - criticas - atencao

resumo_data = [
    ["Métrica", "Valor"],
    ["Total de Tabelas Analisadas", str(total_tabelas)],
    ["Tabelas Saudáveis (< 20%)", str(saudaveis)],
    ["Tabelas em Atenção (20–40%)", str(atencao)],
    ["Tabelas Críticas (≥ 40%)", str(criticas)],
]

resumo_table = Table(resumo_data, colWidths=[10*cm, 5*cm])
resumo_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, 0), 10),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("ALIGN", (1, 0), (1, -1), "CENTER"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE", (0, 1), (-1, -1), 9),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
]))
story.append(resumo_table)
story.append(Spacer(1, 0.5*cm))

# Detalhe por tabela
story.append(Paragraph("Detalhamento por Tabela", style_section))

header = ["Schema", "Tabela", "Linhas", "Pág. Usadas", "Pág. Alocadas", "Overflow", "Fragmentação", "Status"]
table_data = [header]

for d in dados:
    status_label, status_color = status_fragmentacao(d["pct_fragmentacao"])
    table_data.append([
        d["schema"],
        d["tabela"],
        str(d["total_linhas"]),
        str(d["paginas_usadas"]),
        str(d["paginas_alocadas"]),
        str(d["overflow"]),
        f"{d['pct_fragmentacao']:.2f}%",
        status_label,
    ])

col_widths = [3*cm, 3*cm, 2*cm, 2.5*cm, 2.8*cm, 2*cm, 2.8*cm, 2.5*cm]
det_table = Table(table_data, colWidths=col_widths, repeatRows=1)

style_det = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ("ALIGN", (0, 0), (1, -1), "LEFT"),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
])

for i, d in enumerate(dados, start=1):
    _, cor = status_fragmentacao(d["pct_fragmentacao"])
    style_det.add("BACKGROUND", (7, i), (7, i), cor)
    style_det.add("TEXTCOLOR", (7, i), (7, i), colors.white)
    style_det.add("FONTNAME", (7, i), (7, i), "Helvetica-Bold")

det_table.setStyle(style_det)
story.append(det_table)
story.append(Spacer(1, 0.5*cm))

# Legenda de status
story.append(Paragraph("Legenda de Status", style_section))
legenda_data = [
    ["Status", "Faixa de Fragmentação", "Recomendação"],
    ["Ótimo", "0%", "Nenhuma ação necessária"],
    ["Bom", "< 20%", "Monitorar periodicamente"],
    ["Atenção", "20% – 40%", "Planejar REORG em janela de manutenção"],
    ["Crítico", "≥ 40%", "Executar REORG com urgência"],
]
leg_table = Table(legenda_data, colWidths=[3*cm, 5*cm, 9*cm])
leg_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
])
cores_status = [
    colors.HexColor("#27ae60"),
    colors.HexColor("#2ecc71"),
    colors.HexColor("#f39c12"),
    colors.HexColor("#e74c3c"),
]
for i, cor in enumerate(cores_status, start=1):
    leg_style.add("BACKGROUND", (0, i), (0, i), cor)
    leg_style.add("TEXTCOLOR", (0, i), (0, i), colors.white)
    leg_style.add("FONTNAME", (0, i), (0, i), "Helvetica-Bold")
leg_table.setStyle(leg_style)
story.append(leg_table)

# Usuários e permissões do banco
story.append(Paragraph("Usuários e Permissões", style_section))
story.append(Paragraph("Autoridades no Banco de Dados", ParagraphStyle("sub2", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#1a3a5c"), spaceBefore=4, spaceAfter=6, fontName="Helvetica-Bold")))

auth_header = ["Usuário", "Tipo", "DB Admin", "Sec Admin", "Data Access", "Access Ctrl", "Connect", "CreateTab", "Load", "SQL Adm"]
auth_data = [auth_header]
for u in usuarios_db:
    def yn(v): return "Sim" if v == "S" else "Não"
    auth_data.append([
        u["grantee"], u["tipo"],
        yn(u["dbadm"]), yn(u["secadm"]), yn(u["dataaccess"]), yn(u["accessctrl"]),
        yn(u["connect"]), yn(u["createtab"]), yn(u["load"]), yn(u["sqladm"]),
    ])

auth_col_widths = [2.8*cm, 1.8*cm, 1.6*cm, 1.6*cm, 1.8*cm, 1.8*cm, 1.4*cm, 1.6*cm, 1.2*cm, 1.4*cm]
auth_table = Table(auth_data, colWidths=auth_col_widths, repeatRows=1)
auth_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ALIGN", (2, 0), (-1, -1), "CENTER"),
    ("ALIGN", (0, 0), (1, -1), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
])
for i, u in enumerate(usuarios_db, start=1):
    for col, campo in enumerate(["dbadm","secadm","dataaccess","accessctrl","connect","createtab","load","sqladm"], start=2):
        cor_cell = colors.HexColor("#27ae60") if u[campo] == "S" else colors.HexColor("#e74c3c")
        auth_style.add("BACKGROUND", (col, i), (col, i), cor_cell)
        auth_style.add("TEXTCOLOR", (col, i), (col, i), colors.white)
        auth_style.add("FONTNAME", (col, i), (col, i), "Helvetica-Bold")
auth_table.setStyle(auth_style)
story.append(auth_table)
story.append(Spacer(1, 0.4*cm))

story.append(Paragraph("Permissões por Tabela", ParagraphStyle("sub3", parent=styles["Normal"], fontSize=10, textColor=colors.HexColor("#1a3a5c"), spaceBefore=4, spaceAfter=6, fontName="Helvetica-Bold")))

perm_header = ["Usuário", "Tipo", "Schema", "Tabela", "SELECT", "INSERT", "UPDATE", "DELETE", "ALTER", "INDEX", "CONTROL"]
perm_data = [perm_header]
for p in permissoes_tabela:
    def fg(v): return "G" if v == "G" else ("S" if v == "S" else "N")
    perm_data.append([
        p["grantee"], p["tipo"], p["schema"], p["tabela"],
        fg(p["select"]), fg(p["insert"]), fg(p["update"]), fg(p["delete"]),
        fg(p["alter"]), fg(p["index"]), fg(p["control"]),
    ])

perm_col_widths = [2.5*cm, 1.5*cm, 2*cm, 2*cm, 1.2*cm, 1.2*cm, 1.3*cm, 1.3*cm, 1.2*cm, 1.2*cm, 1.6*cm]
perm_table = Table(perm_data, colWidths=perm_col_widths, repeatRows=1)
perm_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 7.5),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ALIGN", (4, 0), (-1, -1), "CENTER"),
    ("ALIGN", (0, 0), (3, -1), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
])
for i, p in enumerate(permissoes_tabela, start=1):
    for col, campo in enumerate(["select","insert","update","delete","alter","index","control"], start=4):
        val = p[campo]
        cor_cell = colors.HexColor("#27ae60") if val in ("G", "S") else colors.HexColor("#e74c3c")
        perm_style.add("BACKGROUND", (col, i), (col, i), cor_cell)
        perm_style.add("TEXTCOLOR", (col, i), (col, i), colors.white)
        perm_style.add("FONTNAME", (col, i), (col, i), "Helvetica-Bold")
perm_table.setStyle(perm_style)
story.append(perm_table)

story.append(Paragraph("G = com WITH GRANT OPTION (pode conceder a outros)  ·  S = permissão direta  ·  N = sem permissão", ParagraphStyle("legperm", parent=styles["Normal"], fontSize=7, textColor=colors.HexColor("#777777"), spaceBefore=3)))
story.append(Spacer(1, 0.4*cm))

# Último backup
story.append(Paragraph("Último Backup", style_section))

tipo_backup = "Full (Completo)" if backup["tipo"] == "F" else "Incremental" if backup["tipo"] == "I" else backup["tipo"]
duracao = datetime.strptime(backup["fim"], "%Y%m%d%H%M%S") - datetime.strptime(backup["inicio"], "%Y%m%d%H%M%S")

backup_data = [
    ["Campo", "Valor"],
    ["Data/Hora Início", formatar_timestamp(backup["inicio"])],
    ["Data/Hora Fim", formatar_timestamp(backup["fim"])],
    ["Duração", f"{int(duracao.total_seconds())} segundo(s)"],
    ["Tipo", tipo_backup],
    ["Local", backup["local"]],
    ["Status", backup["status"]],
]

backup_table = Table(backup_data, colWidths=[6*cm, 11*cm])
backup_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a3a5c")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4f8"), colors.white]),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("TOPPADDING", (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ("BACKGROUND", (1, 6), (1, 6), colors.HexColor("#27ae60")),
    ("TEXTCOLOR", (1, 6), (1, 6), colors.white),
    ("FONTNAME", (1, 6), (1, 6), "Helvetica-Bold"),
])
backup_table.setStyle(backup_style)
story.append(backup_table)

story.append(Spacer(1, 0.5*cm))
story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc")))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(
    f"Relatório gerado automaticamente via MCP DB2 LUW · {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
    style_note
))

doc.build(story)
print(f"PDF gerado: {OUTPUT}")
