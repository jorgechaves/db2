from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from coletar_dados import coletar_tudo

# ── Coleta ao vivo do DB2 ─────────────────────────────────────────────────────

print("Conectando ao DB2 e coletando dados...")
_db = coletar_tudo()

GERADO_EM   = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
PAGE_W      = 17 * cm  # largura útil (A4 21cm - 2x2cm margens)

ambiente    = _db["ambiente"]
db_cfg      = _db["db_cfg"]
_cfg_map    = _db["db_cfg_map"]
tablespaces = _db["tablespaces"]
buffer_pools= _db["buffer_pools"]
log_util    = _db["log_util"]
objetos     = _db["objetos"]
tabelas     = _db["tabelas"]
indices     = _db["indices"]
usuarios_db = _db["usuarios_db"]
perm_tabela = _db["perm_tabela"]
backups     = _db["backups"]
conexoes    = _db["conexoes"]

print(f"Dados coletados: {len(tabelas)} tabela(s), {len(conexoes)} conexão(ões).")

# ── Cores e estilos ──────────────────────────────────────────────────────────

COR_AZUL     = colors.HexColor("#1a3a5c")
COR_AZUL_CLR = colors.HexColor("#2c5f8a")
COR_VERDE    = colors.HexColor("#27ae60")
COR_AMARELO  = colors.HexColor("#f39c12")
COR_VERMELHO = colors.HexColor("#e74c3c")
COR_CINZA    = colors.HexColor("#f0f4f8")
COR_BORDA    = colors.HexColor("#cccccc")
COR_TEXTO    = colors.HexColor("#777777")

styles = getSampleStyleSheet()

s_title = ParagraphStyle("titulo", parent=styles["Title"],
    fontSize=20, textColor=COR_AZUL, spaceAfter=4, alignment=TA_CENTER)
s_subtitle = ParagraphStyle("subtitulo", parent=styles["Normal"],
    fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=2, alignment=TA_CENTER)
s_section = ParagraphStyle("secao", parent=styles["Heading1"],
    fontSize=13, textColor=colors.white, spaceBefore=0, spaceAfter=0,
    fontName="Helvetica-Bold", leftIndent=6)
s_sub = ParagraphStyle("subsecao", parent=styles["Heading2"],
    fontSize=10, textColor=COR_AZUL, spaceBefore=10, spaceAfter=4,
    fontName="Helvetica-Bold")
s_note = ParagraphStyle("nota", parent=styles["Normal"],
    fontSize=7, textColor=COR_TEXTO, spaceAfter=2)
s_normal = ParagraphStyle("normal", parent=styles["Normal"],
    fontSize=8.5, spaceAfter=3)

# ── Helpers ──────────────────────────────────────────────────────────────────

def fmt_ts(ts):
    return datetime.strptime(ts, "%Y%m%d%H%M%S").strftime("%d/%m/%Y %H:%M:%S")

def fmt_kb(kb):
    if kb >= 1048576: return f"{kb/1048576:.1f} GB"
    if kb >= 1024:    return f"{kb/1024:.1f} MB"
    return f"{kb} KB"

def yn_cell(v, sim="Sim", nao="Não"):
    return sim if v == "S" else nao

def cor_pct(pct):
    if pct < 70:   return COR_VERDE
    if pct < 90:   return COR_AMARELO
    return COR_VERMELHO

def cor_frag(pct):
    if pct == 0:   return COR_VERDE
    if pct < 20:   return colors.HexColor("#2ecc71")
    if pct < 40:   return COR_AMARELO
    return COR_VERMELHO

def section_header(title):
    bg = Table([[Paragraph(title, s_section)]], colWidths=[PAGE_W])
    bg.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), COR_AZUL),
        ("TOPPADDING",  (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0),(-1,-1), 6),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
    ]))
    return bg

def base_table_style(header_bg=COR_AZUL):
    return TableStyle([
        ("BACKGROUND",   (0,0), (-1,0), header_bg),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 7.5),
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [COR_CINZA, colors.white]),
        ("GRID",         (0,0), (-1,-1), 0.4, COR_BORDA),
        ("TOPPADDING",   (0,0), (-1,-1), 4),
        ("BOTTOMPADDING",(0,0), (-1,-1), 4),
        ("LEFTPADDING",  (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
    ])

