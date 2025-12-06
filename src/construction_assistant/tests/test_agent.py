import pytest

from construction_assistant import estimate_materials, fetch_project_plan


def test_estimate_materials_from_prompt():
    res = estimate_materials("Estimate materials for 50 sqm")
    assert res["area_sqm"] == 50
    assert res["material"] == "concrete"
    assert res["volume_m3"] == round(50 * 0.12, 3)
    assert res["bags_estimate"] >= 1


def test_fetch_project_plan():
    res = fetch_project_plan("Get a plan for foundation works")
    assert "phases" in res
    assert isinstance(res["phases"], list)
    assert len(res["phases"]) >= 1
