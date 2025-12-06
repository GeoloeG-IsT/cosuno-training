"""Mock tools for the construction assistant.

These tools are used by the LangGraph-based agent to handle
procurement, scheduling, and estimation tasks.
"""
from typing import Dict, Any, Optional


def estimate_materials(prompt: str, area: Optional[float] = None, material: str = "concrete") -> Dict[str, Any]:
    """Produce a simple materials estimate.

    This function intentionally keeps calculations simple and deterministic
    so tests are easy to write and maintain. Replace with real logic for
    production use.
    """
    import re

    if area is None:
        m = re.search(r"(\d+\.?\d*)\s*(sqm|m2|square meters?|sq m)", prompt.lower())
        if m:
            area = float(m.group(1))
        else:
            area = 10.0

    if material == "concrete":
        depth_m = 0.12
        volume = area * depth_m
        # Simple conversion: assume 40 bags per m^3 (toy number)
        bags = max(1, int(round(volume * 40)))
        return {"area_sqm": area, "material": material, "volume_m3": round(volume, 3), "bags_estimate": bags}

    # Generic fallback
    return {"area_sqm": area, "material": material, "note": "simple estimate only"}


def fetch_project_plan(prompt: str, prompt_only: bool = False) -> Dict[str, Any]:
    """Return a toy multi-phase plan for a small project.

    In real LangGraph integration you'd create nodes that produce these
    phases, call external schedulers, and track state in the graph.
    """
    phases = [
        {"name": "Excavation", "duration_days": 3},
        {"name": "Concrete Pour", "duration_days": 2},
        {"name": "Curing", "duration_days": 7},
    ]
    return {"phases": phases, "note": "toy plan generated from prompt: " + prompt[:200]}


def fetch_subcontractor_bids(prompt: str, project_id: Optional[str] = None, api_key: Optional[str] = None) -> Dict[str, Any]:
    """Mock fetching subcontractor bids for a project.

    This simulates calling an external Cosuno-like API to retrieve bids.
    The output is deterministic based on the `project_id` or the prompt so
    tests remain stable.
    """
    # Create a small deterministic set of bids based on project_id or prompt
    seed = 1
    if project_id:
        seed = sum(ord(c) for c in project_id) % 10 + 1
    else:
        seed = sum(ord(c) for c in prompt[:20]) % 10 + 1

    bidders = [
        ("ACME Excavation", 10000 + seed * 10, 7),
        ("Builders Co.", 9500 + seed * 12, 10),
        ("Fast Foundations", 12000 + seed * 8, 5),
    ]

    bids = []
    for name, price, lead_days in bidders:
        bids.append({"subcontractor": name, "price": price, "lead_time_days": lead_days})

    return {"project_id": project_id or "mock-project", "bids": bids, "source": "mock-cosuno"}


def compare_bids(bids: list, top_n: int = 1) -> Dict[str, Any]:
    """Compare bids and return top_n cheapest bids and some simple metrics.

    This function is intentionally simple: it sorts by price and returns the
    best options. Real-world logic may consider lead time, reliability, or
    historical performance.
    """
    if not bids:
        return {"top": [], "count": 0}

    sorted_bids = sorted(bids, key=lambda b: b.get("price", float("inf")))
    top = sorted_bids[:top_n]
    avg_price = sum(b.get("price", 0) for b in bids) / len(bids)
    return {"top": top, "count": len(bids), "average_price": avg_price}
