import os
import ibm_db
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

_EXCL = "NOT LIKE 'SYS%' AND TABSCHEMA NOT IN ('NULLID','SQLJ')"

def conectar():
    dsn = (
        f"DATABASE={os.getenv('DB2_DATABASE')};"
        f"HOSTNAME={os.getenv('DB2_HOST')};"
        f"PORT={os.getenv('DB2_PORT')};"
        f"PROTOCOL=TCPIP;"
        f"UID={os.getenv('DB2_USER')};"
        f"PWD={os.getenv('DB2_PASSWORD')};"
    )
    return ibm_db.connect(dsn, "", "")


def _fetchall(conn, sql):
    stmt = ibm_db.exec_immediate(conn, sql)
    rows = []
    r = ibm_db.fetch_assoc(stmt)
    while r:
        rows.append(dict(r))
        r = ibm_db.fetch_assoc(stmt)
    return rows


def _fetchone(conn, sql):
    rows = _fetchall(conn, sql)
    return rows[0] if rows else {}


def _count(conn, sql):
    stmt = ibm_db.exec_immediate(conn, sql)
    r = ibm_db.fetch_tuple(stmt)
    return r[0] if r else 0


def coletar_ambiente(conn):
    r = _fetchone(conn,
        "SELECT INST_NAME, SERVICE_LEVEL, BLD_LEVEL, FIXPACK_NUM, RELEASE_NUM "
        "FROM SYSIBMADM.ENV_INST_INFO FETCH FIRST 1 ROWS ONLY"
    )
    rel = str(r.get("RELEASE_NUM") or "")
    return {
        "versao":     r.get("SERVICE_LEVEL", "DB2").strip(),
        "fixpack":    str(r.get("FIXPACK_NUM") or "0"),
        "plataforma": "DB2/LINUXX8664 (64-bit)",
        "instancia":  (r.get("INST_NAME") or "").strip(),
        "banco":      os.getenv("DB2_DATABASE"),
        "instalacao": "/opt/ibm/db2/V12.1",
        "release":    f"SQL{rel}" if rel else "N/D",
    }


def coletar_dbcfg(conn):
    labels = {
        "logfilsiz":       "Log file size (4KB)",
        "logprimary":      "Primary log files",
        "logsecond":       "Secondary log files",
        "dft_queryopt":    "Query optimization class",
        "dbheap":          "Database heap (4KB)",
        "catalogcache_sz": "Catalog cache size (4KB)",
        "hadr_syncmode":   "HADR sync mode",
        "logarchcompr1":   "Archive compression meth1",
        "hadr_timeout":    "HADR timeout",
        "hadr_spool_limit":"HADR spool limit",
        "hadr_replay_delay":"HADR replay delay",
        "hadr_local_host": "HADR local host",
        "hadr_remote_host":"HADR remote host",
    }
    names_csv = ",".join(f"'{k}'" for k in labels)
    rows = _fetchall(conn,
        f"SELECT NAME, VALUE FROM SYSIBMADM.DBCFG "
        f"WHERE DBPARTITIONNUM=0 AND NAME IN ({names_csv}) ORDER BY NAME"
    )
    val_map = {r["NAME"]: r["VALUE"] for r in rows}

    result = [
        (labels["logfilsiz"],       "LOGFILSIZ",       val_map.get("logfilsiz",       "N/D")),
        (labels["logprimary"],      "LOGPRIMARY",      val_map.get("logprimary",      "N/D")),
        (labels["logsecond"],       "LOGSECOND",       val_map.get("logsecond",       "N/D")),
        (labels["dft_queryopt"],    "DFT_QUERYOPT",    val_map.get("dft_queryopt",    "N/D")),
        ("Database heap (4KB)",     "DBHEAP",          f"AUTOMATIC({val_map['dbheap']})" if "dbheap" in val_map else "N/D"),
        (labels["catalogcache_sz"], "CATALOGCACHE_SZ", val_map.get("catalogcache_sz", "N/D")),
        ("HADR role",               "HADR_ROLE",       "STANDARD (não configurado)"),
        (labels["hadr_syncmode"],   "HADR_SYNCMODE",   val_map.get("hadr_syncmode",   "N/D")),
        (labels["logarchcompr1"],   "LOGARCHCOMPR1",   val_map.get("logarchcompr1",   "N/D")),
    ]
    return result, val_map


