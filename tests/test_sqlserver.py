import pytest
from migrationproof.sqlserver import (
    quote_identifier, collect_snapshot, select_sum_columns,
    validate_connection_security,
)
from migrationproof.core import DatabaseSnapshot, TableSnapshot, reconcile
from migrationproof.html_report import render_html


def secure_conn():
    return ("DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;"
            "DATABASE=MigrationProofSourceLab;Trusted_Connection=yes;"
            "Encrypt=yes;TrustServerCertificate=no;")


def test_identifier_escaping():
    assert quote_identifier("x]y") == "[x]]y]"
    with pytest.raises(ValueError):
        quote_identifier("")


def test_invalid_limits():
    with pytest.raises(ValueError, match="limits"):
        collect_snapshot(secure_conn(), expected_database="MigrationProofSourceLab",
                         tables_allowlist=("dbo.Orders",), timeout=0)


@pytest.mark.parametrize("connection", [
    "SERVER=localhost;DATABASE=Lab;Encrypt=no;TrustServerCertificate=no;",
    "SERVER=localhost;DATABASE=Lab;Encrypt=yes;TrustServerCertificate=yes;",
    "SERVER=localhost;DATABASE=Lab;Encrypt=yes;",
    "SERVER=localhost;Encrypt=yes;TrustServerCertificate=no;",
    "SERVER=localhost;DATABASE=Lab;Encrypt=yes;Encrypt=no;TrustServerCertificate=no;",
])
def test_unsafe_connections_rejected(connection):
    with pytest.raises(ValueError):
        validate_connection_security(connection)


def test_secure_connection_accepted():
    validate_connection_security(secure_conn())


@pytest.mark.parametrize("expected,tables,rows", [
    ("master", ("dbo.Orders",), 3),
    ("MigrationProofSourceLab", (), 3),
    ("MigrationProofSourceLab", ("dbo.Orders", "dbo.Orders"), 3),
    ("MigrationProofSourceLab", ("Orders",), 3),
    ("MigrationProofSourceLab", ("dbo.Orders",), 0),
    ("MigrationProofSourceLab", ("dbo.Orders",), 100001),
])
def test_invalid_scopes_rejected_before_connect(expected, tables, rows):
    with pytest.raises(ValueError):
        collect_snapshot(secure_conn(), expected_database=expected,
                         tables_allowlist=tables, max_rows_per_table=rows)


def test_html_escaping():
    html = render_html({"status":"<script>bad</script>", "findings":[{"code":"X","table":"<img>","detail":"a&b"}]})
    assert "<script>" not in html and "<img>" not in html
    assert "&lt;script&gt;" in html and "a&amp;b" in html


def test_numeric_sum_column_selection():
    cols = {"Amount":"decimal(9,12,2) NULL=False", "OrderID":"int(4,10,0) NULL=False",
            "CustomerRef":"varchar(20,0,0) NULL=False"}
    assert select_sum_columns(cols, ("Amount", "Amount")) == ("Amount",)
    with pytest.raises(ValueError, match="not numeric"):
        select_sum_columns(cols, ("CustomerRef",))
    with pytest.raises(ValueError, match="not found"):
        select_sum_columns(cols, ("Missing",))


def test_equal_row_count_changed_sum_is_detected():
    columns = {"Amount":"decimal(9,12,2) NULL=False"}
    source = DatabaseSnapshot(database="SourceLab", tables={"dbo.Orders":
        TableSnapshot(columns=columns, row_count=3, aggregates={"sum:Amount":"150.00"})})
    target = DatabaseSnapshot(database="TargetLab", tables={"dbo.Orders":
        TableSnapshot(columns=columns, row_count=3, aggregates={"sum:Amount":"1124.00"})})
    report = reconcile(source, target)
    assert report["status"] == "DIFFERENCES_FOUND"
    assert [f["code"] for f in report["findings"]] == ["AGGREGATE_MISMATCH"]
