# agents/common.py
from typing import Dict, Any

from invest_agent.states import GraphState


def advance_or_finish(state: GraphState) -> GraphState:
    """
    다음 회사로 진행하거나 종료
    
    현재 idx를 1 증가시켜 다음 회사를 처리할 준비를 함.
    companies 리스트를 모두 처리했는지 여부는 workflow의
    조건부 라우팅에서 판단함.
    
    입력:
        - idx: 현재 처리 중인 회사 인덱스
        - companies: 전체 회사 리스트
    
    출력:
        - idx: 증가된 인덱스
    """
    current_idx = state.get("idx", 0)
    companies = state.get("companies", [])
    
    new_idx = current_idx + 1
    
    if new_idx < len(companies):
        print(f"[공통] 다음 회사로 진행: {new_idx + 1}/{len(companies)}")
    else:
        print(f"[공통] 모든 회사 분석 완료: {len(companies)}개")
    
    return {
        **state,
        "idx": new_idx
    }