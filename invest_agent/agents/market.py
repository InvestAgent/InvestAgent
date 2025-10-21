# agents/market.py
from typing import Dict, Any, List, Tuple  # Tuple 추가
import json
from pathlib import Path

from langchain_openai import ChatOpenAI
# from langchain_community.retrievers import EnsembleRetriever
from langchain_community.vectorstores import FAISS
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer

from invest_agent.states import GraphState


class BgeEmbeddings(Embeddings):
    """BGE 임베딩 래퍼"""
    def __init__(self, model_name: str, device: str = "cpu", normalize: bool = True):
        self._model = SentenceTransformer(model_name, device=device)
        self._normalize = normalize

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=self._normalize)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text, normalize_embeddings=self._normalize)
        return embedding.tolist()


MARKET_JSON_SCHEMA = (
    '{\n'
    '  "market": {\n'
    '    "market_size": "",\n'
    '    "cagr": "",\n'
    '    "problem_fit": "",\n'
    '    "demand_drivers": []\n'
    '  },\n'
    '  "traction": {\n'
    '    "funding": "",\n'
    '    "investors": [],\n'
    '    "partnerships": []\n'
    '  },\n'
    '  "business": {\n'
    '    "revenue_model": "",\n'
    '    "pricing_examples": "",\n'
    '    "customer_segments": [],\n'
    '    "monetization_stage": ""\n'
    '  }\n'
    '}'
)


def _build_search_queries(items: List[dict]) -> List[str]:
    """검색 쿼리 생성"""
    if not items:
        return ["startup market size TAM SAM"]
    
    primary = items[0]
    startup = primary.get("startup_name", "")
    industry = primary.get("industry", "")
    
    queries = []
    if industry:
        queries.extend([
            f"{industry} total addressable market TAM SAM USD",
            f"{industry} CAGR 성장률",
            f"{industry} ARR 매출"
        ])
    
    if startup:
        queries.extend([
            f"{startup} total addressable market TAM USD",
            f"{startup} serviceable available market SAM USD",
            f"{startup} CAGR 성장률",
            f"{startup} ARR revenue"
        ])
    
    return queries


def _web_search(query: str, max_results: int = 3) -> Tuple[List[str], List[str]]:  # 반환 타입 수정
    """
    웹 검색 - 콘텐츠와 URL을 함께 반환
    
    Returns:
        (contents, urls) 튜플
    """
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        search = TavilySearchResults(max_results=max_results)
        results = search.invoke({"query": query})
        
        contents = []
        urls = []
        for r in results:
            if r.get("content"):
                contents.append(r["content"])
            if r.get("url"):
                urls.append(r["url"])
        
        return contents, urls
    except Exception:
        return [], []


