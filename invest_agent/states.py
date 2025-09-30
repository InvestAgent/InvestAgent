# invest_agent/states.py
from typing import TypedDict, List, Dict, Any, Optional

class GraphState(TypedDict, total=False):
    # 입력
    query: str
    
    # Discovery
    discovery: Dict[str, Any]
    companies: List[str]
    idx: int
    current_company: str
    
    # Analysis
    tech: Dict[str, Any]
    market_eval: Dict[str, Any]
    competitor: Dict[str, Any]
    decision: Dict[str, Any]
    
    # Report
    reports: List[Dict[str, Any]]
    report_config: Dict[str, Any]
    
    # Optional (invest.py 내부용)
    risks: List[Dict[str, Any]]