import os
import re

def audit_sql():
    suspicious = []
    total_sql_lines = 0
    pattern_fstring = re.compile(r'f["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM).*\{.*\}', re.IGNORECASE)
    pattern_pct_format = re.compile(r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM).*["\']\s*%', re.IGNORECASE)
    pattern_dot_format = re.compile(r'["\'].*(?:SELECT|INSERT|UPDATE|DELETE|FROM).*["\']\.format\(', re.IGNORECASE)

    for root, _, files in os.walk('backend'):
        for f in files:
            if f.endswith('.py') and 'tests' not in root:
                path = os.path.join(root, f)
                with open(path, 'r', encoding='utf-8') as src:
                    lines = src.readlines()
                for idx, line in enumerate(lines, 1):
                    stripped = line.strip()
                    if any(k in stripped.upper() for k in ['SELECT ', 'INSERT INTO ', 'UPDATE ', 'DELETE FROM ']):
                        total_sql_lines += 1
                        if pattern_fstring.search(stripped) or pattern_pct_format.search(stripped) or pattern_dot_format.search(stripped):
                            suspicious.append((path, idx, stripped))

    print(f"Total SQL statement locations surveyed: {total_sql_lines}")
    print(f"Suspicious unparameterized interpolations found: {len(suspicious)}")
    for p, idx, l in suspicious:
        print(f"  {p}:{idx} -> {l}")
    return len(suspicious) == 0

if __name__ == '__main__':
    audit_sql()

