"""Market viability analysis agent using FAISS + EnsembleRetriever + ChatGPT."""
from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Sequence, Tuple, TypedDict

import json

from dotenv import load_dotenv

try:  # Prefer the standalone splitter package if available.
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # Fallback for older LangChain layouts.
    from langchain.text_splitter import RecursiveCharacterTextSplitter  # type: ignore

from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from langchain_openai import ChatOpenAI
from langchain_core.embeddings import Embeddings
from sentence_transformers import SentenceTransformer
from langchain_community.document_loaders import PyMuPDFLoader, TextLoader
from langchain_community.vectorstores import FAISS

try:  # Optional LangGraph support for graph orchestration.
    from langgraph.graph import END, StateGraph
except ImportError:  # LangGraph is optional; graph builder will fail gracefully.
    END = None  # type: ignore
    StateGraph = None  # type: ignore



class BgeEmbeddings(Embeddings):
    """Wrapper around SentenceTransformer for BGE models."""

    def __init__(
        self,
        model_name: str,
        device: str | None = None,
        normalize_embeddings: bool = True,
    ) -> None:
        self._model = SentenceTransformer(model_name, device=device or "cpu")
        self._normalize = normalize_embeddings

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, normalize_embeddings=self._normalize)
        return embeddings.tolist() if hasattr(embeddings, "tolist") else embeddings

    def embed_query(self, text: str) -> list[float]:
        embedding = self._model.encode(text, normalize_embeddings=self._normalize)
        return embedding.tolist() if hasattr(embedding, "tolist") else embedding



def _build_search_queries(items: List[dict], base_question: str) -> List[str]:
    if not items:
        return [base_question]

    primary = items[0]
    startup = primary.get("startup_name", "해당 스타트업")
    industry = primary.get("industry") or primary.get("sector") or ""

    queries = [base_question]
    if industry:
        queries.append(f"{industry} total addressable market TAM SAM USD")
        queries.append(f"{industry} CAGR 성장률")
        queries.append(f"{industry} ARR 매출")

    queries.extend(
        [
            f"{startup} total addressable market TAM USD",
            f"{startup} serviceable available market SAM USD",
            f"{startup} CAGR 성장률",
            f"{startup} ARR revenue",
        ]
    )

    return queries

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


class GraphState(TypedDict):
    """Shared state passed between retrieval and generation steps."""

    question: str
    context: str
    answer: str
    messages: List[Tuple[str, str]]
    relevance: str
    items: List[dict]


@dataclass
class MarketAnalysisDependencies:
    """Container for the core components required by the agent."""

    retriever: EnsembleRetriever
    web_search_fn: Callable[[str], List[str]]
    llm: ChatOpenAI


def _prepare_state(state: GraphState) -> GraphState:
    """Ensure the state has the required structure before running the agent."""

    prepared: GraphState = {
        "question": state.get("question", ""),
        "context": state.get("context", ""),
        "answer": state.get("answer", ""),
        "messages": list(state.get("messages", [])),
        "relevance": state.get("relevance", "unknown"),
        "items": list(state.get("items", [])),
    }

    if not prepared["question"].strip():
        raise ValueError("GraphState must include a non-empty 'question'.")

    if not prepared["messages"]:
        prepared["messages"] = [("user", prepared["question"])]

    return prepared


def _ensure_environment(vars_to_check: Iterable[str]) -> None:
    missing = [var for var in vars_to_check if not os.getenv(var)]
    if missing:
        joined = ", ".join(missing)
        raise EnvironmentError(f"Missing required environment variables: {joined}")


def _load_documents(doc_paths: Sequence[Path]) -> List[Document]:
    documents: List[Document] = []
    for path in doc_paths:
        resolved = path.expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"Document not found: {resolved}")
        if resolved.suffix.lower() == ".pdf":
            loader = PyMuPDFLoader(str(resolved))
            documents.extend(loader.load())
            continue

        elif resolved.suffix.lower() in {".txt", ".md", ".text"}:
            loader = TextLoader(str(resolved), autodetect_encoding=True)
        else:
            raise ValueError(f"Unsupported document type: {resolved.suffix}")
        documents.extend(loader.load())
    return documents


