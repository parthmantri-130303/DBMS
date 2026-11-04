import os
import sys
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import mysql.connector
from backend.config import config

def run_queries():
    conn = mysql.connector.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME
    )
    cursor = conn.cursor(dictionary=True)

    with open("database/queries.sql", "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern matches each query section
    query_blocks = list(re.finditer(
        r'--\s*(QUERY\s+\d+:\s+[^\n]+)\s*\n((?:--[^\n]*\n)*)--\s*=+\s*\n(.*?)(?=(?:--\s*=+\s*\n--\s*QUERY|\Z))',
        content,
        re.DOTALL
    ))

    doc = [
        "# DBMS Course Demonstration Queries & Live Execution Outputs\n\n",
        f"**Database**: `{config.DB_NAME}` (MySQL 8.0 on port {config.DB_PORT})  \n",
        "**Executed**: All queries executed against live seeded database state.  \n\n",
        "---\n\n"
    ]

    for m in query_blocks:
        title = m.group(1).strip()
        comment_header = m.group(2).strip()
        raw_sql = m.group(3).strip()

        # Extract "Demonstrates:" line(s) from comment header
        demonstrates_lines = []
        for line in comment_header.splitlines():
            clean_l = line.lstrip("-").strip()
            if clean_l.startswith("Demonstrates:"):
                demonstrates_lines.append(clean_l)
            elif demonstrates_lines and clean_l and not clean_l.startswith("="):
                demonstrates_lines.append(clean_l)
        demonstrates = " ".join(demonstrates_lines)

        # Extract pure SQL
        sql_lines = [l for l in raw_sql.splitlines() if not l.strip().startswith("--")]
        sql_statement = "\n".join(sql_lines).strip()
        if not sql_statement:
            continue

        doc.append(f"## {title}\n\n")
        if demonstrates:
            doc.append(f"*{demonstrates}*\n\n")
        doc.append("### SQL Statement\n\n```sql\n" + sql_statement + "\n```\n\n")

        # Execute
        try:
            cursor.execute(sql_statement)
            rows = cursor.fetchall()
            doc.append(f"### Live Execution Output ({len(rows)} row(s) returned)\n\n")
            if not rows:
                doc.append("*No rows returned for current dataset filters.*\n\n")
            else:
                headers = list(rows[0].keys())
                doc.append("| " + " | ".join(headers) + " |\n")
                doc.append("| " + " | ".join(["---"] * len(headers)) + " |\n")
                for r in rows[:15]:
                    vals = [str(r.get(h) if r.get(h) is not None else "NULL").replace("\n", " ") for h in headers]
                    doc.append("| " + " | ".join(vals) + " |\n")
                if len(rows) > 15:
                    doc.append(f"\n*... {len(rows) - 15} additional rows truncated for display brevity.*\n")
                doc.append("\n")
        except Exception as e:
            doc.append(f"**Execution Error**: `{e}`\n\n")

        doc.append("---\n\n")

    cursor.close()
    conn.close()

    os.makedirs("docs/submission", exist_ok=True)
    with open("docs/submission/queries_with_output.md", "w", encoding="utf-8") as f:
        f.writelines(doc)

    print("Successfully wrote docs/submission/queries_with_output.md")

if __name__ == "__main__":
    run_queries()
