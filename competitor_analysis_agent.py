"""
경쟁사 분석 Agent
- Vector DB 또는 웹 검색으로 경쟁사 발굴
- 경쟁사별 웹 리서치 수행
- 경쟁 포지셔닝 분석
- SWOT 분석 생성 (투자 판단용)
"""

from typing import TypedDict, Annotated, Sequence, List, Dict, Any
from datetime import datetime
import json
import re
import os

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.tools.tavily_search import TavilySearchResults
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

# 환경 변수 로드
load_dotenv()


# ============================================
# State 정의
# ============================================
class CompetitorAgentState(TypedDict):
    """
    경쟁사 분석 Agent State
    
    Fields:
        messages: 메시지 히스토리
        target_company: 타겟 기업명
        target_tech: 기술 분석 결과 (Tech Agent로부터 입력)
        competitors: 발굴된 경쟁사 리스트 (스타트업 2 + 대기업 2)
        market_info: 시장 분석 결과 (Market Agent로부터 입력)
        research_results: 경쟁사별 웹 리서치 결과
        competitor_scores: 경쟁사별 평가 점수 (overlap, differentiation, moat)
        swot: 최종 SWOT 분석 결과
    """
    messages: Annotated[Sequence[BaseMessage], add_messages]
    target_company: str
    target_tech: Dict  # from Tech Agent
    competitors: List[Dict]  # 경쟁사 4개
    market_info: Dict  # from Market Agent
    research_results: Dict  # 경쟁사별 리서치
    competitor_scores: List[Dict]  # 경쟁사 평가
    swot: Dict  # SWOT 분석 (최종 출력)


# ============================================
# 유틸리티 함수
# ============================================
def extract_json_from_llm_response(text: str) -> dict:
    """
    LLM 응답에서 JSON 추출
    - 마크다운 코드 블록 제거
    - 앞뒤 공백/텍스트 제거
    """
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    text = text.strip()
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패")
        print(f"원본 텍스트:\n{text[:500]}")
        raise e


# ============================================
# 노드 함수들
# ============================================
def initialize_state(state: CompetitorAgentState) -> CompetitorAgentState:
    """
    State 초기화
    - Tech/Market Agent 출력을 입력으로 받음
    """
    messages = state["messages"]
    data = json.loads(messages[0].content) if isinstance(messages[0].content, str) else messages[0].content
    
    assert "company" in data, "타겟 기업명 누락"
    assert "from_tech_summary" in data, "기술 요약 누락"
    
    return {
        "messages": messages,
        "target_company": data["company"],
        "target_tech": data["from_tech_summary"],
        "competitors": [],
        "market_info": data.get("from_market", {}),
        "research_results": {},
        "competitor_scores": [],
        "swot": {}
    }


def search_web_competitors(target: str, core_tech: str, max_results: int = 2, exclude_companies: list = None) -> list:
    """웹 검색으로 경쟁사 발굴"""
    if exclude_companies is None:
        exclude_companies = []
    
    search_tool = TavilySearchResults(max_results=5)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    search_query = f"{target} competitors {core_tech} AI startup similar companies"
    
    try:
        results = search_tool.invoke({"query": search_query})
        context = "\n\n".join([
            f"[{r.get('title', 'N/A')}]\n{r.get('content', '')}\nURL: {r.get('url', '')}"
            for r in results
        ])
        
        prompt = f"""
다음 웹 검색 결과에서 {target}의 경쟁사를 찾아주세요.

타겟 기업: {target}
핵심 기술: {core_tech}

검색 결과:
{context}

제외할 기업: {', '.join(exclude_companies) if exclude_companies else '없음'}

요구사항:
1. {max_results}개의 경쟁사를 찾아주세요
2. 제외 리스트에 없는 기업만 선정
3. AI/기술 스타트업 위주로 선정
4. 각 기업에 대해 다음 정보를 포함:
   - company: 기업명
   - focus: 주력 분야/제품 (한 줄)
   - country: 국가
   - recent_investment: 최근 투자 정보 (알 수 없으면 "N/A")
   - founded_year: 설립 연도 (알 수 없으면 "N/A")
   - website: 웹사이트 URL (있으면)

순수 JSON만 출력:
{{"competitors": [
    {{"company": "CompanyA", "focus": "AI video generation", "country": "US", "recent_investment": "Series B $50M", "founded_year": "2021", "website": "https://example.com"}},
    {{"company": "CompanyB", "focus": "Text-to-video AI", "country": "UK", "recent_investment": "Seed $10M", "founded_year": "2022", "website": ""}}
]}}
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        data = extract_json_from_llm_response(response.content)
        
        web_competitors = []
        for comp in data.get("competitors", [])[:max_results]:
            if comp["company"] not in exclude_companies:
                web_competitors.append({
                    "company": comp["company"],
                    "focus": comp.get("focus", "N/A"),
                    "country": comp.get("country", "N/A"),
                    "recent_investment": comp.get("recent_investment", "N/A"),
                    "founded_year": comp.get("founded_year", "N/A"),
                    "website": comp.get("website", ""),
                    "detailed_info": "",
                    "source": "web_search"
                })
        
        print(f"✅ 웹 검색으로 {len(web_competitors)}개 경쟁사 발견")
        return web_competitors
        
    except Exception as e:
        print(f"❌ 웹 검색 실패: {e}")
        return []


def select_relevant_bigtech(target: str, target_tech: dict) -> list:
    """타겟 기업과 관련된 대기업 2개 선정"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = f"""
