# scripts/build_market_vectordb.py
"""
PDF → FAISS 변환 (LangChain 없이)
시장 리서치 보고서를 FAISS 벡터 DB로 변환
"""

import os
import pickle
from pathlib import Path
from typing import List, Dict, Any
import PyPDF2
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss


# 산업별 키워드
INDUSTRY_KEYWORDS = {
    "Healthcare": ["health", "medical", "patient", "diagnosis", "clinical", "hospital", "healthcare", "의료", "환자"],
    "Finance": ["finance", "banking", "payment", "fintech", "investment", "trading", "금융", "은행"],
    "Marketing": ["marketing", "advertising", "customer", "brand", "campaign", "마케팅", "광고"],
    "Education": ["education", "learning", "student", "teacher", "course", "교육", "학습"],
    "Gaming": ["game", "gaming", "player", "esports", "게임"],
    "Media": ["media", "content", "video", "audio", "entertainment", "미디어", "콘텐츠"],
}


class Document:
    """문서 클래스"""
    def __init__(self, page_content: str, metadata: Dict[str, Any]):
        self.page_content = page_content
        self.metadata = metadata


def extract_text_from_pdf(pdf_path: str) -> List[Document]:
    """PDF에서 텍스트 추출 (페이지별)"""
    documents = []
    
    print(f"📄 PDF 읽는 중: {pdf_path}")
    
    with open(pdf_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        total_pages = len(pdf_reader.pages)
        
        print(f"  총 {total_pages}페이지")
        
        for page_num, page in enumerate(pdf_reader.pages, start=1):
            text = page.extract_text()
            
            if text.strip():  # 빈 페이지 제외
                # 산업 태깅
                industries = tag_industries(text)
                
                doc = Document(
                    page_content=text,
                    metadata={
                        "source_file": os.path.basename(pdf_path),
                        "page": page_num,
                        "industries": industries if industries else ["General"]
                    }
                )
                documents.append(doc)
                
                if page_num % 10 == 0:
                    print(f"  ✓ {page_num}/{total_pages} 페이지 처리 완료")
    
    print(f"✅ 총 {len(documents)}개 페이지 추출 완료")
    return documents


def tag_industries(text: str) -> List[str]:
    """텍스트에서 관련 산업 태깅"""
    text_lower = text.lower()
    matched_industries = []
    
    for industry, keywords in INDUSTRY_KEYWORDS.items():
        if any(keyword.lower() in text_lower for keyword in keywords):
            matched_industries.append(industry)
    
    return matched_industries


def split_documents(documents: List[Document], chunk_size: int = 800, overlap: int = 150) -> List[Document]:
    """문서를 청크로 분할"""
    chunks = []
    
    print(f"✂️ 문서 분할 중 (청크 크기: {chunk_size}, 오버랩: {overlap})")
    
    for doc in documents:
        text = doc.page_content
        
        # 청크 생성
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunk_text = text[start:end]
            
            # 마지막이 아니면 마지막 완전한 문장까지만
            if end < len(text):
                last_period = chunk_text.rfind('.')
                if last_period > chunk_size // 2:  # 청크의 절반 이상에서 찾으면
                    end = start + last_period + 1
                    chunk_text = text[start:end]
            
            chunks.append(Document(
                page_content=chunk_text.strip(),
                metadata=doc.metadata.copy()
            ))
            
            start = end - overlap
    
    print(f"✅ {len(chunks)}개 청크 생성 완료")
    return chunks


def create_faiss_index(
    documents: List[Document],
    model_name: str = "BAAI/bge-base-en-v1.5",
    output_dir: str = "./faiss_market_index"
) -> None:
    """FAISS 인덱스 생성"""
    
    print(f"🔄 임베딩 모델 로드 중: {model_name}")
    model = SentenceTransformer(model_name)
    
    # 텍스트 추출
    texts = [doc.page_content for doc in documents]
    
    print(f"🔄 {len(texts)}개 텍스트 임베딩 중...")
    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        show_progress_bar=True,
        batch_size=32
    )
    
    # FAISS 인덱스 생성
    dimension = embeddings.shape[1]
    print(f"🔄 FAISS 인덱스 생성 중 (차원: {dimension})")
    
    index = faiss.IndexFlatIP(dimension)  # Inner Product (코사인 유사도)
    index.add(embeddings.astype('float32'))
    
    # 저장
    os.makedirs(output_dir, exist_ok=True)
    
    # FAISS 인덱스 저장
    index_path = os.path.join(output_dir, "index.faiss")
    faiss.write_index(index, index_path)
    print(f"💾 FAISS 인덱스 저장: {index_path}")
    
    # 메타데이터 저장
    metadata = {
        "documents": [
            {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
            for doc in documents
        ],
        "model_name": model_name
    }
    
    metadata_path = os.path.join(output_dir, "index.pkl")
    with open(metadata_path, 'wb') as f:
        pickle.dump(metadata, f)
    print(f"💾 메타데이터 저장: {metadata_path}")
    
    print(f"✅ FAISS DB 생성 완료: {output_dir}")
    print(f"  - 총 문서: {len(documents)}개")
    print(f"  - 벡터 차원: {dimension}")


def main():
    """메인 실행 함수"""
    
    # PDF 경로 (환경에 맞게 수정)
    pdf_path = "./data/ai-dossier-r.pdf"
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF 파일을 찾을 수 없습니다: {pdf_path}")
        print(f"   './data/ai-dossier-r.pdf' 경로에 PDF를 배치하세요.")
        return
    
    print("=" * 60)
    print("🚀 시장 리서치 FAISS DB 생성 시작")
    print("=" * 60)
    
    # 1. PDF에서 텍스트 추출
    documents = extract_text_from_pdf(pdf_path)
    
    # 2. 청크로 분할
    chunks = split_documents(documents, chunk_size=800, overlap=150)
    
    # 3. FAISS 인덱스 생성
    create_faiss_index(
        chunks,
        model_name="BAAI/bge-base-en-v1.5",
        output_dir="./faiss_market_index"
    )
    
    print("\n" + "=" * 60)
    print("✅ 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()