# agents/competitor.py
from typing import Dict, Any, List, Tuple
import json
from datetime import datetime
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

from invest_agent.states import GraphState


def extract_json_from_llm_response(text: str) -> dict:
    """LLM 응답에서 JSON 추출"""
    import re
    text = re.sub(r'```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```', '', text)
    text = text.strip()
    
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        text = json_match.group()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {text[:200]}")
        raise e


def search_web_competitors(target: str, core_tech: str, max_results: int = 2, exclude_companies: list = None) -> Tuple[list, list]:
    """
    웹 검색으로 경쟁사 발굴
    
    Returns:
        (competitors, urls) 튜플
    """
    if exclude_companies is None:
        exclude_companies = []
    
    search_tool = TavilySearchResults(max_results=5)
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    search_query = f"{target} competitors {core_tech} AI startup similar companies"
    
    try:
        results = search_tool.invoke({"query": search_query})
        
        # URL 수집
        urls = [r.get("url", "") for r in results if r.get("url")]
        
        context = "\n\n".join([
            f"[{r.get('title', 'N/A')}]\n{r.get('content', '')}"
            for r in results
        ])
        
        prompt = f"""
다음 웹 검색 결과에서 {target}의 경쟁사를 찾아주세요.

타겟: {target}, 기술: {core_tech}
제외: {', '.join(exclude_companies) if exclude_companies else '없음'}

검색 결과:
{context}

{max_results}개 경쟁사를 JSON으로 출력:
{{"competitors": [{{"company": "Name", "focus": "주력분야", "country": "국가", "recent_investment": "투자정보", "founded_year": "연도", "website": "URL"}}]}}
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
                    "source": "web_search"
                })
        
        return web_competitors, urls
        
    except Exception as e:
        print(f"❌ 웹 검색 실패: {e}")
        return [], []


def select_relevant_bigtech(target: str, target_tech: dict) -> list:
    """관련 대기업 2개 선정"""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    
    prompt = f"""
타겟: {target}, 기술: {target_tech.get('core_technology', 'N/A')}

다음 중 가장 관련 높은 대기업 2개 선택:
OpenAI, Meta, Google, Microsoft, Anthropic, Amazon, Adobe, Stability AI

JSON 출력:
{{"companies": [{{"company": "OpenAI", "focus": "GPT", "reasoning": "이유"}}]}}
"""
    
    response = llm.invoke([HumanMessage(content=prompt)])
    data = extract_json_from_llm_response(response.content)
    
    return [{
        "company": c["company"],
        "focus": c["focus"],
        "country": "US",
        "recent_investment": "대기업 (상장)",
        "source": "bigtech"
    } for c in data.get("companies", [])[:2]]


def competitor_analysis(state: GraphState) -> GraphState:
    """
    경쟁사 분석 노드
    
    입력:
        - current_company: 타겟 기업명
        - tech: 기술 분석 결과
        - market_eval: 시장 분석 결과
    
    출력:
        - competitor: {...}
        - sources["competitor"]: 참고 출처
    """
    target = state.get("current_company", "Unknown")
    tech = state.get("tech", {})
    tech_blk = tech.get("technology", {})
    market_eval = state.get("market_eval", {})
    
    print(f"[경쟁사 분석] 시작: {target}")
    
    # ===== 출처 수집 =====
    competitor_sources = []
    
    # 1. 경쟁사 발굴 (스타트업 2 + 대기업 2)
    startup_competitors = []
    
    # Discovery FAISS 활용
    try:
        embeddings = HuggingFaceBgeEmbeddings(
            model_name="BAAI/bge-base-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
        
        faiss_path = Path("faiss_startup_index")  # ✅ Discovery 스타트업 DB
        
        if faiss_path.exists():
            vectorstore = FAISS.load_local(
                str(faiss_path),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            search_query = f"{target} {tech_blk.get('core_technology', '')} AI startup"
            docs = vectorstore.similarity_search(search_query, k=3)
            
            for doc in docs:
                comp_name = doc.metadata.get("startup_name", "Unknown")
                
                # 자기 자신 제외
                if comp_name != target:
                    startup_competitors.append({
                        "company": comp_name,
                        "focus": doc.metadata.get("industry", "N/A"),
                        "country": doc.metadata.get("country", "N/A"),
                        "source": "discovery_faiss"
                    })
            
            print(f"  ✓ Discovery FAISS: {len(startup_competitors)}개")
        else:
            print(f"  ⚠️ Discovery FAISS 없음: {faiss_path}")
        
    except Exception as e:
        print(f"  ⚠ Vector DB 실패: {e}")
    
    # 부족하면 웹 검색 (URL 수집 포함)
    if len(startup_competitors) < 2:
        needed = 2 - len(startup_competitors)
        web_comps, web_urls = search_web_competitors(
            target,
            tech_blk.get('core_technology', ''),
            max_results=needed,
            exclude_companies=[c["company"] for c in startup_competitors]
        )
        startup_competitors.extend(web_comps)
        competitor_sources.extend(web_urls)
        print(f"  ✓ 웹 검색: {len(web_comps)}개 추가")
    
    # 대기업 2개
    bigtech = select_relevant_bigtech(target, tech_blk)
    print(f"  ✓ 대기업: {[c['company'] for c in bigtech]}")
    
    all_competitors = startup_competitors[:2] + bigtech[:2]
    
    # 2. 웹 리서치 (URL 수집)
    search_tool = TavilySearchResults(max_results=3)
    research_data = {}
    
    for comp in all_competitors:
        comp_name = comp["company"]
        try:
            results = search_tool.invoke({
                "query": f"{comp_name} AI product features customers"
            })
            
            # URL 수집
            for r in results:
                if r.get("url"):
                    competitor_sources.append(r["url"])
            
            context = "\n".join([r.get('content', '')[:200] for r in results])
            research_data[comp_name] = context
        except Exception as e:
            research_data[comp_name] = f"Focus: {comp.get('focus', 'N/A')}"
    
    print(f"  ✓ 웹 리서치 완료")
    print(f"  ✓ 수집된 출처: {len(competitor_sources)}개")
    
    # 3. 경쟁 포지셔닝 분석
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    scored_list = []
    
    for comp in all_competitors:
        prompt = f"""