타겟 기업: {target}
핵심 기술: {target_tech.get('core_tech', 'N/A')}
강점: {', '.join(target_tech.get('strengths', []))}

다음 대기업 중 타겟과 가장 관련 높은 2개를 선택하세요.

대기업 목록:
- OpenAI: GPT, ChatGPT, DALL-E
- Meta: Llama, AI research
- Google: Gemini, DeepMind, Imagen
- Microsoft: Copilot, Azure AI
- Anthropic: Claude
- Amazon: AWS AI, Alexa
- Adobe: Firefly, Sensei
- Stability AI: Stable Diffusion

순수 JSON만 출력:
{{"companies": [{{"company": "OpenAI", "focus": "LLM, ChatGPT", "reasoning": "이유"}}, {{"company": "Google", "focus": "Gemini", "reasoning": "이유"}}]}}
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json_from_llm_response(response.content)
    
    bigtech = []
    for comp in data.get("companies", [])[:2]:
        bigtech.append({
            "company": comp["company"],
            "focus": comp["focus"],
            "country": "US",
            "recent_investment": "대기업 (상장)",
            "source": "bigtech",
            "reasoning": comp.get("reasoning", "")
        })
    
    print(f"✅ 대기업 선정: {[c['company'] for c in bigtech]}")
    return bigtech


def search_competitors_hybrid(state: CompetitorAgentState) -> CompetitorAgentState:
    """
    Vector DB에서 경쟁사 검색 + 웹 검색 보완
    - Vector DB에서 유사 스타트업 검색 (최대 2개)
    - 부족하면 웹 검색
    - 대기업 2개 추가
    - 총 4개 경쟁사
    """
    target = state["target_company"]
    target_tech = state["target_tech"]
    
    embeddings = HuggingFaceBgeEmbeddings(
        model_name="BAAI/bge-base-en-v1.5",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )
    
    startup_competitors = []
    
    try:
        vectorstore = FAISS.load_local(
            "competitor_vectordb",
            embeddings,
            allow_dangerous_deserialization=True
        )
        
        search_query = f"{target} {target_tech.get('core_tech', '')} AI startup"
        docs = vectorstore.similarity_search(search_query, k=2)
        
        for doc in docs:
            startup_competitors.append({
                "company": doc.metadata.get("company", "Unknown"),
                "focus": doc.metadata.get("focus", "N/A"),
                "country": doc.metadata.get("country", "N/A"),
                "recent_investment": doc.metadata.get("recent_investment", "N/A"),
                "founded_year": doc.metadata.get("founded_year", "N/A"),
                "website": doc.metadata.get("website", ""),
                "detailed_info": doc.metadata.get("detailed_info", ""),
                "source": "vectordb"
            })
        
        print(f"✅ Vector DB: {len(startup_competitors)}개 발견")
        
    except FileNotFoundError:
        print("⚠️ Vector DB 파일 없음. 웹 검색으로 대체")
        startup_competitors = []
    except Exception as e:
        print(f"❌ Vector DB 로드 실패: {e}")
        startup_competitors = []
    
    if len(startup_competitors) < 2:
        needed = 2 - len(startup_competitors)
        web_startups = search_web_competitors(
            target, 
            target_tech.get('core_tech', ''), 
            max_results=needed,
            exclude_companies=[c["company"] for c in startup_competitors]
        )
        startup_competitors.extend(web_startups)
        print(f"✅ 웹 검색: {len(web_startups)}개 추가")
    
    bigtech = select_relevant_bigtech(target, target_tech)
    all_competitors = startup_competitors[:2] + bigtech[:2]
    
    print(f"📊 최종 경쟁사: {[c['company'] for c in all_competitors]}")
    
    return {
        **state,
        "competitors": all_competitors,
        "messages": state["messages"] + [
            HumanMessage(content=f"경쟁사 4개 선정 (스타트업 {len(startup_competitors[:2])}, 대기업 {len(bigtech[:2])})")
        ]
    }


