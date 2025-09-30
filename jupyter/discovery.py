import os
import json
import re
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError
from langchain_openai import ChatOpenAI
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.vectorstores.utils import filter_complex_metadata
from langchain_community.retrievers import TavilySearchAPIRetriever
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter


load_dotenv()

def check_api_keys():
    openai_key = os.getenv("OPENAI_API_KEY")
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not openai_key:
        print("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
        return False
    if not tavily_key:
        print("❌ TAVILY_API_KEY가 설정되지 않았습니다.")
        return False
    print("✅ API 키가 올바르게 설정되었습니다.")
    return True


class IndustryEnum(str, Enum):
    HEALTHCARE = "Healthcare"
    FINANCE = "Finance"
    MARKETING = "Marketing"
    EDUCATION = "Education"
    GAMING = "Gaming"
    MEDIA = "Media"


class FundingStageEnum(str, Enum):
    ANGEL = "Angel"
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"


class GenerativeAIStartup(BaseModel):
    startup_name: str = Field(description="Startup company name")
    technology_description: str = Field(description="2-3 line description of main technology and services")
    website: Optional[str] = Field(default="Information not available")
    founded_year: Optional[int] = Field(default=None)
    country: str
    ceo: str = Field(default="Information not available")
    funding_stage: FundingStageEnum
    funding_details: str
    industry: IndustryEnum
    core_technology: str
    source_urls: List[str]


class GenerativeAIStartupList(BaseModel):
    items: List[GenerativeAIStartup]


def extract_ceo_name_only(raw_text: str) -> str:
    if not raw_text or raw_text == "Information not available":
        return "Information not available"
    text = re.sub(r'\([^)]*\)', '', raw_text)
    keywords_to_remove = [
        'CEO', 'Chief Executive Officer', 'Founder', 'Co-Founder', 'Co-founder',
        'President', 'Director', 'Executive', 'Owner', 'Leader',
        '대표', '공동대표', '창립자', '공동창립자', '최고경영자',
        'founded by', 'established by', 'led by', 'current CEO',
        ':', '-', '|', 'and', '&', 'of', 'at'
    ]
    for keyword in keywords_to_remove:
        text = re.sub(rf'\b{keyword}\b', '', text, flags=re.IGNORECASE)
    if ',' in text:
        text = text.split(',')[0]
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) > 50 or len(re.findall(r'\d', text)) > 5 or len(text) < 2:
        return "Information not available"
    return text


