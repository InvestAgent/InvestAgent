# invest_agent/workflow.py
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .states import GraphState

# ── Nodes
from ..nodes.discovery import startup_discovery, pick_company
from ..nodes.tech import tech_summary
from ..nodes.market import market_eval
from ..nodes.competitor import competitor_analysis
from ..nodes.invest import investment_decision
from ..nodes.report import report_writer       
from ..nodes.common import advance_or_finish

# ── Routers
def invest_or_hold(state: GraphState):
    companies = state.get("companies", [])
    idx = state.get("idx", 0)
    if idx >= len(companies):
        return "done"
    label = state.get("decision", {}).get("label", "hold")
    if label == "recommend":
        return "invest"
    elif label == "reject":
        return "reject_next"
    else:
        return "hold_or_next"

def has_more_companies(state: GraphState):
    companies = state.get("companies", [])
    idx = state.get("idx", 0)
    return "next" if idx + 1 < len(companies) else "done"


def build_app():
    # --------- Wire Graph ---------
    workflow = StateGraph(GraphState)

    # 노드 등록
    workflow.add_node("startup_discovery", startup_discovery)
    workflow.add_node("pick_company",       pick_company)
    workflow.add_node("tech_summary",       tech_summary)
    workflow.add_node("market_eval",        market_eval)
    workflow.add_node("competitor_analysis", competitor_analysis)
    workflow.add_node("investment_decision", investment_decision)
    workflow.add_node("report_writer",      report_writer)
    workflow.add_node("advance_or_finish",  advance_or_finish)

    # 흐름:
    # 탐색 → 회사 선택 → (기술, 시장) 병렬 → 경쟁 → 투자
    workflow.add_edge("startup_discovery", "pick_company")
    workflow.add_edge("pick_company", "tech_summary")
    workflow.add_edge("pick_company", "market_eval")
    workflow.add_edge("tech_summary", "competitor_analysis")
    workflow.add_edge("market_eval", "competitor_analysis")
    workflow.add_edge("competitor_analysis", "investment_decision")

    # 투자 판단 분기:
    # - 추천(invest) → 보고서 → 다음 회사/종료
    # - 보류/거절 → 바로 다음 회사/종료
    workflow.add_conditional_edges(
        "investment_decision",
        invest_or_hold,
        {
            "invest": "report_writer",
            "hold_or_next": "advance_or_finish",
            "reject_next": "advance_or_finish",
            "done": END,
        },
    )

    # 보고서 후 다음 회사/종료
    workflow.add_conditional_edges(
        "report_writer",
        has_more_companies,
        {
            "next": "advance_or_finish",
            "done": END,
        },
    )

    # advance 후 다음 회사 선택 → 다시 기술/시장으로
    workflow.add_edge("advance_or_finish", "pick_company")

    # 시작점
    workflow.set_entry_point("startup_discovery")

    # 컴파일
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)
    return app

# 바로 import해서 쓰기 편하게
app = build_app()