def _build_vectorstore(
    index_dir: Path,
    embeddings: Embeddings,
    doc_paths: Sequence[Path],
    recreate: bool,
) -> FAISS:
    if index_dir.exists() and not recreate:
        return FAISS.load_local(
            str(index_dir), embeddings, allow_dangerous_deserialization=True
        )

    docs = _load_documents(doc_paths)
    if not docs:
        raise ValueError("No documents supplied to build the FAISS index.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=700, chunk_overlap=150)
    splits = splitter.split_documents(docs)

    vectorstore = FAISS.from_documents(splits, embeddings)
    index_dir.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(index_dir))
    return vectorstore


def _build_ensemble_retriever(vectorstore: FAISS, top_k: int) -> EnsembleRetriever:
    similarity = vectorstore.as_retriever(
        search_type="similarity", search_kwargs={"k": top_k}
    )
    mmr = vectorstore.as_retriever(
        search_type="mmr", search_kwargs={"k": max(2, top_k), "lambda_mult": 0.1}
    )
    return EnsembleRetriever(retrievers=[similarity, mmr], weights=[0.7, 0.3])


def _build_web_search_fn(max_results: int) -> Callable[[str], List[str]]:
    try:
        from langchain_community.retrievers import TavilySearchAPIRetriever

        retriever = TavilySearchAPIRetriever(max_results=max_results)

        def tavily_search(query: str) -> List[str]:
            docs = retriever.get_relevant_documents(query)
            return [doc.page_content for doc in docs if doc.page_content]

        return tavily_search
    except Exception:
        try:
            from langchain_community.utilities import GoogleSearchAPIWrapper

            wrapper = GoogleSearchAPIWrapper()

            def google_search(query: str) -> List[str]:
                results = wrapper.results(query, num=max_results)
                snippets: List[str] = []
                for item in results:
                    title = item.get("title", "")
                    snippet = item.get("snippet", "")
                    link = item.get("link", "")
                    combined = " ".join(
                        part.strip()
                        for part in (title, snippet, link)
                        if part and part.strip()
                    )
                    if combined:
                        snippets.append(combined)
                return snippets

            return google_search
        except Exception:
            def stub_search(query: str) -> List[str]:
                return [
                    (
                        "[Web search unavailable] Summarize publicly known signals about "
                        f"'{query}' using the retrieved documents or general insight."
                    )
                ]

            return stub_search


def retrieve_from_vectordb(
    state: GraphState,
    retriever: EnsembleRetriever,
    verbose: bool = False,
) -> GraphState:
    question = state["question"]
    try:
        docs = retriever.invoke(question)
    except AttributeError:  # Backwards compatibility for older LangChain builds.
        docs = retriever.get_relevant_documents(question)
    if not docs:
        state["context"] = ""
        state["relevance"] = "none"
        state["messages"].append(("agent", "Vector store returned no passages."))
        return state

    body = "\n\n".join(
        doc.page_content.strip() for doc in docs if doc.page_content and doc.page_content.strip()
    )
    sources = [
        doc.metadata.get("source")
        or doc.metadata.get("file_path")
        or doc.metadata.get("path")
        for doc in docs
    ]
    footers = [f"Source: {src}" for src in sources if src]
    if footers:
        body = f"{body}\n\n" + "\n".join(footers)

    state["context"] = body
    state["relevance"] = "high"
    state["messages"].append(
        ("agent", f"Vector store supplied {len(docs)} candidate chunks.")
    )

    if verbose:
        print("[VectorDB chunks]", len(docs))
        print(body[:500])

    return state


