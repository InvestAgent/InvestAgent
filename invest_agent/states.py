# invest_agent/states.py
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from enum import Enum 
class InvestmentLabel(str, Enum):
    """투자 판단 레이블"""
    INVEST = "invest"
    RECOMMEND = "recommend"
    INVEST_CONDITIONAL = "invest_conditional"
    HOLD = "hold"
    REJECT = "reject"

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
    risks: List[Dict[str, Any]]
    
    # Report
    reports: List[Dict[str, Any]]
    report_config: Dict[str, Any]

    # 출처 추적
    sources: Annotated[Dict[str, List[str]], lambda x, y: {**x, **y}]
    