경쟁사 평가 (각 0-10점):

타겟: {target} / 기술: {tech_blk.get('core_technology', 'N/A')}
경쟁사: {comp["company"]} / {comp.get('focus', 'N/A')}

리서치: {research_data.get(comp["company"], "")[:300]}

JSON 출력:
{{"company": "{comp['company']}", "overlap": 7.5, "differentiation": 6.0, "moat": 5.5, "positioning": "한 문장 요약"}}
"""
        
        response = llm.invoke([HumanMessage(content=prompt)])
        score_data = extract_json_from_llm_response(response.content)
        scored_list.append(score_data)
    
    print(f"  ✓ 포지셔닝 분석 완료")
    
    # 4. SWOT 분석
    competitor_summary = "\n".join([
        f"- {s['company']}: overlap {s['overlap']}, moat {s['moat']}"
        for s in scored_list
    ])
    
    swot_prompt = f"""
투자 심사용 SWOT 분석 (각 5-7개, 구체적 근거 포함):

타겟: {target}
기술: {tech_blk.get('core_technology', 'N/A')}
차별화: {tech_blk.get('differentiation', '')}
리스크: {', '.join(tech_blk.get('tech_risks', []))}

경쟁사:
{competitor_summary}

시장: {market_eval.get('market', {}).get('market_size', 'N/A')}, CAGR {market_eval.get('market', {}).get('cagr', 'N/A')}

JSON 출력:
{{
  "strengths": ["영상 생성 특화 AI 모델로 경쟁사 대비 15% 우수", "..."],
  "weaknesses": ["GPU 비용이 매출 60%로 경쟁사 대비 2배", "..."],
  "opportunities": ["시장 CAGR 150% 성장", "..."],
  "threats": ["OpenAI 경쟁으로 마진 50% 축소 위험", "..."]
}}
"""
    
    response = llm.invoke([HumanMessage(content=swot_prompt)])
    swot_data = extract_json_from_llm_response(response.content)
    
    print(f"  ✓ SWOT 완료")
    
    # 5. 최종 출력
    output = {
        "company": target,
        "competitors_analysis": scored_list,
        "swot": swot_data,
        "generated_at": datetime.now().isoformat()
    }
    
    # State 업데이트
    state_sources = state.get("sources", {})
    state_sources["competitor"] = list(set(competitor_sources))  # 중복 제거
    
    return {
        **state,
        "competitor": output,
        "sources": state_sources
    }