import pytest
from enterprise_ai_patterns.text_to_sql.safe_text_to_sql import (
    validate_read_only_sql, validate_table_allowlist
)

def test_select_allowed():
    validate_read_only_sql("SELECT id FROM customers WHERE state = 'FL'")

@pytest.mark.parametrize("sql", [
    "DELETE FROM customers",
    "UPDATE customers SET state = 'GA'",
    "DROP TABLE customers",
])
def test_mutating_sql_rejected(sql):
    with pytest.raises(ValueError):
        validate_read_only_sql(sql)

def test_unknown_table_rejected():
    with pytest.raises(ValueError):
        validate_table_allowlist("SELECT * FROM payroll")