class GenerativeAIStartupRAG:
    def __init__(self):
        if not check_api_keys():
            raise ValueError("API 키가 설정되지 않았습니다.")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            max_tokens=2000,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        self.structured_llm = self.llm.with_structured_output(GenerativeAIStartupList)

        self.web_search_llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )
        web_search_tool = {"type": "web_search_preview"}
        self.web_search_llm_with_tools = self.web_search_llm.bind_tools([web_search_tool])

        self.embeddings = HuggingFaceBgeEmbeddings(
            model_name="BAAI/bge-base-en-v1.5",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
            query_instruction="Represent this sentence for searching relevant passages: "
        )

        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=150,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )

        self.web_retriever = TavilySearchAPIRetriever(
            k=12,
            search_depth="advanced",
            include_generated_answer=True,
            include_raw_content=True,
            include_images=False,
            api_key=os.getenv("TAVILY_API_KEY"),
        )

        self.vector_store = None
        self.vector_retriever = None
        self.query_cache = {}

        self.prompt = ChatPromptTemplate.from_template("""
You are a generative AI startup analysis specialist.

From the provided web search information, identify up to 5 notable generative AI startups that meet ALL criteria below, preferably 3–5:
- Uses generative AI as core business
- Has launched or is developing real products/services
- **CRITICAL**: Has received funding at Angel, Pre-Seed, Seed, or Series A stage (NO Series B, C, D or later stages)
- Funding must be between 2015-2025
- **VERY IMPORTANT**: Must have current CEO information available


For EACH startup, extract:
- Company Name (official)
- Technology Description (2-3 sentences)
- Website (official)
- Founded Year
- Country (HQ)
- **CEO: THIS IS CRITICAL - Extract ONLY the current CEO's NAME**
  **IMPORTANT**: Return ONLY the person's name, WITHOUT any titles, roles, or descriptions
  **Examples of CORRECT format:**
    - "John Doe" (not "John Doe (CEO)")
    - "Jane Smith" (not "CEO Jane Smith")
    - "이승우" (not "이승우 대표")
  **What to look for:**
    - "CEO [Name]", "[Name] CEO", "led by [Name]", "current CEO is [Name]"
    - Korean: "대표 [Name]", "[Name] 대표", "최고경영자 [Name]"
  **If multiple CEOs or co-CEOs, list first name only**
- Funding Stage: **MUST BE ONE OF**: Angel, Pre-Seed, Seed, Series A
- Funding Details: Amount raised and key investors
- Industry: **MUST BE ONE OF**: Healthcare, Finance, Marketing, Education, Gaming, Media
- Core Technology: Main generative AI technology being used
- Source URLs (where the info is obtained)


**CRITICAL REQUIREMENTS**:
1. **PRIORITIZE startups where CEO information is clearly available**
2. **CEO field must contain ONLY the person's name - NO titles, NO roles, NO parentheses**
3. Funding Stage MUST be exactly one of: Angel, Pre-Seed, Seed, Series A
4. Industry MUST be exactly one of: Healthcare, Finance, Marketing, Education, Gaming, Media
5. DO NOT include companies that have raised Series B, C, D or beyond


<searched_information>
{context}
</searched_information>


User question: {input}


Return the result in Korean, and produce between 2 and 5 startups (ideally 5) that best fit the criteria.
Focus on startups in early funding stages (Angel to Series A only) **WITH AVAILABLE CEO NAME**.
""")

    def create_vector_db_from_web_search(self, query: str) -> None:
        print("🔍 웹에서 정보를 검색하고 있습니다...")
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            if query_hash in self.query_cache:
                print("✅ 캐시된 검색 결과를 사용합니다.")
                cached_docs = self.query_cache[query_hash]
                self._build_vector_store(cached_docs)
                return

            print("🔄 병렬 웹 검색을 시작합니다...")

            with ThreadPoolExecutor(max_workers=2) as executor:
                future_general = executor.submit(self.web_retriever.invoke, query)
                ceo_query = query + " CEO current chief executive officer 대표"
                future_ceo = executor.submit(self.web_retriever.invoke, ceo_query)

                web_docs = future_general.result()
                ceo_docs = future_ceo.result()

            seen_urls = set()
            all_docs = []

            for doc in web_docs + ceo_docs:
                url = doc.metadata.get('source', '')
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_docs.append(doc)

            if not all_docs:
                print("❌ 웹 검색 결과가 없습니다.")
                return

            print(f"📄 {len(all_docs)}개의 고유 웹 문서를 찾았습니다.")
            self.query_cache[query_hash] = all_docs
            self._build_vector_store(all_docs)

        except Exception as e:
            print(f"❌ 웹 검색 또는 벡터 DB 생성 중 오류 발생: {e}")
            raise

    def _build_vector_store(self, docs):
        print("🧹 복잡한 메타데이터를 필터링하고 있습니다...")
        filtered_docs = filter_complex_metadata(docs)
        print(f"✅ {len(filtered_docs)}개의 문서에서 메타데이터 필터링 완료")

        split_docs = self.text_splitter.split_documents(filtered_docs)
        print(f"✂️ 문서를 {len(split_docs)}개 청크로 분할했습니다.")

        print("🔄 FAISS 벡터 데이터베이스를 생성하고 있습니다...")
        self.vector_store = FAISS.from_documents(
            documents=split_docs,
            embedding=self.embeddings
        )

        self.vector_retriever = self.vector_store.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": 15,
                "fetch_k": 40,
                "lambda_mult": 0.7
            }
        )
        print("✅ FAISS 벡터 데이터베이스 생성 완료!")

    def add_enriched_startups_to_vector_store(self, startups: List[GenerativeAIStartup]) -> None:
        print("\n" + "=" * 60)
        print("💾 보완된 스타트업 데이터를 FAISS 벡터 DB에 추가 중...")
        print("=" * 60)

        if not self.vector_store:
            print("⚠️ 벡터 스토어가 초기화되지 않았습니다.")
            return

        enriched_docs = []

        for startup in startups:
            enriched_text = f"""
스타트업명: {startup.startup_name}
CEO: {startup.ceo}
설립년도: {startup.founded_year if startup.founded_year else '정보 없음'}
국가: {startup.country}
웹사이트: {startup.website}
산업: {startup.industry.value}
핵심 기술: {startup.core_technology}
투자 단계: {startup.funding_stage.value}
투자 세부사항: {startup.funding_details}
기술 설명: {startup.technology_description}
"""
            doc = Document(
                page_content=enriched_text,
                metadata={
                    "type": "enriched_startup_data",
                    "startup_name": startup.startup_name,
                    "ceo": startup.ceo,
                    "country": startup.country,
                    "industry": startup.industry.value,
                    "funding_stage": startup.funding_stage.value,
                    "source": "gpt_enriched_data"
                }
            )
            enriched_docs.append(doc)
            print(f"   ✅ {startup.startup_name} 데이터 준비 완료")

        try:
            print(f"\n🔄 {len(enriched_docs)}개의 보완된 문서를 임베딩 중...")
            self.vector_store.add_documents(enriched_docs)
            print(f"✅ {len(enriched_docs)}개의 보완된 스타트업 데이터가 벡터 DB에 추가되었습니다!")

            total_docs = self.vector_store.index.ntotal
            print(f"📊 현재 벡터 DB 총 문서 수: {total_docs}")

        except Exception as e:
            print(f"❌ 벡터 DB 추가 중 오류: {e}")

    def save_vector_store(self, save_path: str = "./faiss_enriched_index") -> None:
        if not self.vector_store:
            print("⚠️ 저장할 벡터 스토어가 없습니다.")
            return

        try:
            self.vector_store.save_local(save_path)
            print(f"💾 벡터 스토어가 저장되었습니다: {save_path}")
        except Exception as e:
            print(f"❌ 벡터 스토어 저장 중 오류: {e}")

    def load_vector_store(self, load_path: str = "./faiss_enriched_index") -> None:
        try:
            self.vector_store = FAISS.load_local(
                load_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            self.vector_retriever = self.vector_store.as_retriever(
                search_type="mmr",
                search_kwargs={
                    "k": 15,
                    "fetch_k": 40,
                    "lambda_mult": 0.7
                }
            )
            print(f"✅ 벡터 스토어가 로드되었습니다: {load_path}")
        except Exception as e:
            print(f"❌ 벡터 스토어 로드 중 오류: {e}")

    def sup_missing_ceo_with_gpt(self, company_name: str) -> str:
        print(f"🤖 GPT 웹 검색으로 {company_name}의 CEO 이름을 찾는 중...")

        try:
            search_prompt = f"""
You are an AI assistant with web search capabilities. 


**Task:** Find the current CEO of {company_name}


**CRITICAL INSTRUCTION:** Return ONLY the CEO's full name. Do NOT include:
- Titles (CEO, Chief Executive Officer, President, etc.)
- Roles (Founder, Co-Founder, etc.)
- Parentheses or brackets
- Additional descriptions
- Korean titles (대표, 공동대표, etc.)


**Examples of CORRECT responses:**
- "John Doe"
- "Jane Smith"
- "이승우"
- "김철수"


**Examples of INCORRECT responses:**
- "John Doe (CEO)" ❌
- "CEO: Jane Smith" ❌
- "이승우 대표" ❌
- "Founded by Mike Johnson" ❌


Search the web for {company_name}'s current CEO and return ONLY the person's name.
If the CEO information is not found, return exactly: "Information not available"


Do not include any explanations, titles, or additional text.
"""
            print(f"   🔎 GPT가 웹 검색을 시작합니다: {company_name} CEO")
            response = self.web_search_llm_with_tools.invoke(search_prompt)

            if hasattr(response, 'content'):
                if isinstance(response.content, list):
                    text_content = []
                    for block in response.content:
                        if isinstance(block, dict) and block.get('type') == 'text':
                            text_content.append(block.get('text', ''))
                    extracted_info = ' '.join(text_content).strip()
                else:
                    extracted_info = response.content.strip()
            else:
                extracted_info = str(response).strip()

            cleaned_ceo_name = extract_ceo_name_only(extracted_info)

            if cleaned_ceo_name != "Information not available":
                print(f"   ✅ CEO 이름 추출 성공: {cleaned_ceo_name}")
                return cleaned_ceo_name
            else:
                print(f"   ⚠️ CEO 정보를 찾지 못했습니다.")
                return "Information not available"

        except Exception as e:
            print(f"   ❌ GPT 웹 검색 중 오류: {e}")
            return "Information not available"

    def sup_startup_data(self, startup: GenerativeAIStartup) -> GenerativeAIStartup:
        print(f"\n{'='*60}")
        print(f"🔍 {startup.startup_name} 데이터 보완 시작")
        print(f"{'='*60}")

        if startup.ceo == "Information not available":
            print(f"📍 CEO 정보 누락 감지")
            sup_ceo = self.sup_missing_ceo_with_gpt(startup.startup_name)
            if sup_ceo != "Information not available":
                startup.ceo = sup_ceo
                print(f"✅ CEO 정보 업데이트: {sup_ceo}")
        else:
            print(f"📍 기존 CEO 정보 정리 중: {startup.ceo}")
            cleaned_ceo = extract_ceo_name_only(startup.ceo)
            if cleaned_ceo != startup.ceo:
                startup.ceo = cleaned_ceo
                print(f"✅ CEO 이름 정리 완료: {cleaned_ceo}")

        print(f"{'='*60}\n")
        return startup

    def search_startup(self, query: str, save_enriched_to_db: bool = True) -> GenerativeAIStartupList:
        if "한국" in query or "Korea" in query:
            search_query = f"{query} Korea generative AI startup CEO current chief executive 대표 angel seed series A 2015-2025"
        else:
            search_query = f"{query} generative AI startup CEO current chief executive angel seed series A 2020-2025"

        self.create_vector_db_from_web_search(search_query)

        if not self.vector_retriever:
            raise ValueError("벡터 리트리버가 생성되지 않았습니다.")

        print("🔗 커스텀 RAG 체인을 구성하고 있습니다...")

        def custom_rag_chain(inputs: dict) -> GenerativeAIStartupList:
            context_docs = self.vector_retriever.invoke(inputs["input"])
            context_text = "\n\n".join([doc.page_content for doc in context_docs])
            formatted_prompt = self.prompt.format(
                context=context_text,
                input=inputs["input"]
            )
            result = self.structured_llm.invoke(formatted_prompt)
            return result

        print("🤖 AI가 여러 스타트업을 분석하고 있습니다...")
        try:
            result = custom_rag_chain({"input": query})

            print("\n🔄 초기 추출된 CEO 정보 정리 중...")
            for startup in result.items:
                if startup.ceo != "Information not available":
                    cleaned = extract_ceo_name_only(startup.ceo)
                    if cleaned != startup.ceo:
                        print(f"   - {startup.startup_name}: '{startup.ceo}' -> '{cleaned}'")
                        startup.ceo = cleaned

            print("\n" + "=" * 60)
            print("🔄 GPT 웹 검색으로 누락된 CEO 정보를 보완 중...")
            print("=" * 60)

            with ThreadPoolExecutor(max_workers=3) as executor:
                sup_items = list(executor.map(self.sup_startup_data, result.items))

            result.items = sup_items

            if save_enriched_to_db:
                self.add_enriched_startups_to_vector_store(result.items)

            return result
        except ValidationError as ve:
            print(f"⚠️ 구조화 출력 검증 실패: {ve}")
            raise

    def cleanup(self):
        pass


def save_result_to_json(result: GenerativeAIStartupList, output_dir: str = "./results") -> str:
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"startup_analysis_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    result_dict = result.model_dump(exclude_none=True)
    output_data = {
        "generated_at": datetime.now().isoformat(),
        "total_startups": len(result.items),
        "data": result_dict
    }
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=4)
    print(f"💾 JSON 파일 저장 완료: {filepath}")
    return filepath


def main():
    rag_system = None
    try:
        rag_system = GenerativeAIStartupRAG()
        user_query = "2015년도 이후에 한국에서 설립되고 2025년 9월까지 운영중이며, CEO 정보가 있는 50명 미만의 생성형 AI 스타트업 찾아줘"

        print("=" * 60)
        print("🚀 생성형 AI 스타트업 검색 시스템 실행")
        print("=" * 60)

        result = rag_system.search_startup(user_query, save_enriched_to_db=True)

        if isinstance(result, GenerativeAIStartupList):
            print(json.dumps(result.model_dump(exclude_none=True), ensure_ascii=False, indent=2))
            save_result_to_json(result)
            rag_system.save_vector_store("./faiss_enriched_index")
        else:
            print("예상하지 못한 결과:", result)

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if rag_system:
            rag_system.cleanup()


if __name__ == "__main__":
    main()
