import copy
import pytest

from migrationproof.rows import RowEvidenceError, reconcile_rows


def evidence(rows):
    return {
        "table": "dbo.Orders",
        "key_columns": ["OrderID"],
        "compare_columns": ["Amount", "Status"],
        "rows": rows,
    }


def row(order_id, amount, status="paid"):
    return {"OrderID": order_id, "Amount": amount, "Status": status}


def test_equal_rows_match_in_different_order():
    source = evidence([row(1, "10.00"), row(2, "20.00")])
    target = evidence([row(2, "20.00"), row(1, "10.00")])
    result = reconcile_rows(source, target)
    assert result["status"] == "SUPPLIED_ROWS_MATCH"
    assert result["changed_matching_keys"] == 0


def test_equal_counts_equal_sums_still_detect_swapped_values():
    source = evidence([row(1, "10.00"), row(2, "20.00")])
    target = evidence([row(1, "20.00"), row(2, "10.00")])
    result = reconcile_rows(source, target)
    assert result["status"] == "DIFFERENCES_FOUND"
    assert result["changed_matching_keys"] == 2
    assert result["source_rows_supplied"] == result["target_rows_supplied"] == 2


def test_missing_and_extra_keys():
    result = reconcile_rows(
        evidence([row(1, "10.00"), row(2, "20.00")]),
        evidence([row(2, "20.00"), row(3, "30.00")]),
    )
    assert result["missing_target_keys"] == 1
    assert result["extra_target_keys"] == 1


def test_boolean_and_integer_keys_do_not_collide():
    result = reconcile_rows(evidence([row(True, "1")]), evidence([row(1, "1")]))
    assert result["missing_target_keys"] == 1
    assert result["extra_target_keys"] == 1


def test_no_raw_values_or_row_keys_in_result():
    secret = "person@example.invalid"
    source = evidence([row(973851, secret)])
    target = evidence([row(973851, "other")])
    output = str(reconcile_rows(source, target))
    assert secret not in output
    assert "973851" not in output


@pytest.mark.parametrize("bad", [
    {"table": "dbo.Orders", "key_columns": [], "compare_columns": ["Amount"], "rows": []},
    {"table": "dbo.Orders", "key_columns": ["OrderID"], "compare_columns": ["OrderID"], "rows": []},
    evidence([row(1, "10.00"), row(1, "20.00")]),
    evidence([{"OrderID": 1, "Amount": "10.00"}]),
    evidence([row(None, "10.00")]),
    evidence([row(1, 10.01)]),
    evidence([row(1, "10.00", status={"nested": "object"})]),
])
def test_ambiguous_input_is_rejected(bad):
    with pytest.raises(RowEvidenceError):
        reconcile_rows(bad, bad)


def test_scope_mismatch_rejected():
    source = evidence([row(1, "10.00")])
    target = copy.deepcopy(source)
    target["compare_columns"] = ["Amount"]
    with pytest.raises(RowEvidenceError, match="scope"):
        reconcile_rows(source, target)


def test_bounded_rows_rejected():
    with pytest.raises(RowEvidenceError, match="budget"):
        reconcile_rows(evidence([row(i, "1") for i in range(10001)]), evidence([]))
