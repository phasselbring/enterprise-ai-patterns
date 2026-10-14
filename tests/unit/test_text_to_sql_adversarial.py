"""Adversarial cases for the text-to-SQL guard.

The guard is defence in depth: the real boundary is a read-only database role with a statement
timeout. These tests pin down that the guard itself is not trivially bypassable either.
"""

import pytest

from enterprise_ai_patterns.text_to_sql.safe_text_to_sql import (
    validate_query,
    validate_read_only_sql,
    validate_table_allowlist,
)


@pytest.mark.parametrize(
    "sql",
    [
        # Tables outside the allowlist, reached in ways the old regex missed
        "SELECT * FROM customers, users",
        'SELECT * FROM "users"',
        "SELECT * FROM customers c JOIN LATERAL (SELECT * FROM users) u ON TRUE",
        "SELECT * FROM (SELECT * FROM users) s",
        "SELECT * FROM customers WHERE id IN (SELECT id FROM users)",
        "SELECT * FROM public.users",
        "SELECT * FROM other_schema.customers",
        # Dangerous or unknown functions
        "SELECT pg_read_file('/etc/passwd') FROM customers",
        "SELECT pg_sleep(100000) FROM customers",
        "SELECT * FROM generate_series(1, 1000000000)",
        "SELECT * FROM read_csv('/etc/passwd')",
        # Statements that write or lock despite starting with SELECT
        "SELECT * INTO stolen FROM customers",
        "SELECT * FROM customers FOR UPDATE",
        # Stacked statements
        "SELECT 1 FROM customers; DROP TABLE customers",
    ],
)
def test_bypasses_are_rejected(sql):
    with pytest.raises(ValueError):
        validate_query(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT\n  id\nFROM customers",
        "WITH big AS (SELECT customer_id FROM orders) SELECT * FROM big JOIN customers c ON c.id = big.customer_id",
        "SELECT state, count(*) AS n FROM customers GROUP BY state",
        "SELECT * FROM customers WHERE status = 'update pending'",
        "SELECT * FROM customers WHERE note = 'drop shipped';",
        "SELECT lower(name), coalesce(region, 'n/a') FROM customers",
        "SELECT id FROM customers UNION SELECT customer_id FROM orders",
    ],
)
def test_legitimate_queries_are_accepted(sql):
    validate_query(sql)


def test_allowlists_are_configurable():
    validate_query("SELECT * FROM payroll", allowed_tables={"payroll"})
    with pytest.raises(ValueError, match="Tables not allowed"):
        validate_query("SELECT * FROM customers", allowed_tables={"payroll"})
    with pytest.raises(ValueError, match="Functions not allowed"):
        validate_query("SELECT lower(name) FROM customers", allowed_functions=set())


def test_qualified_allowlist_entry_is_honoured():
    validate_query("SELECT * FROM sales.orders", allowed_tables={"sales.orders"})
    with pytest.raises(ValueError):
        validate_query("SELECT * FROM hr.orders", allowed_tables={"sales.orders"})


def test_legacy_helpers_keep_working():
    validate_read_only_sql("SELECT id FROM customers")
    validate_table_allowlist("SELECT id FROM customers")
    with pytest.raises(ValueError):
        validate_table_allowlist("SELECT * FROM customers, users")
    with pytest.raises(ValueError):
        validate_read_only_sql("SELECT pg_sleep(10)")


def test_unparseable_sql_is_rejected():
    with pytest.raises(ValueError):
        validate_query("SELECT FROM WHERE ((")


@pytest.mark.parametrize(
    "sql",
    [
        # Postgres data-modifying CTEs: the outer statement is a SELECT
        "WITH gone AS (DELETE FROM customers RETURNING *) SELECT * FROM gone",
        "WITH x AS (UPDATE orders SET total = 0 RETURNING id) SELECT * FROM x",
        "WITH x AS (INSERT INTO orders (id) VALUES (1) RETURNING id) SELECT * FROM x",
        # Cross-database reference
        "SELECT * FROM otherdb.public.customers",
    ],
)
def test_hidden_writes_and_cross_database_refs_are_rejected(sql):
    with pytest.raises(ValueError):
        validate_query(sql)


def test_table_valued_function_rejected_even_if_function_is_allowlisted():
    with pytest.raises(ValueError, match="Tables not allowed"):
        validate_query("SELECT * FROM generate_series(1, 10)",
                       allowed_functions={"GENERATE_SERIES", "EXPLODING_GENERATE_SERIES"})