def market_eval(state: GraphState) -> GraphState:
    """
    시장 분석 노드
    
    입력:
        - current_company: 현재 분석 중인 회사명
        - discovery: 기업 탐색 결과 (industry 포함)
    
    출력:
        - market_eval: {market, traction, business}
        - sources["market"]: 참고한 출처 URL/파일 리스트
    """
    current_company = state.get("current_company", "")
    discovery_items = state.get("discovery", {}).get("items", [])
    
    # 현재 회사 데이터 찾기
    target_item = None
    for item in discovery_items:
        if item.get("startup_name") == current_company:
            target_item = item
            break
    
    if not target_item:
        target_item = discovery_items[0] if discovery_items else {}
    
    industry = target_item.get("industry", "General")
    print(f"[시장 분석] 시작: {current_company} (산업: {industry})")
    
    market_sources = []  # 출처 수집용
    context_parts = []

    # 1. FAISS에서 산업별 시장 데이터 검색
    try:
        index_dir = Path("faiss_market_index")
        
        if not index_dir.exists():
            print(f"  ⚠️ FAISS DB 없음. scripts/build_market_vectordb.py를 먼저 실행하세요.")
        else:
            embeddings = BgeEmbeddings(
                model_name="BAAI/bge-base-en-v1.5",
                device="cpu",
                normalize=True
            )
            
            vectorstore = FAISS.load_local(
                str(index_dir),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            # 산업별 시장 데이터 검색 쿼리
            search_queries = [
                f"{industry} AI market size TAM SAM",
                f"{industry} generative AI CAGR growth",
                f"{industry} AI adoption trends",
                f"{current_company} market analysis"
            ]
            
            all_docs = []
            for query in search_queries:
                docs = vectorstore.similarity_search(query, k=3)
                all_docs.extend(docs)
            
            # 중복 제거 및 산업 필터링
            seen_content = set()
            filtered_docs = []
            
            for doc in all_docs:
                content_hash = hash(doc.page_content[:100])
                if content_hash not in seen_content:
                    # 해당 산업과 관련된 문서만 선택
                    doc_industries = doc.metadata.get("industries", [])
                    if industry in doc_industries or "General" in doc_industries:
                        seen_content.add(content_hash)
                        filtered_docs.append(doc)
            
            if filtered_docs:
                # 상위 5개만 사용
                top_docs = filtered_docs[:5]
                
                vector_context = "\n\n".join([
                    f"[{doc.metadata.get('source', 'N/A')} - Page {doc.metadata.get('page', 'N/A')}]\n"
                    f"{doc.page_content[:600]}"
                    for doc in top_docs
                ])
                
                context_parts.append(f"[시장 리서치 보고서 - {industry} 산업]\n{vector_context}")
                
                # 출처 수집
                for doc in top_docs:
                    source = doc.metadata.get("source_file", "시장 리서치 보고서")
                    if source not in market_sources:
                        market_sources.append(source)
                
                print(f"  ✓ FAISS 검색: {len(top_docs)}개 관련 섹션 발견")
            else:
                print(f"  ⚠️ {industry} 산업 관련 데이터 없음")
    
    except Exception as e:
        print(f"  ⚠️ FAISS 검색 실패: {e}")
    
    # 2. 웹 검색 (추가 최신 정보)
    queries = _build_search_queries([target_item])
    for query in queries[:3]:  # 3개로 줄임 (PDF가 메인 출처)
        snippets, urls = _web_search(query, max_results=2)  # 2개로 줄임
        if snippets:
            web_context = f"[웹 검색: {query}]\n" + "\n".join(snippets)
            context_parts.append(web_context)
            market_sources.extend(urls)
    
    print(f"  ✓ 웹 검색 완료")
    print(f"  ✓ 총 출처: {len(market_sources)}개")
    
    # 3. LLM 분석
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    system_prompt = (
        f"You are a venture capital associate evaluating a {industry} startup's market potential. "  # industry 추가
        "Prioritize evidence from the market research report context. "  # 우선순위 명시
        "Respond strictly in JSON following this schema, and write every value in Korean.\n"
        f"{MARKET_JSON_SCHEMA}\n"
        "반드시 market.market_size에 TAM/SAM(USD) 값을 포함하고, market.cagr에는 성장률 % 값을,"
        " business.revenue_model 또는 business.monetization_stage에는 ARR/연 매출 추정치를 포함하라."
        " 시장 리서치 보고서의 구체적 수치를 최우선으로 사용하라."  # 보고서 우선 명시
        " 수치가 부족하면 합리적 추정을 제공하고 '(estimated)'와 근거를 함께 표기하라."
        " Do not leave any field empty; when data is unavailable, write 'unknown' or a short note such as"
        " 'insufficient context' or '(estimated)'. For list fields, return at least one string (e.g., ['unknown'])."
    )
    
    items_json = json.dumps([target_item], ensure_ascii=False, indent=2)
    context_text = "\n\n".join(context_parts) if context_parts else "No external context provided."
    
    user_prompt = (
        f"스타트업 기본 정보:\n{items_json}\n\n"
        f"산업: {industry}\n\n"
        f"질문: 이 스타트업의 시장성과 투자 현황을 분석해 줘\n\n"
        f"Context:\n{context_text}"
    )
    
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    # JSON 파싱
    try:
        content = response.content.strip()
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        content = content.strip()
        
        market_data = json.loads(content)
        print(f"  ✓ 시장 분석 완료")
        
    except json.JSONDecodeError as e:
        print(f"  ⚠ JSON 파싱 실패: {e}")
        market_data = {
            "market": {
                "market_size": "unknown",
                "cagr": "unknown",
                "problem_fit": target_item.get("technology_description", ""),
                "demand_drivers": ["unknown"]
            },
            "traction": {
                "funding": target_item.get("funding_details", "unknown"),  # funding_status → funding_details
                "investors": ["unknown"],
                "partnerships": ["unknown"]
            },
            "business": {
                "revenue_model": "unknown",
                "pricing_examples": "unknown",
                "customer_segments": ["unknown"],
                "monetization_stage": "초기"
            }
        }
    
    # State 업데이트
    state_sources = state.get("sources", {})
    state_sources["market"] = list(set(market_sources))  # 중복 제거
    
    return {
        "market_eval": market_data,
        "sources": state_sources
    }