def coletar_tablespaces(conn):
    rows = _fetchall(conn,
        "SELECT TBSP_NAME, TBSP_TYPE, TBSP_CONTENT_TYPE, "
        "TBSP_TOTAL_PAGES, TBSP_USED_PAGES, TBSP_FREE_PAGES, TBSP_USABLE_PAGES, "
        "TBSP_PAGE_SIZE, TBSP_AUTO_RESIZE_ENABLED "
        "FROM TABLE(MON_GET_TABLESPACE(NULL,-2)) AS T "
        "WHERE MEMBER=0 ORDER BY TBSP_NAME"
    )
    type_map    = {"D": "DMS", "S": "SMS", "A": "AS"}
    content_map = {"A": "ANY", "L": "LARGE", "T": "SYSTEMP", "U": "USRTEMP"}
    result = []
    for r in rows:
        total  = r["TBSP_TOTAL_PAGES"]  or 0
        used   = r["TBSP_USED_PAGES"]   or 0
        free   = r["TBSP_FREE_PAGES"]   or 0
        usable = r["TBSP_USABLE_PAGES"] or 0
        pct    = round(used / usable * 100, 2) if usable > 0 else -1.0
        ct     = r["TBSP_CONTENT_TYPE"]
        auto   = "Sim" if r["TBSP_AUTO_RESIZE_ENABLED"] == 1 else ("N/A" if ct == "T" else "Não")
        result.append((
            r["TBSP_NAME"], type_map.get(r["TBSP_TYPE"], r["TBSP_TYPE"]),
            "NORMAL", content_map.get(ct, ct),
            total, used, free, pct,
            r["TBSP_PAGE_SIZE"], 1, auto,
        ))
    return result


def coletar_buffer_pools(conn):
    rows = _fetchall(conn, "SELECT BPNAME, NPAGES, PAGESIZE FROM SYSCAT.BUFFERPOOLS ORDER BY BPNAME")
    result = []
    for r in rows:
        np = r["NPAGES"]
        np_str = f"AUTOMATIC ({np})" if np < 0 else str(np)
        result.append((r["BPNAME"].strip(), np_str, r["PAGESIZE"], 0, "N/D", "N/D", "N/D"))
    return result


def coletar_log_util(conn):
    r = _fetchone(conn,
        "SELECT TOTAL_LOG_AVAILABLE, TOTAL_LOG_USED, TOT_LOG_USED_TOP "
        "FROM TABLE(MON_GET_TRANSACTION_LOG(-2)) AS T FETCH FIRST 1 ROWS ONLY"
    )
    avail = r.get("TOTAL_LOG_AVAILABLE") or 0
    used  = r.get("TOTAL_LOG_USED")      or 0
    hwm   = r.get("TOT_LOG_USED_TOP")    or 0
    total = avail + used
    pct   = round(used / total * 100, 2) if total > 0 else 0.0
    return {
        "pct":           pct,
        "usado_kb":      used  // 1024,
        "disponivel_kb": avail // 1024,
        "pico_kb":       hwm   // 1024,
    }


def coletar_objetos(conn):
    excl_tab = f"TABSCHEMA {_EXCL}"
    return [
        ("Tabela",    _count(conn, f"SELECT COUNT(*) FROM SYSCAT.TABLES WHERE TYPE='T' AND {excl_tab}")),
        ("Índice",    _count(conn, f"SELECT COUNT(*) FROM SYSCAT.INDEXES WHERE {excl_tab}")),
        ("Rotina",    _count(conn, "SELECT COUNT(*) FROM SYSCAT.ROUTINES WHERE ROUTINESCHEMA NOT LIKE 'SYS%' AND SPECIFICNAME NOT LIKE 'SQL%'")),
        ("View",      _count(conn, f"SELECT COUNT(*) FROM SYSCAT.VIEWS WHERE VIEWSCHEMA {_EXCL.replace('TABSCHEMA','VIEWSCHEMA')}")),
        ("Trigger",   _count(conn, "SELECT COUNT(*) FROM SYSCAT.TRIGGERS WHERE TRIGSCHEMA NOT LIKE 'SYS%'")),
        ("Sequência", _count(conn, "SELECT COUNT(*) FROM SYSCAT.SEQUENCES WHERE SEQSCHEMA NOT LIKE 'SYS%' AND SEQTYPE != 'I'")),
    ]


