import re

FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|truncate|merge|grant|revoke|create)\b", re.I)
ALLOWED_TABLES = {"customers", "orders", "products"}

def validate_read_only_sql(sql: str):
    normalized = sql.strip().rstrip(";")
    if not normalized.lower().startswith("select "):
        raise ValueError("Only SELECT statements are allowed")
    if FORBIDDEN.search(normalized):
        raise ValueError("Mutating SQL is not allowed")
    if ";" in normalized:
        raise ValueError("Multiple statements are not allowed")

def validate_table_allowlist(sql: str):
    refs = {
        x.lower()
        for x in re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*)", sql, re.I)
    }
    denied = refs - ALLOWED_TABLES
    if denied:
        raise ValueError(f"Tables not allowed: {sorted(denied)}")