def kv_table(rows, col1=7*cm, col2=10*cm):
    data = [["Parâmetro", "Valor"]] + [[r[0], r[1]] for r in rows]
    t = Table(data, colWidths=[col1, col2])
    t.setStyle(base_table_style())
    return t

# ── Construção do story ──────────────────────────────────────────────────────

story = []

# ── Capa ────────────────────────────────────────────────────────────────────
story.append(Spacer(1, 2*cm))
story.append(Paragraph("Assessment Geral do Ambiente", s_title))
story.append(Paragraph("IBM DB2 LUW", s_subtitle))
story.append(Paragraph(f"Banco: <b>TESTDB</b> &nbsp;·&nbsp; Instância: <b>db2inst1</b>", s_subtitle))
story.append(Paragraph(f"Gerado em: {GERADO_EM}", s_subtitle))
story.append(Spacer(1, 0.4*cm))
story.append(HRFlowable(width="100%", thickness=2, color=COR_AZUL))
story.append(Spacer(1, 0.5*cm))

# Resumo executivo cards
_tbsp_valid   = [(t[0], t[7]) for t in tablespaces if t[7] >= 0]
_tbsp_crit    = max(_tbsp_valid, key=lambda x: x[1]) if _tbsp_valid else ("N/D", 0)
_tbsp_crit_str= f"{_tbsp_crit[0]} {_tbsp_crit[1]:.2f}%".replace(".", ",")

_max_frag = max((t[6] for t in tabelas), default=0)
_frag_label = "Ótimo" if _max_frag == 0 else "Bom" if _max_frag < 20 else "Atenção" if _max_frag < 40 else "Crítico"

_ult_backup = "N/D"
if backups:
    try:
        _bd = datetime.strptime(backups[0][2], "%Y%m%d%H%M%S")
        _ult_backup = f"{_bd.strftime('%d/%m/%Y %H:%M')} ({backups[0][1]})"
    except Exception:
        pass

_hadr_role = next((r[2] for r in db_cfg if r[1] == "HADR_ROLE"), "STANDARD")
_hadr_str  = "Não configurado" if "STANDARD" in str(_hadr_role).upper() else _hadr_role

resumo = [
    ["Versão",             ambiente["versao"]],
    ["Fix Pack",           ambiente["fixpack"]],
    ["Tablespaces",        f"{len(tablespaces)} encontrados"],
    ["Tablespace crítico", _tbsp_crit_str],
    ["Tabelas",            str(len(tabelas))],
    ["Conexões ativas",    str(len(conexoes))],
    ["Último backup",      _ult_backup],
    ["HADR",               _hadr_str],
    ["Fragmentação",       f"{_max_frag:.0f}% ({_frag_label})"],
    ["Log utilizado",      f"{log_util['pct']:.2f}% ({fmt_kb(log_util['usado_kb'])})"],
]
resumo_t = Table(
    [[resumo[i], resumo[i+1]] for i in range(0, len(resumo), 2)],
    colWidths=[PAGE_W/2, PAGE_W/2]
)
inner_style = TableStyle([
    ("FONTSIZE",     (0,0), (-1,-1), 8),
    ("FONTNAME",     (0,0), (-1,-1), "Helvetica"),
    ("GRID",         (0,0), (-1,-1), 0.4, COR_BORDA),
    ("ROWBACKGROUNDS",(0,0),(-1,-1), [COR_CINZA, colors.white]),
    ("TOPPADDING",   (0,0), (-1,-1), 5),
    ("BOTTOMPADDING",(0,0), (-1,-1), 5),
    ("LEFTPADDING",  (0,0), (-1,-1), 6),
])

def mini_kv(pair):
    return Table([[f"{pair[0]}:", pair[1]]], colWidths=[4.5*cm, 4*cm],
                 style=TableStyle([
                     ("FONTSIZE",(0,0),(-1,-1),8),
                     ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
                     ("FONTNAME",(1,0),(-1,-1),"Helvetica"),
                     ("TOPPADDING",(0,0),(-1,-1),4),
                     ("BOTTOMPADDING",(0,0),(-1,-1),4),
                     ("LEFTPADDING",(0,0),(-1,-1),5),
                 ]))