def web_research_competitors(state: CompetitorAgentState) -> CompetitorAgentState:
    """경쟁사별 웹 리서치"""
    target = state["target_company"]
    competitors = state["competitors"]
    search_tool = TavilySearchResults(max_results=3)
    research_data = {}
    
    for comp in competitors:
        comp_name = comp["company"]
        search_query = f"{comp_name} AI startup product features customers funding"
        
        try:
            results = search_tool.invoke({"query": search_query})
            context = "\n\n".join([
                f"[{r.get('title', 'N/A')}]\n{r.get('content', '')}\nURL: {r.get('url', '')}"
                for r in results
            ])
            
            llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
            summary = llm.invoke([HumanMessage(content=f"""
다음 웹 검색 결과에서 핵심 정보만 추출하세요:

경쟁사: {comp_name}
주력 분야: {comp.get('focus', 'N/A')}

검색 결과:
{context}

다음 항목을 간결하게 정리 (각 2-3문장):
1. 제품/서비스 특징
2. 주요 고객층/타겟 시장
3. 최근 동향 (투자, 제품 출시 등)
4. 기술적 강점
""")])
            
            research_data[comp_name] = summary.content
            print(f"✅ {comp_name} 리서치 완료")
            
        except Exception as e:
            print(f"❌ 웹 검색 실패 ({comp_name}): {e}")
            research_data[comp_name] = f"주력 분야: {comp.get('focus', 'N/A')}"
    
    return {
        **state,
        "research_results": research_data,
        "messages": state["messages"] + [
            HumanMessage(content=f"웹 리서치 완료: {len(competitors)}개 경쟁사")
        ]
    }


def analyze_competitive_positioning(state: CompetitorAgentState) -> CompetitorAgentState:
    """경쟁사별 포지셔닝 분석"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    target = state["target_company"]
    target_tech = state["target_tech"]
    competitors = state["competitors"]
    research = state["research_results"]
    
    scored_list = []
    
    for comp in competitors:
        prompt = f"""
경쟁사를 다음 기준으로 평가하세요 (각 0-10점):
1. overlap: 타겟({target})과 시장 중복도
2. differentiation: 경쟁사만의 차별화
3. moat: 진입장벽
4. positioning: 한 문장 요약

타겟 핵심 기술: {target_tech.get('core_tech', 'N/A')}
경쟁사: {comp["company"]}
주력 분야: {comp.get('focus', 'N/A')}
최근 투자: {comp.get('recent_investment', 'N/A')}

웹 리서치:
{research.get(comp["company"], "정보 없음")}

순수 JSON만 출력:
{{"company": "{comp['company']}", "overlap": 7.5, "differentiation": 6.0, "moat": 5.5, "positioning": "한 문장"}}
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        score_data = extract_json_from_llm_response(response.content)
        scored_list.append(score_data)
        print(f"✅ {comp['company']} 평가 완료")
    
    return {
        **state,
        "competitor_scores": scored_list,
        "messages": state["messages"] + [
            HumanMessage(content=f"경쟁 구도 분석 완료: {len(scored_list)}개")
        ]
    }