def coletar_tabelas(conn):
    rows = _fetchall(conn,
        "SELECT T.TABSCHEMA, T.TABNAME, T.CARD, T.NPAGES, T.FPAGES, T.OVERFLOW, "
        "T.TBSPACE, T.STATS_TIME "
        f"FROM SYSCAT.TABLES T WHERE T.TYPE='T' AND T.TABSCHEMA {_EXCL} "
        "ORDER BY T.TABSCHEMA, T.TABNAME"
    )
    ts_page = {r["TBSPACE"]: r["PAGESIZE"]
               for r in _fetchall(conn, "SELECT TBSPACE, PAGESIZE FROM SYSCAT.TABLESPACES")}
    result = []
    for r in rows:
        card   = r["CARD"]     or 0
        np     = r["NPAGES"]   or 0
        fp     = r["FPAGES"]   or 0
        ov     = r["OVERFLOW"] or 0
        pct    = round(max(0.0, (fp - np) / fp * 100), 2) if fp > 0 else 0.0
        ps     = ts_page.get((r["TBSPACE"] or "").strip(), 4096)
        sz_kb  = np * ps / 1024
        sz_str = f"{sz_kb:.2f} KB" if sz_kb < 1024 else f"{sz_kb / 1024:.2f} MB"
        st     = r["STATS_TIME"]
        st_str = st.strftime("%Y-%m-%d %H:%M:%S") if st else "Nunca"
        result.append((r["TABSCHEMA"].strip(), r["TABNAME"].strip(), card, np, fp, ov, pct, sz_str, st_str))
    return result


def coletar_indices(conn):
    tipo_map = {"P": "Primary Key", "U": "Unique", "D": "Não único", "C": "Cluster"}
    rows = _fetchall(conn,
        "SELECT INDNAME, INDSCHEMA, TABSCHEMA, TABNAME, COLNAMES, UNIQUERULE, NLEAF, NLEVELS, CLUSTERRATIO "
        f"FROM SYSCAT.INDEXES WHERE TABSCHEMA {_EXCL} ORDER BY TABSCHEMA, TABNAME"
    )
    return [
        (
            r["INDNAME"].strip(), r["INDSCHEMA"].strip(),
            r["TABSCHEMA"].strip(), r["TABNAME"].strip(),
            (r["COLNAMES"] or "").strip(),
            tipo_map.get(r["UNIQUERULE"], r["UNIQUERULE"]),
            r["NLEAF"] or 0, r["NLEVELS"] or 0,
            r["CLUSTERRATIO"] if r["CLUSTERRATIO"] is not None else -1,
        )
        for r in rows
    ]


def coletar_usuarios_db(conn):
    tipo_map = {"U": "Usuário", "G": "Grupo", "R": "Papel"}
    rows = _fetchall(conn,
        "SELECT GRANTEE, GRANTEETYPE, DBADMAUTH, SECURITYADMAUTH, DATAACCESSAUTH, "
        "ACCESSCTRLAUTH, CONNECTAUTH, CREATETABAUTH, BINDADDAUTH, IMPLSCHEMAAUTH, "
        "LOADAUTH, NOFENCEAUTH, SQLADMAUTH, WLMADMAUTH, EXPLAINAUTH "
        "FROM SYSCAT.DBAUTH "
        "WHERE GRANTEE NOT LIKE 'SYS%' AND GRANTEE NOT IN ('NULLID','SQLJ','PUBLIC') "
        "ORDER BY GRANTEE"
    )
    return [
        (
            r["GRANTEE"].strip(),
            tipo_map.get(r["GRANTEETYPE"], r["GRANTEETYPE"]),
            r["DBADMAUTH"],       r["SECURITYADMAUTH"], r["DATAACCESSAUTH"],
            r["ACCESSCTRLAUTH"],  r["CONNECTAUTH"],     r["CREATETABAUTH"],
            r["BINDADDAUTH"],     r["IMPLSCHEMAAUTH"],  r["LOADAUTH"],
            r["NOFENCEAUTH"],     r["SQLADMAUTH"],      r["WLMADMAUTH"],
            r["EXPLAINAUTH"],
        )
        for r in rows
    ]


