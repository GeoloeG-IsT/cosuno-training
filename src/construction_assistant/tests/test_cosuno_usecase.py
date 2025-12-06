import pytest

from construction_assistant import fetch_subcontractor_bids, compare_bids


def test_fetch_subcontractor_bids_returns_structure():
    res = fetch_subcontractor_bids("Fetch bids for foundation works", project_id="P-123")
    assert "project_id" in res
    assert res["project_id"] == "P-123"
    assert "bids" in res
    assert isinstance(res["bids"], list)
    assert len(res["bids"]) >= 1


def test_compare_bids_picks_lowest():
    bids = [
        {"subcontractor": "A", "price": 15000},
        {"subcontractor": "B", "price": 12000},
        {"subcontractor": "C", "price": 13000},
    ]
    out = compare_bids(bids, top_n=2)
    assert out["count"] == 3
    assert len(out["top"]) == 2
    assert out["top"][0]["price"] <= out["top"][1]["price"]
    assert out["average_price"] == pytest.approx((15000 + 12000 + 13000) / 3)