def generate_swot_analysis(state: CompetitorAgentState) -> CompetitorAgentState:
    """SWOT 분석 생성 (투자 판단용)"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    target = state["target_company"]
    target_tech = state["target_tech"]
    competitor_scores = state["competitor_scores"]
    market_info = state["market_info"]
    research_results = state["research_results"]
    
    competitor_summary = "\n".join([
        f"- {score['company']}: overlap {score['overlap']}/10, moat {score['moat']}/10\n  포지셔닝: {score['positioning']}"
        for score in competitor_scores
    ])
    
    swot_prompt = f"""
당신은 벤처 투자 심사역입니다. 다음 스타트업에 대한 투자 판단을 위한 경쟁 분석 기반 SWOT을 작성하세요.

## 타겟 기업 정보
- 기업명: {target}
- 핵심 기술: {target_tech.get('core_tech', 'N/A')}
- 기술적 강점: {', '.join(target_tech.get('strengths', []))}
- 기술적 약점: {', '.join(target_tech.get('weaknesses', []))}

## 시장 환경
{json.dumps(market_info, indent=2, ensure_ascii=False)}

## 경쟁사 분석 결과
{competitor_summary}

## 경쟁사 상세 리서치
{json.dumps(research_results, indent=2, ensure_ascii=False)[:2000]}

---

투자 의사결정에 필요한 **구체적이고 실행 가능한** SWOT 분석을 작성하세요:

### Strengths (경쟁 우위, 5-7개)
- 경쟁사 대비 **명확히 우월한 점**
- 정량적 근거 포함 (예: "렌더링 속도 경쟁사 대비 2배", "고객 만족도 95%")
- 방어 가능한 기술적/시장적 우위
- 투자자 관점: "이 회사가 왜 이길 수 있는가?"

### Weaknesses (투자 리스크, 5-7개)
- 경쟁사 대비 **명확히 불리한 점**
- 정량적 리스크 (예: "운영비용 매출의 70%", "대기업 대비 자본력 1/100")
- 단기적으로 개선 어려운 구조적 약점
- 투자자 관점: "어떤 리스크로 실패할 수 있는가?"

### Opportunities (성장 기회, 5-7개)
- 시장 성장 기회 (구체적 수치)
- 경쟁사가 놓치고 있는 틈새
- 기술/시장 트렌드 활용 방안
- 파트너십, M&A, 신규 시장 진출 가능성
- 투자자 관점: "어떻게 10배 성장할 수 있는가?"

### Threats (생존 위협, 5-7개)
- 대기업 진입 위협 (OpenAI, Google 등)
- 기술 commoditization 리스크
- 규제, 저작권 이슈
- 경쟁 심화로 인한 마진 축소
- 투자자 관점: "무엇이 이 회사를 죽일 수 있는가?"

---

**작성 원칙:**
1. 각 항목은 **구체적 근거**와 함께 작성 (추상적 표현 금지)
2. 투자 의사결정에 직접 활용 가능한 수준
3. 경쟁사 분석 결과를 **명시적으로 반영**
4. 시장 데이터가 있으면 인용