cards_data = [[mini_kv(resumo[i]), mini_kv(resumo[i+1])] for i in range(0, len(resumo), 2)]
cards = Table(cards_data, colWidths=[PAGE_W/2, PAGE_W/2])
cards.setStyle(TableStyle([
    ("GRID", (0,0),(-1,-1), 0.4, COR_BORDA),
    ("ROWBACKGROUNDS",(0,0),(-1,-1),[COR_CINZA, colors.white]),
    ("TOPPADDING",(0,0),(-1,-1),0),
    ("BOTTOMPADDING",(0,0),(-1,-1),0),
]))
story.append(cards)
story.append(Spacer(1, 0.5*cm))

# ── 1. Visão Geral ───────────────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("1. Visão Geral do Ambiente"),
    Spacer(1, 0.25*cm),
    kv_table([
        ("Versão DB2",       ambiente["versao"]),
        ("Fix Pack",         ambiente["fixpack"]),
        ("Plataforma",       ambiente["plataforma"]),
        ("Instância",        ambiente["instancia"]),
        ("Banco de Dados",   ambiente["banco"]),
        ("Diretório Install",ambiente["instalacao"]),
        ("Release Code",     ambiente["release"]),
    ]),
    Spacer(1, 0.4*cm),
]))

# ── 2. Configuração do Banco ─────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("2. Configuração do Banco (DB CFG)"),
    Spacer(1, 0.25*cm),
    kv_table([(r[0], r[2]) for r in db_cfg]),
    Spacer(1, 0.4*cm),
]))

# ── 3. Tablespaces ───────────────────────────────────────────────────────────
story.append(section_header("3. Tablespaces"))
story.append(Spacer(1, 0.25*cm))

tbsp_header = ["Nome", "Tipo", "Estado", "Conteúdo", "Total", "Usado", "Livre", "% Uso", "Page", "Auto Resize"]
tbsp_data = [tbsp_header]
tbsp_style = base_table_style()

for i, t in enumerate(tablespaces, start=1):
    nome, tipo, estado, cont, total, usado, livre, pct, page, cont_n, auto = t
    pct_str = f"{pct:.2f}%" if pct >= 0 else "N/A"
    tbsp_data.append([
        nome, tipo, estado, cont,
        fmt_kb(total), fmt_kb(usado), fmt_kb(livre),
        pct_str, f"{page//1024}K", auto
    ])
    if pct >= 0:
        cor = cor_pct(pct)
        tbsp_style.add("BACKGROUND", (7, i), (7, i), cor)
        tbsp_style.add("TEXTCOLOR",  (7, i), (7, i), colors.white)
        tbsp_style.add("FONTNAME",   (7, i), (7, i), "Helvetica-Bold")

col_tbsp = [3.5*cm,1.2*cm,1.6*cm,2*cm,2*cm,2*cm,1.8*cm,1.4*cm,1*cm,2.5*cm]
tbsp_t = Table(tbsp_data, colWidths=col_tbsp, repeatRows=1)
tbsp_t.setStyle(tbsp_style)
story.append(tbsp_t)
story.append(Paragraph("Verde < 70%  ·  Amarelo 70–90%  ·  Vermelho > 90%", s_note))
story.append(Spacer(1, 0.4*cm))

# ── 4. Buffer Pools ──────────────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("4. Buffer Pools"),
    Spacer(1, 0.25*cm),
]))
bp_header = ["Nome", "Páginas", "Page Size", "Block Pages", "Hit Ratio Total", "Hit Ratio Data", "Hit Ratio Index"]
bp_data = [bp_header]
for bp in buffer_pools:
    bp_data.append([bp[0], bp[1], f"{bp[2]//1024}K", str(bp[3]), bp[4], bp[5], bp[6]])
bp_t = Table(bp_data, colWidths=[3.5*cm,2.5*cm,1.8*cm,2.2*cm,2.5*cm,2.5*cm,2*cm], repeatRows=1)
bp_t.setStyle(base_table_style())
story.append(bp_t)
story.append(Paragraph("Hit ratios N/D: snap ainda não coletado após reinicialização.", s_note))
story.append(Spacer(1, 0.4*cm))

# ── 5. Utilização do Log ─────────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("5. Utilização do Log"),
    Spacer(1, 0.25*cm),
    kv_table([
        ("Utilização atual",        f"{log_util['pct']:.2f}%"),
        ("Log usado",               fmt_kb(log_util['usado_kb'])),
        ("Log disponível",          fmt_kb(log_util['disponivel_kb'])),
        ("Pico de uso registrado",  fmt_kb(log_util['pico_kb'])),
        ("Primary logs",            "16 × 4 MB = 64 MB"),
        ("Secondary logs",          "22 × 4 MB = 88 MB"),
        ("Capacidade total logs",   "152 MB"),
    ]),
    Spacer(1, 0.4*cm),
]))

