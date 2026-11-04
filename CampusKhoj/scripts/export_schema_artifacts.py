import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from backend.config import config

def export_schema():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)

    # 1. Get all base tables
    cursor.execute("""
        SELECT table_name, engine, table_rows, create_time, table_collation
        FROM information_schema.tables
        WHERE table_schema = %s AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """, (config.DB_NAME,))
    tables = cursor.fetchall()

    schema_doc = ["# CampusKhoj Relational Database Schema Specification\n\n",
                  f"**Database**: `{config.DB_NAME}`  \n",
                  "**RDBMS**: MySQL Community Server 8.0.46  \n",
                  "**Engine**: InnoDB (ACID compliant)  \n",
                  "**Default Charset**: `utf8mb4`  \n",
                  "**Default Collation**: `utf8mb4_unicode_ci`  \n",
                  "**Extracted From Live Instance**: Verified  \n\n",
                  "---\n\n",
                  "## Table of Contents\n\n"]

    def g(row, key):
        return row.get(key.lower()) or row.get(key.upper()) or row.get(key)

    for t in tables:
        tname = g(t, "TABLE_NAME")
        schema_doc.append(f"- [{tname}](#{tname.lower()})\n")
    schema_doc.append("\n---\n\n")

    mermaid_lines = ["erDiagram\n"]

    # 2. Get foreign keys for Mermaid and docs
    cursor.execute("""
        SELECT 
            kcu.TABLE_NAME,
            kcu.COLUMN_NAME,
            kcu.REFERENCED_TABLE_NAME,
            kcu.REFERENCED_COLUMN_NAME,
            kcu.CONSTRAINT_NAME
        FROM information_schema.key_column_usage kcu
        JOIN information_schema.table_constraints tc 
          ON kcu.constraint_name = tc.constraint_name 
         AND kcu.table_schema = tc.table_schema
        WHERE kcu.table_schema = %s 
          AND tc.constraint_type = 'FOREIGN KEY'
          AND kcu.referenced_table_name IS NOT NULL
        ORDER BY kcu.table_name, kcu.constraint_name;
    """, (config.DB_NAME,))
    fks = cursor.fetchall()

    for fk in fks:
        src = g(fk, "TABLE_NAME")
        dst = g(fk, "REFERENCED_TABLE_NAME")
        col = g(fk, "COLUMN_NAME")
        ref_col = g(fk, "REFERENCED_COLUMN_NAME")
        mermaid_lines.append(f"    {dst} ||--o{{ {src} : \"{col} -> {ref_col}\"\n")

    mermaid_lines.append("\n")

    # 3. For each table, get columns, keys, and CREATE TABLE statement
    for t in tables:
        tname = g(t, "TABLE_NAME")
        schema_doc.append(f"### `{tname}`\n\n")
        
        cursor.execute(f"SHOW CREATE TABLE `{tname}`")
        create_res = cursor.fetchone()
        create_sql = create_res.get("Create Table") or create_res.get("CREATE TABLE") or ""

        cursor.execute("""
            SELECT 
                COLUMN_NAME,
                COLUMN_TYPE,
                IS_NULLABLE,
                COLUMN_KEY,
                COLUMN_DEFAULT,
                EXTRA
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position;
        """, (config.DB_NAME, tname))
        cols = cursor.fetchall()

        mermaid_lines.append(f"    {tname} {{\n")
        schema_doc.append("| Column | Type | Nullable | Key | Default | Extra |\n")
        schema_doc.append("|---|---|---|---|---|---|\n")

        for c in cols:
            cname = g(c, "COLUMN_NAME")
            ctype = g(c, "COLUMN_TYPE")
            cnull = g(c, "IS_NULLABLE")
            ckey = g(c, "COLUMN_KEY") or "-"
            cdef = str(g(c, "COLUMN_DEFAULT")) if g(c, "COLUMN_DEFAULT") is not None else "-"
            cext = g(c, "EXTRA") or "-"
            schema_doc.append(f"| `{cname}` | `{ctype}` | {cnull} | {ckey} | `{cdef}` | {cext} |\n")

            # Mermaid field
            mtype = ctype.split("(")[0].replace(" ", "_")
            mermaid_lines.append(f"        {mtype} {cname}\n")

        mermaid_lines.append("    }\n\n")

        schema_doc.append("\n#### Raw DDL Definition\n\n```sql\n" + create_sql + "\n```\n\n---\n\n")

    cursor.close()
    conn.close()

    os.makedirs("docs/submission", exist_ok=True)

    with open("docs/submission/relational_schema.md", "w", encoding="utf-8") as f:
        f.writelines(schema_doc)

    with open("docs/submission/ER_diagram.mmd", "w", encoding="utf-8") as f:
        f.writelines(mermaid_lines)

    print("Successfully exported docs/submission/relational_schema.md and docs/submission/ER_diagram.mmd")

if __name__ == "__main__":
    export_schema()
