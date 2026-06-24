# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project does

Two Python scripts generate formatted PDF reports about an IBM DB2 LUW environment using `reportlab`. Data is collected from the live database via the `db2-luw` MCP server, then embedded as hardcoded Python variables in each script before the PDF is built.

- **`gerar_relatorio_fragmentacao.py`** — Fragmentation-focused report: table fragmentation status, user authorities, table permissions, and last backup.
- **`gerar_assessment.py`** — Full environment assessment: DB2 version/config, tablespaces, buffer pools, log utilization, objects, tables, fragmentation, indexes, security, backup history, HADR status, and active connections.

## Running the scripts

```bash
python gerar_relatorio_fragmentacao.py   # → relatorio_fragmentacao.pdf
python gerar_assessment.py               # → assessment_db2.pdf
```

Requires `reportlab` (`pip install reportlab`).

## Workflow for updating reports

1. Query the live DB2 database using the `mcp__db2-luw__*` MCP tools (read-only SELECT queries only).
2. Update the hardcoded data variables at the top of the relevant script with the freshly collected values.
3. Run the script to regenerate the PDF.

## DB2 environment

- **Instance:** `db2inst1`
- **Database:** `TESTDB`
- **Version:** DB2 v12.1.4.0 (Linux x86-64, 64-bit)
- **Install path:** `/opt/ibm/db2/V12.1`

## MCP tools available

The `db2-luw` MCP server exposes read-only access to TESTDB:

| Tool | Purpose |
|------|---------|
| `mcp__db2-luw__execute_query` | Run any SELECT query |
| `mcp__db2-luw__list_schemas` | List schemas (supports LIKE filter) |
| `mcp__db2-luw__list_tables` | List tables in a schema |
| `mcp__db2-luw__describe_table` | Column details for a table |
| `mcp__db2-luw__list_indexes` | List indexes |
| `mcp__db2-luw__list_views` | List views |
| `mcp__db2-luw__get_table_constraints` | List constraints |

## PDF structure (`gerar_assessment.py`)

Sections in order: cover page → executive summary cards → 1. Environment Overview → 2. DB CFG → 3. Tablespaces → 4. Buffer Pools → 5. Log Utilization → 6. Object Counts → 7. Tables & Statistics → 8. Fragmentation → 9. Indexes → 10. Security (authorities) → 11. Security (table permissions) → 12. Backup & Recovery → 13. HADR → 14. Active Connections.

## Color coding conventions

- **Fragmentation:** Green 0%, Light-green <20%, Yellow 20–40%, Red ≥40%
- **Tablespace usage:** Green <70%, Yellow 70–90%, Red >90%
- **Permissions (G/S/N):** Green = granted, Red = not granted
- **Connection status:** Green = CONNECTED, Blue = UOWEXEC, Yellow = UOWWAIT