# ── 6. Objetos do Banco ──────────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("6. Objetos do Banco"),
    Spacer(1, 0.25*cm),
]))
obj_header = ["Tipo de Objeto", "Quantidade"]
obj_data = [obj_header] + [[o[0], str(o[1])] for o in objetos]
obj_t = Table(obj_data, colWidths=[10*cm, 7*cm])
obj_t.setStyle(base_table_style())
story.append(obj_t)
story.append(Spacer(1, 0.4*cm))

# ── 7. Tabelas e Tamanho ─────────────────────────────────────────────────────
story.append(section_header("7. Tabelas – Tamanho e Estatísticas"))
story.append(Spacer(1, 0.25*cm))
tab_header = ["Schema", "Tabela", "Linhas", "Pág. Usadas", "Pág. Aloc.", "Overflow", "Tamanho", "Último RUNSTATS"]
tab_data = [tab_header]
for t in tabelas:
    tab_data.append([t[0], t[1], str(t[2]), str(t[3]), str(t[4]), str(t[5]), t[7], t[8]])
tab_t = Table(tab_data, colWidths=[2.5*cm,2.5*cm,1.5*cm,2.2*cm,2.2*cm,1.8*cm,1.8*cm,2.5*cm], repeatRows=1)
tab_t.setStyle(base_table_style())
story.append(tab_t)
story.append(Spacer(1, 0.4*cm))

# ── 8. Fragmentação ──────────────────────────────────────────────────────────
story.append(section_header("8. Fragmentação de Tabelas"))
story.append(Spacer(1, 0.25*cm))
frag_header = ["Schema", "Tabela", "Linhas", "Pág. Usadas", "Pág. Aloc.", "Overflow", "% Frag.", "Status"]
frag_data = [frag_header]
frag_style = base_table_style()
for i, t in enumerate(tabelas, start=1):
    pct = t[6]
    if pct == 0:   status = "Ótimo"
    elif pct < 20: status = "Bom"
    elif pct < 40: status = "Atenção"
    else:          status = "Crítico"
    frag_data.append([t[0], t[1], str(t[2]), str(t[3]), str(t[4]), str(t[5]), f"{pct:.2f}%", status])
    cor = cor_frag(pct)
    frag_style.add("BACKGROUND", (7,i), (7,i), cor)
    frag_style.add("TEXTCOLOR",  (7,i), (7,i), colors.white)
    frag_style.add("FONTNAME",   (7,i), (7,i), "Helvetica-Bold")

frag_t = Table(frag_data, colWidths=[2.5*cm,2.5*cm,1.5*cm,2.2*cm,2.2*cm,1.8*cm,1.8*cm,2.5*cm], repeatRows=1)
frag_t.setStyle(frag_style)
story.append(frag_t)
story.append(Spacer(1, 0.4*cm))

# ── 9. Índices ───────────────────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("9. Índices"),
    Spacer(1, 0.25*cm),
]))
idx_header = ["Nome do Índice", "Schema", "Tabela", "Colunas", "Tipo", "Folhas", "Níveis", "% Cluster"]
idx_data = [idx_header]
for ix in indices:
    idx_data.append([ix[0][:20], ix[1], ix[2], ix[3], ix[4], str(ix[5]), str(ix[6]), f"{ix[7]}%"])
idx_style = base_table_style()
idx_t = Table(idx_data, colWidths=[3.8*cm,2.2*cm,2.2*cm,1.8*cm,2.2*cm,1.5*cm,1.5*cm,1.8*cm], repeatRows=1)
idx_t.setStyle(idx_style)
story.append(idx_t)
story.append(Spacer(1, 0.4*cm))

# ── 10. Segurança – Autoridades ──────────────────────────────────────────────
story.append(PageBreak())
story.append(section_header("10. Segurança – Autoridades no Banco"))
story.append(Spacer(1, 0.25*cm))

