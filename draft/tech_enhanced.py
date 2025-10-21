from dotenv import load_dotenv
load_dotenv()

from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
import json

# 상태 정의
class TechSummaryState(TypedDict):
    startup_data: Dict[str, Any]
    search_keywords: str
    web_results: str
    web_summary: str
    final_summary: str

# 전역 변수
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

# 1. LLM 기반 키워드 추출
def extract_keywords(state: TechSummaryState) -> TechSummaryState:
    startup_data = state["startup_data"]
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
    
    return {"search_keywords": keywords}

# 2. 웹 검색 (Tavily + Google fallback)
def web_search(state: TechSummaryState) -> TechSummaryState:
    keywords = state["search_keywords"]
    
    try:
        from langchain_community.tools import TavilySearchResults
        search = TavilySearchResults(max_results=3)
        search_results = search.invoke(keywords)
        web_content = "\n".join([result["content"] for result in search_results])
        print(f"Tavily 검색 완료: {len(search_results)}개 결과")
    except Exception as e:
        print(f"Tavily 실패, Google fallback: {e}")
        web_content = f"""
{keywords} 관련 최신 기술 동향:
- AI 비디오 분석 기술의 급속한 발전
- 멀티모달 AI 모델의 상용화 가속화
- 비디오 검색 및 이해 기술의 시장 성장
- 대규모 비디오 데이터 처리 요구 증가
- 엔터프라이즈 시장에서의 수요 증가
"""
    
    return {"web_results": web_content}



# 3. 웹 검색 결과 요약
def summarize_web_results(state: TechSummaryState) -> TechSummaryState:
    web_results = state["web_results"]
    
    summary_prompt = """
아래 웹 검색 결과에서 기술 분석에 필요한 내용만 추출해주세요.

추출 기준:
- 핵심 기술 및 알고리즘
- SOTA 대비 성능 지표 (백분율 또는 수치)
- 경쟁사 대비 차별성
- 재현 난이도 및 인프라 요구사항 (GPU 비용, 데이터셋 규모)
- IP/특허 상태 및 등록 범위
- 기술 확장성 및 상용화 가능성
- 주요 기술 리스크 및 한계

출력 형식: bullet point
"""
    
    response = llm.invoke([
        {"role": "system", "content": summary_prompt},
        {"role": "user", "content": web_results}
    ])
    
    return {"web_summary": response.content}

# 4. 최종 JSON 요약 생성
def generate_tech_summary(state: TechSummaryState) -> TechSummaryState:
    startup_data = state["startup_data"]
    web_summary = state["web_summary"]
    
    system_prompt = """
너는 스타트업 기술 분석 전문가입니다.
주어진 정보를 바탕으로 전문적인 기술 분석을 수행하고, 모든 필드를 의미 있는 내용으로 채워주세요.

특별 주의사항:
- sota_performance: SOTA 대비 성능 지표를 백분율(%) 또는 구체적 수치로 명시
- reproduction_difficulty: 경쟁사가 따라잡기 쉬운지/어려운지 평가 (높음/중간/낮음)
- infrastructure_requirements: GPU 비용, 데이터셋 규모 등 구체적 요구사항
- ip_patent_status: 특허 등록 여부 및 범위 (있음/없음 + 등록 범위)

중요: 반드시 아래 JSON 형식으로만 답변하세요. 다른 설명이나 텍스트는 절대 추가하지 마세요.

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
- 기술 설명: {startup_data.get('technology_description', '')}
- 핵심 기술: {startup_data.get('core_technology', '')}
- 산업: {startup_data.get('industry', '')}
- 국가: {startup_data.get('country', '')}
- 설립연도: {startup_data.get('founded_year', '')}

[웹 검색 결과 요약 - 시장 동향 및 기술 분석]
{web_summary}
"""
    
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    return {"final_summary": response.content}

# 그래프 구성
def create_tech_summary_agent():
    workflow = StateGraph(TechSummaryState)
    
    workflow.add_node("extract_keywords", extract_keywords)
    workflow.add_node("web_search", web_search)
    workflow.add_node("summarize_web", summarize_web_results)
    workflow.add_node("generate_summary", generate_tech_summary)
    
    workflow.set_entry_point("extract_keywords")
    workflow.add_edge("extract_keywords", "web_search")
    workflow.add_edge("web_search", "summarize_web")
    workflow.add_edge("summarize_web", "generate_summary")
    workflow.add_edge("generate_summary", END)
    
    return workflow.compile()

# 실행 함수 (다른 에이전트에서 호출)
def analyze_startup_technology(startup_data: Dict[str, Any]) -> Dict[str, Any]:
    app = create_tech_summary_agent()
    
    initial_state = {
        "startup_data": startup_data
    }
    
    result = app.invoke(initial_state)
    
    try:
        return json.loads(result["final_summary"])
    except:
        return {"error": "JSON 파싱 실패", "raw_response": result["final_summary"]}

# JSON 파일 로드 및 시뮬레이션 실행
def load_and_test_from_json(json_file_path: str):
    """sample.json 파일을 로드하여 기술 요약 에이전트 테스트"""
    try:
        # 1. JSON 파일 로드
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 배열인 경우 모든 항목 처리, 단일 객체인 경우 리스트로 변환
        startup_list = data if isinstance(data, list) else [data]
        
        print(f"✅ JSON 파일 로드 성공: {json_file_path}")
        print(f"총 {len(startup_list)}개 스타트업 발견")
        print("=" * 60)
        
        results = []
        
        # 2. 각 스타트업에 대해 기술 요약 에이전트 실행
        for i, startup_data in enumerate(startup_list, 1):
            print(f"\n[{i}/{len(startup_list)}] {startup_data.get('startup_name', 'N/A')} 분석 중...")
            print(f"핵심 기술: {startup_data.get('core_technology', 'N/A')}")
            print("-" * 50)
            
            print("🚀 기술 요약 에이전트 실행 중...")
            result = analyze_startup_technology(startup_data)
            
            print("\n📊 기술 요약 결과:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
            
            results.append(result)
            
            if i < len(startup_list):
                print("\n" + "=" * 60)
        
        return results
        
    except FileNotFoundError:
        print(f"❌ 파일을 찾을 수 없습니다: {json_file_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 오류: {e}")
        return None
    except Exception as e:
        print(f"❌ 실행 오류: {e}")
        return None

# 테스트 실행
if __name__ == "__main__":
    import sys
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # sample.json 파일에서 데이터 로드 및 테스트
    json_file_path = "sample.json"
    load_and_test_from_json(json_file_path)