def retrieve_from_web(
    state: GraphState,
    search_fn: Callable[[str], List[str]],
    queries: List[str],
) -> GraphState:
    aggregated: List[str] = []
    for query in queries:
        snippets = search_fn(query)
        if not snippets:
            continue
        header = f"[검색 쿼리] {query}"
        aggregated.append("\n".join([header, *snippets]))

    if not aggregated:
        state["context"] = ""
        state["relevance"] = "none"
        state["messages"].append(("agent", "Web search returned no additional evidence."))
        return state

    state["context"] = "\n\n".join(aggregated)
    state["relevance"] = "medium"
    state["messages"].append(
        ("agent", f"Web search contributed {len(aggregated)} supplemental snippets from targeted queries.")
    )
    return state


def llm_answer(state: GraphState, llm: ChatOpenAI) -> GraphState:
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
    context = state["context"] or "No external context provided."
    items_payload = json.dumps(state.get("items", []), ensure_ascii=False, indent=2)
    user_prompt = (
        f"스타트업 기본 정보(JSON):\n{items_payload}\n\n"
        f"질문: {state['question']}\n\nContext:\n{context}"
    )

    response = llm.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    state["answer"] = response.content.strip()
    state["messages"].append(("assistant", state["answer"]))
    return state


def market_analysis_step(
    state: GraphState,
    retriever: EnsembleRetriever,
    web_search_fn: Callable[[str], List[str]],
    llm: ChatOpenAI,
    *,
    use_web_fallback: bool = True,
    verbose: bool = False,
) -> GraphState:
    working_state = _prepare_state(state)
    question = working_state["question"]

    retrieve_from_vectordb(working_state, retriever, verbose=verbose)

    if use_web_fallback:
        queries = _build_search_queries(working_state.get("items", []), question)
        existing_context = working_state["context"]
        existing_relevance = working_state["relevance"]
        retrieve_from_web(working_state, web_search_fn, queries)
        if existing_context and working_state["context"]:
            working_state["context"] = "\n\n".join(
                [existing_context, working_state["context"]]
            )
        elif existing_context and not working_state["context"]:
            working_state["context"] = existing_context
            working_state["relevance"] = existing_relevance

    llm_answer(working_state, llm)
    return working_state


def run_agent(
    question: str,
    retriever: EnsembleRetriever,
    web_search_fn: Callable[[str], List[str]],
    llm: ChatOpenAI,
    use_web_fallback: bool = True,
    items: List[dict] | None = None,
    verbose: bool = False,
) -> GraphState:
    initial_state: GraphState = {
        "question": question,
        "context": "",
        "answer": "",
        "messages": [("user", question)],
        "relevance": "unknown",
        "items": list(items or []),
    }

    return market_analysis_step(
        state=initial_state,
        retriever=retriever,
        web_search_fn=web_search_fn,
        llm=llm,
        use_web_fallback=use_web_fallback,
        verbose=verbose,
    )


def create_market_analysis_dependencies(
    *,
    index_dir: Path,
    doc_paths: Sequence[Path],
    reindex: bool,
    embedding_model: str,
    embedding_device: str | None,
    top_k: int,
    llm_model: str,
    temperature: float,
    max_web_results: int,
) -> MarketAnalysisDependencies:
    doc_paths = list(doc_paths)

    embeddings = BgeEmbeddings(
        model_name=embedding_model,
        device=embedding_device,
        normalize_embeddings=True,
    )

    vectorstore = _build_vectorstore(index_dir, embeddings, doc_paths, reindex)
    retriever = _build_ensemble_retriever(vectorstore, top_k)
    web_search_fn = _build_web_search_fn(max_web_results)
    llm = ChatOpenAI(model=llm_model, temperature=temperature)

    return MarketAnalysisDependencies(
        retriever=retriever,
        web_search_fn=web_search_fn,
        llm=llm,
    )