# tuple pos: grantee(0),tipo(1),dbadm(2),secadm(3),dataaccess(4),accessctrl(5),
#            connect(6),createtab(7),bindadd(8),implschema(9),load(10),
#            nofence(11),sqladm(12),wlmadm(13),explain(14)
AUTH_IDX   = [2,  3,    4,    5,    6,      7,         10,   12,      13,      14]
auth_cols  = ["DB Adm","Sec Adm","Data Acc","Acc Ctrl","Connect","CreateTab","Load","SQL Adm","WLM Adm","Explain"]
auth_header = ["Usuário","Tipo"] + auth_cols
auth_data = [auth_header]
auth_style = base_table_style()

for i, u in enumerate(usuarios_db, start=1):
    vals = [u[idx] for idx in AUTH_IDX]
    row = [u[0], u[1]] + [yn_cell(v) for v in vals]
    auth_data.append(row)
    for j, v in enumerate(vals, start=2):
        c = COR_VERDE if v == "S" else COR_VERMELHO
        auth_style.add("BACKGROUND",(j,i),(j,i),c)
        auth_style.add("TEXTCOLOR", (j,i),(j,i),colors.white)
        auth_style.add("FONTNAME",  (j,i),(j,i),"Helvetica-Bold")

# 2.5 + 1.5 + 10×1.3 = 17.0 cm
auth_cw = [2.5*cm, 1.5*cm] + [1.3*cm]*10
auth_t = Table(auth_data, colWidths=auth_cw, repeatRows=1)
auth_t.setStyle(auth_style)
story.append(auth_t)
story.append(Spacer(1, 0.4*cm))

# ── 11. Segurança – Permissões por Tabela ────────────────────────────────────
story.append(KeepTogether([
    section_header("11. Segurança – Permissões por Tabela"),
    Spacer(1, 0.25*cm),
]))
perm_cols = ["SELECT","INSERT","UPDATE","DELETE","ALTER","INDEX","REF","CONTROL"]
perm_header = ["Usuário","Tipo","Schema","Tabela"] + perm_cols
perm_data = [perm_header]
perm_style = base_table_style()

for i, p in enumerate(perm_tabela, start=1):
    vals = list(p[4:])
    perm_data.append([p[0],p[1],p[2],p[3]] + vals)
    for j, v in enumerate(vals, start=4):
        c = COR_VERDE if v in ("G","S") else COR_VERMELHO
        perm_style.add("BACKGROUND",(j,i),(j,i),c)
        perm_style.add("TEXTCOLOR", (j,i),(j,i),colors.white)
        perm_style.add("FONTNAME",  (j,i),(j,i),"Helvetica-Bold")

perm_cw = [2.5*cm,1.6*cm,2*cm,2*cm] + [1.24*cm]*8
perm_t = Table(perm_data, colWidths=perm_cw, repeatRows=1)
perm_t.setStyle(perm_style)
story.append(perm_t)
story.append(Paragraph("G = WITH GRANT OPTION  ·  S = permissão direta  ·  N = sem permissão", s_note))
story.append(Spacer(1, 0.4*cm))

# ── 12. Backup e Recuperação ─────────────────────────────────────────────────
story.append(KeepTogether([
    section_header("12. Backup e Recuperação"),
    Spacer(1, 0.25*cm),
]))
bk_header = ["Operação","Subtipo","Início","Fim","Duração","Local","Status"]
bk_data = [bk_header]
bk_style = base_table_style()
for i, b in enumerate(backups, start=1):
    inicio = datetime.strptime(b[2], "%Y%m%d%H%M%S")
    fim    = datetime.strptime(b[3], "%Y%m%d%H%M%S")
    dur    = int((fim - inicio).total_seconds())
    bk_data.append([b[0], b[1], fmt_ts(b[2]), fmt_ts(b[3]), f"{dur}s", b[4], b[5]])
    c = COR_VERDE if b[5] == "Sucesso" else COR_VERMELHO
    bk_style.add("BACKGROUND",(6,i),(6,i),c)
    bk_style.add("TEXTCOLOR", (6,i),(6,i),colors.white)
    bk_style.add("FONTNAME",  (6,i),(6,i),"Helvetica-Bold")

bk_t = Table(bk_data, colWidths=[2.2*cm,1.8*cm,3.5*cm,3.5*cm,1.5*cm,2.5*cm,2*cm], repeatRows=1)
bk_t.setStyle(bk_style)
story.append(bk_t)
story.append(Spacer(1, 0.4*cm))