순수 JSON만 출력:
{{
  "strengths": [
    "영상 생성 특화 AI 모델로 경쟁사(Pika Labs) 대비 렌더링 품질 15% 우수",
    "크리에이터 중심 UX로 사용자 이탈률 5% (업계 평균 20%)",
    "...5-7개"
  ],
  "weaknesses": [
    "GPU 인프라 비용이 매출의 60%로 경쟁사(30%) 대비 2배 높음",
    "OpenAI, Adobe 등 대기업 대비 R&D 투자 1/50 수준",
    "...5-7개"
  ],
  "opportunities": [
    "생성형 AI 비디오 시장 2024-2027 CAGR 150% 성장 예상",
    "크리에이터 이코노미 시장 $104B → $480B (2027) 확대",
    "...5-7개"
  ],
  "threats": [
    "OpenAI Sora 출시 시 가격 경쟁으로 마진 50% 축소 위험",
    "오픈소스 모델(Stable Video Diffusion) 품질 향상으로 무료 대체재 증가",
    "...5-7개"
  ]
}}
"""
    
    response = llm.invoke([HumanMessage(content=swot_prompt)])
    swot_data = extract_json_from_llm_response(response.content)
    
    for key in ["strengths", "weaknesses", "opportunities", "threats"]:
        if len(swot_data.get(key, [])) < 4:
            print(f"⚠️ {key} 항목이 {len(swot_data.get(key, []))}개로 부족함")
    
    print("✅ SWOT 분석 완료")
    
    return {
        **state,
        "swot": swot_data,
        "messages": state["messages"] + [
            HumanMessage(content="SWOT 분석 완료")
        ]
    }


def finalize_output(state: CompetitorAgentState) -> CompetitorAgentState:
    """최종 출력 생성"""
    output = {
        "company": state["target_company"],
        "competitors_analysis": state["competitor_scores"],
        "swot": state["swot"],
        "generated_at": datetime.now().isoformat()
    }
    
    return {
        **state,
        "messages": state["messages"] + [
            HumanMessage(content=json.dumps(output, indent=2, ensure_ascii=False))
        ]
    }


# ============================================
# 그래프 생성
# ============================================
def create_competitor_analysis_graph():
    """경쟁사 분석 그래프 생성"""
    workflow = StateGraph(CompetitorAgentState)
    
    workflow.add_node("initialize", initialize_state)
    workflow.add_node("search_competitors", search_competitors_hybrid)
    workflow.add_node("web_research", web_research_competitors)
    workflow.add_node("analyze_positioning", analyze_competitive_positioning)
    workflow.add_node("swot_analysis", generate_swot_analysis)
    workflow.add_node("finalize", finalize_output)
    
    workflow.add_edge(START, "initialize")
    workflow.add_edge("initialize", "search_competitors")
    workflow.add_edge("search_competitors", "web_research")
    workflow.add_edge("web_research", "analyze_positioning")
    workflow.add_edge("analyze_positioning", "swot_analysis")
    workflow.add_edge("swot_analysis", "finalize")
    workflow.add_edge("finalize", END)
    
    return workflow.compile()


# ============================================
# 유틸리티 함수
# ============================================
def save_output_to_json(output_json: str, filename: str = "competitor_analysis_output.json"):
    """출력 결과를 JSON 파일로 저장"""
    output = json.loads(output_json)
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"저장 완료: {filename}")


def analyze_competitors(company: str, tech_summary: Dict, market_summary: Dict) -> Dict:
    """
    경쟁사 분석 실행 (외부에서 호출 가능한 함수)
    
    Args:
        company: 분석 대상 기업명
        tech_summary: 기술 분석 결과
        market_summary: 시장 분석 결과
    
    Returns:
        경쟁사 분석 결과 (SWOT 포함)
    """
    input_data = {
        "company": company,
        "from_tech_summary": tech_summary,
        "from_market": market_summary
    }
    
    graph = create_competitor_analysis_graph()
    
    initial_state = {
        "messages": [HumanMessage(content=json.dumps(input_data, ensure_ascii=False))],
        "target_company": "",
        "target_tech": {},
        "competitors": [],
        "market_info": {},
        "research_results": {},
        "competitor_scores": [],
        "swot": {}
    }
    
    final_state = graph.invoke(initial_state)
    result = json.loads(final_state["messages"][-1].content)
    
    return result


# ============================================
# 메인 실행
# ============================================
if __name__ == "__main__":
    # 테스트 실행
    test_input = {
        "company": "Runway",
        "tech_summary": {
            "company": "Runway",
            "core_tech": "Text-to-video generation",
            "strengths": ["영상 생성 AI", "크리에이터 UX"],
            "weaknesses": ["GPU 비용", "데이터 투명성"]
        },
        "market_summary": {}
    }
    
    print("=== 경쟁사 분석 Agent 실행 ===\n")
    result = analyze_competitors(
        test_input["company"],
        test_input["tech_summary"],
        test_input["market_summary"]
    )
    
    print("\n=== 최종 결과 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))