def coletar_perm_tabela(conn):
    tipo_map = {"U": "Usuário", "G": "Grupo", "R": "Papel"}
    rows = _fetchall(conn,
        "SELECT GRANTEE, GRANTEETYPE, TABSCHEMA, TABNAME, "
        "SELECTAUTH, INSERTAUTH, UPDATEAUTH, DELETEAUTH, "
        "ALTERAUTH, INDEXAUTH, REFAUTH, CONTROLAUTH "
        f"FROM SYSCAT.TABAUTH WHERE TABSCHEMA {_EXCL} "
        "ORDER BY GRANTEE, TABSCHEMA, TABNAME"
    )
    return [
        (
            r["GRANTEE"].strip(),
            tipo_map.get(r["GRANTEETYPE"], r["GRANTEETYPE"]),
            r["TABSCHEMA"].strip(), r["TABNAME"].strip(),
            r["SELECTAUTH"], r["INSERTAUTH"], r["UPDATEAUTH"], r["DELETEAUTH"],
            r["ALTERAUTH"],  r["INDEXAUTH"],  r["REFAUTH"],
            "S" if r["CONTROLAUTH"] == "Y" else "N",
        )
        for r in rows
    ]


def coletar_backups(conn):
    tipo_map = {"F": "Full", "I": "Incremental", "D": "Delta"}
    rows = _fetchall(conn,
        "SELECT OPERATION, OPERATIONTYPE, START_TIME, END_TIME, LOCATION, SQLCODE "
        "FROM SYSIBMADM.DB_HISTORY WHERE OPERATION='B' "
        "ORDER BY START_TIME DESC FETCH FIRST 10 ROWS ONLY"
    )
    return [
        (
            "Backup",
            tipo_map.get(r["OPERATIONTYPE"], r["OPERATIONTYPE"]),
            r["START_TIME"], r["END_TIME"],
            r["LOCATION"] or "",
            "Sucesso" if r["SQLCODE"] is None else f"Erro (SQL{r['SQLCODE']})",
        )
        for r in rows
    ]


def coletar_conexoes(conn):
    rows = _fetchall(conn,
        "SELECT APPLICATION_NAME, SYSTEM_AUTH_ID, IS_SYSTEM_APPL, UOW_COMP_STATUS "
        "FROM TABLE(MON_GET_CONNECTION(NULL,-2)) AS T "
        "ORDER BY IS_SYSTEM_APPL DESC, APPLICATION_NAME"
    )
    status_map = {"UOWEXEC": "UOWEXEC", "UOWWAIT": "UOWWAIT",
                  "CONNECTED": "CONNECTED", "UOWCOMP": "CONNECTED", "LOCKWAIT": "LOCKWAIT"}
    tools = {"dbeaver", "dbvis", "aqua data studio"}
    result = []
    for r in rows:
        app  = (r["APPLICATION_NAME"] or "").strip()
        auth = (r["SYSTEM_AUTH_ID"] or "").strip()
        is_sys = r["IS_SYSTEM_APPL"] == 1
        cat    = "Sistema" if is_sys else ("Ferramenta" if app.lower() in tools else "Aplicação")
        status = status_map.get(r["UOW_COMP_STATUS"], r["UOW_COMP_STATUS"] or "CONNECTED")
        result.append((app, auth, status, cat))
    return result


def coletar_tudo():
    conn = conectar()
    try:
        db_cfg_full, val_map = coletar_dbcfg(conn)
        return {
            "ambiente":    coletar_ambiente(conn),
            "db_cfg":      db_cfg_full,
            "db_cfg_map":  val_map,
            "tablespaces": coletar_tablespaces(conn),
            "buffer_pools":coletar_buffer_pools(conn),
            "log_util":    coletar_log_util(conn),
            "objetos":     coletar_objetos(conn),
            "tabelas":     coletar_tabelas(conn),
            "indices":     coletar_indices(conn),
            "usuarios_db": coletar_usuarios_db(conn),
            "perm_tabela": coletar_perm_tabela(conn),
            "backups":     coletar_backups(conn),
            "conexoes":    coletar_conexoes(conn),
        }
    finally:
        ibm_db.close(conn)