# ── 13. Alta Disponibilidade (HADR) ──────────────────────────────────────────
_hadr_sync    = _cfg_map.get("hadr_syncmode",    "N/D")
_hadr_lhost   = _cfg_map.get("hadr_local_host",  "(não definido)")
_hadr_rhost   = _cfg_map.get("hadr_remote_host", "(não definido)")
_hadr_timeout = _cfg_map.get("hadr_timeout",     "120")
_hadr_spool   = _cfg_map.get("hadr_spool_limit", "AUTOMATIC")
_hadr_replay  = _cfg_map.get("hadr_replay_delay","0")
_hadr_compress= _cfg_map.get("logarchcompr1",    "OFF")
_hadr_ativo   = "STANDARD" not in str(_hadr_role).upper()
_hadr_nota    = (f"HADR ativo em modo {_hadr_role}." if _hadr_ativo
                 else "HADR não está ativo. O banco opera em modo STANDARD sem standby.")

story.append(KeepTogether([
    section_header("13. Alta Disponibilidade (HADR)"),
    Spacer(1, 0.25*cm),
    kv_table([
        ("Status HADR",           _hadr_str),
        ("Role do banco",         _hadr_role),
        ("Sync Mode configurado", f"{_hadr_sync} {'(inativo)' if not _hadr_ativo else ''}".strip()),
        ("Host local",            _hadr_lhost or "(não definido)"),
        ("Host remoto",           _hadr_rhost or "(não definido)"),
        ("Timeout HADR",          f"{_hadr_timeout} segundos"),
        ("Spool limit",           _hadr_spool),
        ("Replay delay",          f"{_hadr_replay} segundos"),
        ("Compressão de log",     _hadr_compress),
    ]),
    Paragraph(_hadr_nota, s_note),
    Spacer(1, 0.4*cm),
]))

# ── 14. Conexões Ativas ──────────────────────────────────────────────────────
story.append(section_header("14. Conexões Ativas"))
story.append(Spacer(1, 0.25*cm))

total_con = len(conexoes)
sys_con   = sum(1 for c in conexoes if c[3] == "Sistema")
app_con   = sum(1 for c in conexoes if c[3] == "Aplicação")
tool_con  = sum(1 for c in conexoes if c[3] == "Ferramenta")
exec_con  = sum(1 for c in conexoes if c[2] == "UOWEXEC")
wait_con  = sum(1 for c in conexoes if c[2] == "UOWWAIT")

story.append(kv_table([
    ("Total de conexões",       str(total_con)),
    ("Processos de sistema",    str(sys_con)),
    ("Aplicações (JCC)",        str(app_con)),
    ("Ferramentas (DBeaver)",   str(tool_con)),
    ("Em execução (UOWEXEC)",   str(exec_con)),
    ("Aguardando (UOWWAIT)",    str(wait_con)),
], col1=7*cm, col2=10*cm))
story.append(Spacer(1, 0.25*cm))

conn_header = ["Aplicação","Auth ID","Status","Categoria"]
conn_data = [conn_header]
conn_style = base_table_style()
status_colors = {"CONNECTED": COR_VERDE, "UOWEXEC": COR_AZUL_CLR, "UOWWAIT": COR_AMARELO}
for i, c in enumerate(conexoes, start=1):
    conn_data.append(list(c))
    cor = status_colors.get(c[2], COR_CINZA)
    conn_style.add("BACKGROUND",(2,i),(2,i),cor)
    conn_style.add("TEXTCOLOR", (2,i),(2,i),colors.white)
    conn_style.add("FONTNAME",  (2,i),(2,i),"Helvetica-Bold")

conn_t = Table(conn_data, colWidths=[5.5*cm,3*cm,3*cm,5.5*cm], repeatRows=1)
conn_t.setStyle(conn_style)
story.append(conn_t)
story.append(Spacer(1, 0.4*cm))

# ── Rodapé ───────────────────────────────────────────────────────────────────
story.append(HRFlowable(width="100%", thickness=0.5, color=COR_BORDA))
story.append(Spacer(1, 0.2*cm))
story.append(Paragraph(
    f"Assessment gerado automaticamente via MCP DB2 LUW  ·  {GERADO_EM}  ·  DB2 v12.1.4.0 / TESTDB",
    s_note
))

# ── Geração ──────────────────────────────────────────────────────────────────
OUTPUT = "/Users/jorgehbchaves/Dev/db2/assessment_db2.pdf"
doc = SimpleDocTemplate(OUTPUT, pagesize=A4,
    rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
doc.build(story)
print(f"PDF gerado: {OUTPUT}")
