"""Defence-in-depth validation for model-generated SQL.

This guard parses the SQL into an AST and checks it against allowlists. It is *not* the security
boundary on its own. Run generated SQL only through:

* a database role with read-only grants on exactly the permitted tables/views,
* a statement timeout and row limit enforced by the database or driver,
* row-level security (or views) for per-caller data scoping.

The guard exists so that bad queries are rejected early with a useful message, and so that a
misconfigured role is not the only line of defence.

Requires the ``sql`` extra (``pip install -e ".[sql]"``) for the ``sqlglot`` parser.
"""

from __future__ import annotations

from typing import Iterable

ALLOWED_TABLES = frozenset({"customers", "orders", "products"})

# Allowlist, not denylist: anything unknown (pg_read_file, pg_sleep, dblink, lo_import,
# table-valued functions ...) is rejected by default.
ALLOWED_FUNCTIONS = frozenset(
    {
        "ABS", "AVG", "CASE", "CAST", "COALESCE", "CONCAT", "COUNT", "DATE_TRUNC",
        "EXTRACT", "GREATEST", "IF", "LEAST", "LENGTH", "LOWER", "MAX", "MIN", "NULLIF",
        "ROUND", "SUBSTRING", "SUM", "TIMESTAMP_TRUNC", "TRIM", "TRY_CAST", "UPPER",
    }
)


def _sqlglot():
    try:
        import sqlglot
        from sqlglot import exp
    except ImportError as exc:  # pragma: no cover - optional dependency
        raise RuntimeError('Install the "sql" extra: pip install -e ".[sql]"') from exc
    return sqlglot, exp


def _parse_single_select(sql: str, dialect: str | None):
    sqlglot, exp = _sqlglot()
    try:
        statements = [s for s in sqlglot.parse(sql, read=dialect) if s is not None]
    except sqlglot.errors.ParseError as exc:
        raise ValueError(f"SQL could not be parsed: {exc}") from exc

    # A trailing comment after the final semicolon parses as an empty statement.
    statements = [s for s in statements if not isinstance(s, exp.Semicolon)]
    if len(statements) != 1:
        raise ValueError("Multiple statements are not allowed")

    tree = statements[0]
    if not isinstance(tree, exp.Query):
        raise ValueError("Only SELECT statements are allowed")
    return tree, exp


def _function_name(node, exp) -> str:
    if isinstance(node, exp.Anonymous):
        return str(node.name).upper()
    return node.sql_name().upper()


def _check_read_only(tree, exp, allowed_functions: set[str]) -> None:
    for node in tree.walk():
        if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Merge, exp.Create,
                             exp.Drop, exp.Alter, exp.Command, exp.TruncateTable)):
            raise ValueError("Mutating SQL is not allowed")
        if isinstance(node, exp.Into):
            raise ValueError("SELECT ... INTO is not allowed")
        if isinstance(node, exp.Lock):
            raise ValueError("Locking clauses (FOR UPDATE/SHARE) are not allowed")

    denied = sorted(
        {
            _function_name(fn, exp)
            for fn in tree.find_all(exp.Func)
            if _function_name(fn, exp) not in allowed_functions
        }
    )
    if denied:
        raise ValueError(f"Functions not allowed: {denied}")


def _check_tables(tree, exp, allowed_tables: set[str]) -> None:
    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    denied: set[str] = set()

    for table in tree.find_all(exp.Table):
        name = table.name.lower()
        if not name:
            # Table-valued function or other non-table source (e.g. generate_series(...)).
            denied.add(table.sql().lower())
            continue
        if table.catalog:
            denied.add(f"{table.catalog}.{table.db}.{name}".lower())
            continue
        if table.db:
            qualified = f"{table.db}.{name}".lower()
            if qualified not in allowed_tables:
                denied.add(qualified)
            continue
        if name in cte_names:
            continue
        if name not in allowed_tables:
            denied.add(name)

    if denied:
        raise ValueError(f"Tables not allowed: {sorted(denied)}")


def _normalise(names: Iterable[str]) -> set[str]:
    return {n.lower() for n in names}


def validate_query(
    sql: str,
    *,
    allowed_tables: Iterable[str] = ALLOWED_TABLES,
    allowed_functions: Iterable[str] = ALLOWED_FUNCTIONS,
    dialect: str | None = "postgres",
) -> None:
    """Raise ``ValueError`` unless ``sql`` is a single read-only query over allowed objects.

    ``allowed_tables`` entries are bare names (``"orders"``) or schema-qualified names
    (``"sales.orders"``). A schema-qualified reference must match a qualified entry exactly.
    """
    tree, exp = _parse_single_select(sql, dialect)
    _check_read_only(tree, exp, {f.upper() for f in allowed_functions})
    _check_tables(tree, exp, _normalise(allowed_tables))


def validate_read_only_sql(
    sql: str,
    *,
    allowed_functions: Iterable[str] = ALLOWED_FUNCTIONS,
    dialect: str | None = "postgres",
) -> None:
    """Statement-type and function checks only. Prefer :func:`validate_query`."""
    tree, exp = _parse_single_select(sql, dialect)
    _check_read_only(tree, exp, {f.upper() for f in allowed_functions})


def validate_table_allowlist(
    sql: str,
    *,
    allowed_tables: Iterable[str] = ALLOWED_TABLES,
    dialect: str | None = "postgres",
) -> None:
    """Table-reference checks only. Prefer :func:`validate_query`."""
    tree, exp = _parse_single_select(sql, dialect)
    _check_tables(tree, exp, _normalise(allowed_tables))
