# agents/market.py
from typing import Dict, Any, List
import json
from pathlib import Path

from langchain_openai import ChatOpenAI
from langchain.retrievers import EnsembleRetriever
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


def _web_search(query: str, max_results: int = 3) -> List[str]:
    """웹 검색"""
    try:
        from langchain_community.tools.tavily_search import TavilySearchResults
        search = TavilySearchResults(max_results=max_results)
        results = search.invoke({"query": query})
        return [r.get("content", "") for r in results if r.get("content")]
    except Exception:
        return []


def market_eval(state: GraphState) -> GraphState:
    """
    시장 분석 노드
    
    입력:
        - current_company: 현재 분석 중인 회사명
        - discovery: 기업 탐색 결과
    
    출력:
        - market_eval: {market, traction, business}
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
    
    print(f"[시장 분석] 시작: {current_company}")
    
    # 1. Vector DB 검색
    context_parts = []
    try:
        index_dir = Path("faiss_index")
        embeddings = BgeEmbeddings(
            model_name="BAAI/bge-base-en-v1.5",
            device="cpu",
            normalize=True
        )
        
        if index_dir.exists():
            vectorstore = FAISS.load_local(
                str(index_dir),
                embeddings,
                allow_dangerous_deserialization=True
            )
            
            similarity = vectorstore.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4}
            )
            mmr = vectorstore.as_retriever(
                search_type="mmr",
                search_kwargs={"k": 4, "lambda_mult": 0.1}
            )
            retriever = EnsembleRetriever(
                retrievers=[similarity, mmr],
                weights=[0.7, 0.3]
            )
            
            question = f"{current_company} market analysis TAM SAM CAGR"
            docs = retriever.invoke(question)
            
            if docs:
                vector_context = "\n\n".join([
                    doc.page_content[:500] for doc in docs if doc.page_content
                ])
                context_parts.append(f"[Vector DB]\n{vector_context}")
                print(f"  ✓ Vector DB: {len(docs)}개 문서")
        
    except Exception as e:
        print(f"  ⚠ Vector DB 실패: {e}")
    
    # 2. 웹 검색
    queries = _build_search_queries([target_item])
    for query in queries[:5]:
        snippets = _web_search(query, max_results=3)
        if snippets:
            web_context = f"[검색 쿼리] {query}\n" + "\n".join(snippets)
            context_parts.append(web_context)
    
    print(f"  ✓ 웹 검색 완료")
    
    # 3. LLM 분석
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    
    system_prompt = (
        "You are a venture capital associate evaluating a startup's market potential. "
        "Prioritize evidence from the supplied context, but when the context is silent, "
        "use well-known market knowledge or reasoned estimates and clearly mark them as such. "
        "Respond strictly in JSON following this schema, and write every value in Korean.\n"
        f"{MARKET_JSON_SCHEMA}\n"
        "반드시 market.market_size에 TAM/SAM(USD) 값을 포함하고, market.cagr에는 성장률 % 값을,"
        " business.revenue_model 또는 business.monetization_stage에는 ARR/연 매출 추정치를 포함하라."
        " 수치가 부족하면 합리적 추정을 제공하고 '(estimated)'와 근거를 함께 표기하라."
        " Do not leave any field empty; when data is unavailable, write 'unknown' or a short note such as"
        " 'insufficient context' or '(estimated)'. For list fields, return at least one string (e.g., ['unknown'])."
    )
    
    items_json = json.dumps([target_item], ensure_ascii=False, indent=2)
    context_text = "\n\n".join(context_parts) if context_parts else "No external context provided."
    
    user_prompt = (
        f"스타트업 기본 정보(JSON):\n{items_json}\n\n"
        f"질문: 이 스타트업의 시장성과 투자 현황을 분석해 줘\n\nContext:\n{context_text}"
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
                "funding": target_item.get("funding_status", "unknown"),
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
    
    return {
        # **state,
        "market_eval": market_data
    }