def build_market_analysis_graph(
    dependencies: MarketAnalysisDependencies,
    *,
    use_web_fallback: bool = True,
    verbose: bool = False,
) -> Any:
    if StateGraph is None or END is None:  # pragma: no cover - optional dependency guard
        raise ImportError(
            "LangGraph is not installed. Run 'pip install langgraph' to use the graph builder."
        )

    graph = StateGraph(GraphState)

    def _market_node(state: GraphState) -> GraphState:
        return market_analysis_step(
            state=state,
            retriever=dependencies.retriever,
            web_search_fn=dependencies.web_search_fn,
            llm=dependencies.llm,
            use_web_fallback=use_web_fallback,
            verbose=verbose,
        )

    graph.add_node("market_analysis", _market_node)
    graph.set_entry_point("market_analysis")
    graph.add_edge("market_analysis", END)
    return graph.compile()


def _default_document_paths() -> List[Path]:
    """Provide the default corpus used to build the FAISS index."""

    candidate_paths = [
        Path("16-AgenticRAG/data/ai-dossier-r.pdf"),
        Path("data/ai-dossier-r.pdf"),
    ]

    for candidate in candidate_paths:
        if candidate.exists():
            return [candidate]

    return []


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the market potential analysis agent with FAISS + EnsembleRetriever."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default="이 스타트업의 시장성과 투자 현황을 분석해 줘",
        help=(
            "Investment question or hypothesis to investigate. "
            "Defaults to a general market viability analysis prompt."
        ),
    )
    parser.add_argument(
        "--index-dir",
        default="16-AgenticRAG/faiss_index",
        help="Directory to read or write the FAISS index (default: 16-AgenticRAG/faiss_index).",
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        default=None,
        help="Optional document paths to build the index when --reindex is set or the index is missing.",
    )
    parser.add_argument(
        "--reindex",
        action="store_true",
        help="Force rebuilding the FAISS index from the supplied documents.",
    )
    parser.add_argument(
        "--embedding-model",
        default="BAAI/bge-base-en-v1.5",
        help="Hugging Face BGE embedding model name (default: BAAI/bge-base-en-v1.5).",
    )
    parser.add_argument(
        "--embedding-device",
        default=None,
        help="Device for the embedding model; leave blank for auto-detection.",
    )
    parser.add_argument(
        "--items-file",
        type=Path,
        default=None,
        help="Optional JSON file containing a list of startup metadata dictionaries.",
    )
    parser.add_argument(
        "--llm-model",
        default="gpt-4o-mini",
        help="OpenAI chat model to use for generation (default: gpt-4o-mini).",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.0,
        help="Sampling temperature for the chat model (default: 0.0).",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=4,
        help="Number of top vector results to request from FAISS (default: 4).",
    )
    parser.add_argument(
        "--max-web-results",
        type=int,
        default=3,
        help="Number of snippets to pull from the web fallback (default: 3).",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable the web-search fallback even when the vector store is empty.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print retrieval diagnostics for debugging.",
    )
    args = parser.parse_args()

    load_dotenv()
    _ensure_environment(["OPENAI_API_KEY"])

    index_dir = Path(args.index_dir)
    doc_paths = (
        [Path(p) for p in args.docs]
        if args.docs is not None
        else _default_document_paths()
    )

    if not index_dir.exists() and not doc_paths:
        raise FileNotFoundError(
            "FAISS index is missing and no documents were provided to build it."
        )

    dependencies = create_market_analysis_dependencies(
        index_dir=index_dir,
        doc_paths=doc_paths,
        reindex=args.reindex,
        embedding_model=args.embedding_model,
        embedding_device=args.embedding_device,
        top_k=args.top_k,
        llm_model=args.llm_model,
        temperature=args.temperature,
        max_web_results=args.max_web_results,
    )

    items_payload: List[dict] = []
    if args.items_file:
        items_text = args.items_file.read_text(encoding="utf-8")
        loaded = json.loads(items_text)
        items_payload = loaded if isinstance(loaded, list) else [loaded]

    state = run_agent(
        question=args.question,
        retriever=dependencies.retriever,
        web_search_fn=dependencies.web_search_fn,
        llm=dependencies.llm,
        use_web_fallback=not args.no_web,
        items=items_payload,
        verbose=args.verbose,
    )

    print(state["answer"])


if __name__ == "__main__":
    main()
