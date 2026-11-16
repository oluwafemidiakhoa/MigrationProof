import pytest
from migrationproof.sqlserver import quote_identifier, collect_snapshot
from migrationproof.html_report import render_html

def test_identifier_escaping():
    assert quote_identifier("x]y") == "[x]]y]"
    with pytest.raises(ValueError):
        quote_identifier("")

def test_invalid_limits():
    with pytest.raises(ValueError):
        collect_snapshot("unused", timeout=0)

def test_html_escaping():
    html = render_html({"status":"<script>bad</script>", "findings":[{"code":"X","table":"<img>","detail":"a&b"}]})
    assert "<script>" not in html and "<img>" not in html
    assert "&lt;script&gt;" in html and "a&amp;b" in html
