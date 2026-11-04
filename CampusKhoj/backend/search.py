import re

def escape_like(s: str) -> str:
    """Escapes SQL LIKE wildcards (% and _) and backslashes."""
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

def build_search_clause(
    table_prefix: str,
    query_str: str,
    include_location: bool = False,
    loc_prefix: str = "loc"
) -> tuple[str | None, list]:
    """
    Builds SQL search condition and parameters.
    - Uses MySQL FULLTEXT (MATCH ... AGAINST in BOOLEAN MODE) for queries with 3+ character tokens.
    - Uses escaped LIKE fallback for short queries (<3 chars), symbol-only queries (e.g. %, _),
      or alongside FULLTEXT for location/spot fields.
    - Safely handles wildcards % and _ so they are matched literally if entered.
    """
    if not query_str:
        return None, []

    q = query_str.strip()
    if not q:
        return None, []

    tokens = re.findall(r"[a-zA-Z0-9]+", q)
    long_tokens = [t for t in tokens if len(t) >= 3]

    pfx = f"{table_prefix}." if table_prefix else ""
    loc_pfx = f"{loc_prefix}." if loc_prefix else ""
    escaped_like = f"%{escape_like(q.lower())}%"

    if long_tokens:
        ft_query = " ".join(f"+{t}*" for t in long_tokens)
        ft_clause = f"MATCH({pfx}item_name, {pfx}description, {pfx}brand) AGAINST(%s IN BOOLEAN MODE)"

        if include_location:
            loc_conditions = [
                ft_clause,
                f"LOWER({loc_pfx}location_name) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({loc_pfx}building, '')) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({pfx}room_no, '')) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({pfx}specific_spot, '')) LIKE %s ESCAPE '\\\\'"
            ]
            clause = f"({' OR '.join(loc_conditions)})"
            params = [ft_query, escaped_like, escaped_like, escaped_like, escaped_like]
            return clause, params
        else:
            return ft_clause, [ft_query]
    else:
        like_conditions = [
            f"LOWER({pfx}item_name) LIKE %s ESCAPE '\\\\'",
            f"LOWER({pfx}description) LIKE %s ESCAPE '\\\\'",
            f"LOWER(COALESCE({pfx}brand, '')) LIKE %s ESCAPE '\\\\'"
        ]
        params = [escaped_like, escaped_like, escaped_like]
        if include_location:
            like_conditions.extend([
                f"LOWER({loc_pfx}location_name) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({loc_pfx}building, '')) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({pfx}room_no, '')) LIKE %s ESCAPE '\\\\'",
                f"LOWER(COALESCE({pfx}specific_spot, '')) LIKE %s ESCAPE '\\\\'"
            ])
            params.extend([escaped_like, escaped_like, escaped_like, escaped_like])

        return f"({' OR '.join(like_conditions)})", params

