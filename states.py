# invest_agent/states.py
from typing import TypedDict, Dict, Any, List

class GraphState(TypedDict, total=False):
    query: str
    companies: List[str]
    idx: int
    current_company: str
    tech: Dict[str, Any]
    market: Dict[str, Any]
    competitor: Dict[str, Any]
    decision: Dict[str, Any]
    reports: List[str]  # 또는 List[Dict[str, str]]