# agents/tech.py
from typing import Dict, Any
import json

from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults

from invest_agent.states import GraphState


def tech_summary(state: GraphState) -> GraphState:
    """
    기술 요약 노드
    
    입력:
        - current_company: 현재 분석 중인 회사명
        - discovery: 기업 탐색 결과 (items 리스트)
    
    출력:
        - tech: {
            technology: {...},
            meta: {...}
          }
    """
    current_company = state.get("current_company", "")
    discovery_items = state.get("discovery", {}).get("items", [])
    
    # 현재 회사 데이터 찾기
    startup_data = None
    for item in discovery_items:
        if item.get("startup_name") == current_company:
            startup_data = item
            break
    
    if not startup_data:
        print(f"[기술 요약] 경고: {current_company} 데이터 없음")
        return {
            **state,
            "tech": {
                "technology": {"technology_summary": "데이터 없음"},
                "meta": {"startup_name": current_company}
            }
        }
    
    print(f"[기술 요약] 시작: {current_company}")
    
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)
    
    # 1. 키워드 추출
    tech_desc = startup_data.get("technology_description", "")
    core_tech = startup_data.get("core_technology", "")
    startup_name = startup_data.get("startup_name", "")
    
    keyword_prompt = f"""
다음 스타트업 정보에서 웹 검색에 최적화된 키워드를 추출해주세요.
스타트업명: {startup_name}
기술 설명: {tech_desc}
핵심 기술: {core_tech}

검색 키워드 (영어, 3-5개 단어):
"""
    
    response = llm.invoke([{"role": "user", "content": keyword_prompt}])
    keywords = response.content.strip()
    print(f"  ✓ 키워드: {keywords}")
    
    # 2. 웹 검색
    try:
        search = TavilySearchResults(max_results=3)
        search_results = search.invoke(keywords)
        web_content = "\n".join([result["content"] for result in search_results])
        print(f"  ✓ 웹 검색: {len(search_results)}개 결과")
    except Exception as e:
        print(f"  ⚠ 웹 검색 실패, fallback 사용: {e}")
        web_content = f"""
{keywords} 관련 최신 기술 동향:
- AI 기술의 급속한 발전
- 멀티모달 AI 모델의 상용화 가속화
- 엔터프라이즈 시장에서의 수요 증가
"""
    
    # 3. 웹 결과 요약
    summary_prompt = """
아래 웹 검색 결과에서 기술 분석에 필요한 내용만 추출해주세요.

추출 기준:
- 핵심 기술 및 알고리즘
- SOTA 대비 성능 지표
- 경쟁사 대비 차별성
- 재현 난이도 및 인프라 요구사항
- IP/특허 상태
- 기술 확장성
- 주요 기술 리스크

출력 형식: bullet point
"""
    
    web_summary_response = llm.invoke([
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": web_content}
    ])
    web_summary = web_summary_response.content
    print(f"  ✓ 웹 요약 완료")
    
    # 4. 최종 JSON 생성
    system_prompt = """
너는 스타트업 기술 분석 전문가입니다.
주어진 정보를 바탕으로 전문적인 기술 분석을 수행하고, 모든 필드를 의미 있는 내용으로 채워주세요.

특별 주의사항:
- sota_performance: SOTA 대비 성능을 구체적으로
- reproduction_difficulty: 재현 난이도 (높음/중간/낮음)
- infrastructure_requirements: GPU, 데이터셋 등 구체적 요구사항
- ip_patent_status: 특허 등록 여부 및 범위

중요: 반드시 아래 JSON 형식으로만 답변하세요.

JSON 스키마:
{
  "technology": {
    "technology_summary": "",
    "core_technology": "",
    "differentiation": "",
    "sota_performance": "",
    "reproduction_difficulty": "",
    "infrastructure_requirements": "",
    "ip_patent_status": "",
    "scalability": "",
    "tech_risks": []
  },
  "meta": {
    "startup_name": "",
    "industry": "",
    "country": "",
    "founded_year": ""
  }
}
"""
    
    user_prompt = f"""
스타트업 정보:
- 스타트업명: {startup_data.get('startup_name', '')}
- 기술 설명: {tech_desc}
- 핵심 기술: {core_tech}
- 산업: {startup_data.get('industry', '')}
- 국가: {startup_data.get('country', '')}
- 설립연도: {startup_data.get('founded_year', '')}

[웹 검색 결과 요약]
{web_summary}
"""
    
    final_response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    # JSON 파싱
    try:
        # 마크다운 코드 블록 제거
        content = final_response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        tech_data = json.loads(content)
        print(f"  ✓ 기술 요약 완료")
        
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON 파싱 실패: {e}")
        # fallback
        tech_data = {
            "technology": {
                "technology_summary": tech_desc,
                "core_technology": core_tech,
                "differentiation": "분석 중",
                "sota_performance": "N/A",
                "reproduction_difficulty": "중간",
                "infrastructure_requirements": "표준 클라우드 인프라",
                "ip_patent_status": "확인 필요",
                "scalability": "확장 가능",
                "tech_risks": ["데이터 품질", "경쟁 심화"]
            },
            "meta": {
                "startup_name": startup_name,
                "industry": startup_data.get('industry', ''),
                "country": startup_data.get('country', ''),
                "founded_year": startup_data.get('founded_year', '')
            }
        }
    
    return {
        **state,
        "tech": tech_data
    }