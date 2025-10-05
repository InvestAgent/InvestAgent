# 🤖 Agents 상세 설명

이 프로젝트는 AI 스타트업의 투자 가능성을 자동 평가하기 위해 **6개의 전문 에이전트**가 모듈형으로 동작합니다.  
각 에이전트는 입력 → 처리 → 산출 단계를 가지며, 전체 파이프라인은 아래 순서로 연결됩니다:

1. 🔍 스타트업 탐색  
2. 🧠 기술 요약  
3. 📈 시장성 평가  
4. 🥊 경쟁사 비교  
5. 🚀 투자 판단  
6. 📄 보고서 생성

---

## 🤖 : Agents
### 🔍 스타트업 탐색 에이전트
**목적:** 웹 및 문서 기반 스타트업 정보 수집 및 정제
1. 쿼리 재구성: 사용자의 자연어 입력을 키워드 중심 쿼리로 변환
2. 병렬 웹 검색: Tavily API로 스타트업/CEO 정보 동시 수집
3. 벡터 DB 생성
   * Chunking: chunk_size=800, overlap=150
   * Embedding: HuggingFace 모델 → FAISS 저장
4. RAG 기반 정보 추출: 의미적으로 유사한 텍스트 조각을 LLM에 전달
5. 데이터 보완 및 정제: 누락된 CEO 정보 자동 보완, 불필요 텍스트 제거
6. JSON 결과 및 벡터 DB 업데이트: 최신 정보 반영 및 저장
   
### 🔄 RAG 파이프라인 (정리)

### 전체 흐름
웹 검색 → 벡터 DB 구축 → 관련 문서 검색 → LLM 정보 추출 → 데이터 보완

### 5단계 프로세스

#### 1️⃣ 웹 검색
- Tavily API로 병렬 검색 (일반 쿼리 + CEO 특화 쿼리)
- 최대 24개 문서 수집 및 중복 제거

#### 2️⃣ 벡터 DB 구축
- 문서를 800자 청크로 분할 (150자 오버랩)
- BGE 임베딩 모델로 벡터화
- FAISS에 저장 (MMR 검색 설정)

#### 3️⃣ 관련 문서 검색
- MMR 알고리즘으로 관련성 높은 15개 청크 선택
- lambda=0.7 (관련성 70% + 다양성 30%)

#### 4️⃣ 정보 추출
- 검색된 문서를 컨텍스트로 GPT-4o-mini 호출
- Pydantic 스키마로 구조화된 JSON 생성
- 2-5개 스타트업 정보 반환

#### 5️⃣ 데이터 보완
- 누락된 CEO 정보 GPT 웹 검색으로 보완
- 정규식으로 이름 정제 (직함 제거)
- 보완된 데이터 벡터 DB에 재저장

### 핵심 특징
- ⚡ **병렬 처리**: 웹 검색 2개, CEO 보완 3개 동시 실행
- 💾 **쿼리 캐싱**: MD5 해시로 중복 검색 방지
- 🎯 **구조화 출력**: Pydantic으로 데이터 품질 보장
---
### 🧠  기술 요약 에이전트
**목적:** 핵심 기술 요약 및 경쟁 환경 분석
1. LLM 기반 질의 생성: 경쟁사·분석 항목을 포함한 검색 질의 자동 생성
2. 다중 웹 검색 및 필터링: 다양한 질의를 한 번에 처리
3. 구조화된 요약 생성: 정량 지표 및 URL 포함
4. JSON 매핑 강화: URL과 지표를 명시적으로 JSON 필드에 삽입
---
### :chart_with_upwards_trend: 시장성 평가 에이전트
**목적:** 시장 규모·성장성·수요를 정량·정성적으로 평가
* FAISS + BGE 임베딩 기반 사내 리서치 문서 활용
* EnsembleRetriever로 핵심 인사이트 추출
* Tavily, GOOGLE_CES를 통해 검색 자동 보강 → TAM, CAGR, 수요 요인 채움
* 컨텍스트 부족 시 합리적 추정치 명시
---
### 🥊 경쟁사 비교 에이전트
**목적:** 경쟁 환경 분석 및 차별화 전략 도출
* 벡터 DB + 웹 검색으로 경쟁사 4곳 자동 발굴 (스타트업 2곳, 대기업 2곳)
* 정량 평가 지표
  * :bar_chart: 시장 중복도 (Overlap)
  * :bulb: 차별성 (Differentiation)
  * :european_castle: 진입장벽 (Moat)
* VC 관점의 SWOT 분석 생성

* 🔄 동작 흐름 (6단계)
1. **[입력] Tech Agent + Market Agent 결과**  
   ↓  
2. **initialize_state** – 입력 데이터 파싱 및 State 초기화  
   ↓  
3. **search_competitors_hybrid** – 벡터 DB 검색(스타트업 2곳) + 부족 시 웹 검색 보완 + 대기업 2곳 선정  
   ↓  
4. **web_research_competitors** – 각 경쟁사별 제품·고객·투자 등 리서치  
   ↓  
5. **analyze_competitive_positioning** – Overlap, Differentiation, Moat 정량 평가 + Positioning 한 줄 요약  
   ↓  
6. **generate_swot_analysis** – VC 관점 SWOT 생성 (정량 근거 포함)  
   ↓  
7. **finalize_output** – JSON 형태 최종 결과 출력  

* 🔍 경쟁사 발굴 전략 (Hybrid + RAG)
- **Vector DB (FAISS)**  
  - HuggingFace BGE-base-en-v1.5 임베딩 기반  
  - 사전 구축된 스타트업 DB에서 유사 기업 2곳 검색  
- **웹 검색 보완 (RAG Retrieval)**  
  - Tavily Search API + GPT-4o-mini 활용  
  - Vector DB 부족 시 자동 실행, 중복 기업 제외  
- **대기업 후보군**  
  - OpenAI, Google, Meta, Microsoft, Adobe, Amazon, Anthropic, Stability AI  
  - GPT-4o-mini reasoning 기반 2곳 선정  

* 📝 SWOT 분석 생성 원칙
- **투자 판단 중심** (VC 의사결정 활용 목적)  
- **정량적 근거 필수** (추상적 표현 금지, 수치 기반)  
- **각 항목 5~7개 작성**  

- **Strengths (강점)** – 경쟁사 대비 우월한 점, 정량 근거 포함  
- **Weaknesses (약점)** – 구조적 리스크, 개선 어려움  
- **Opportunities (기회)** – 시장 성장, 틈새 기회, 파트너십 가능성  
- **Threats (위협)** – 대기업 진입, 규제, 기술 commoditization 리스크  
---
## :rocket: Startup Investment Decision Engine
정량 지표는 계산, 정성 평가는 LLM 해석으로 처리하여 스타트업 투자 판단을 자동화하는 엔진입니다.
---
### :bar_chart: 평가 가중치
| 항목      | 비중  | 주요 요소                        |
| ------- | --- | ---------------------------- |
| :chart_with_upwards_trend: 시장성  | 35% | TAM, CAGR, Problem-fit (LLM) |
| :brain: 기술력  | 25% | 성능, IP, 확장성                  |
| :boxing_glove: 경쟁우위 | 20% | 차별성, Moat, 포지셔닝 (LLM)        |
| :briefcase: 실적   | 10% | ARR, 파트너십, 펀딩                |
| :moneybag: 투자조건 | 10% | 밸류에이션, 지분 구조                 |
---
### :gear: 스코어 계산
Final Score = Σ(영역 점수 × 가중치) – Risk Penalty
---
### :white_check_mark: 투자 판단 규칙
| 점수      | 판단        |
| ------- | --------- |
| ≥ 70    | :white_check_mark: 투자 권고   |
| 60 ~ 69 | :warning: 조건부 투자 |
| < 60    | :x: 재검토 필요  |
---
### :compass: 투자의견 생성 (LLM)
투자 판단 결과가 ‘투자 권고’ 계열일 때만 보고서를 생성하여 불필요한 산출물을 줄이고 집중도를 유지합니다.
기술·시장·경쟁·비즈니스 블록에서 KPI, SWOT, 차별화 포인트를 추출해 HTML 템플릿에 자동 매핑하고, 출처 URL을 정제하여 참고 자료를 구성합니다. 이후 HTML을 PDF로 렌더링해 보고서를 완성합니다.
---

## 📄 보고서 생성 에이전트

**목적:** 투자 판단이 ‘투자 권고’ 계열일 경우 자동 보고서를 생성하여 의사결정 지원

**주요 기능:**

- 각 에이전트 산출물을 집계하여 KPI, SWOT, 경쟁 포인트, 차별화 요소 수집  
- HTML 템플릿에 분석 내용을 자동 삽입  
- 참고 자료(URL, 기사, 논문 등) 정제 및 첨부  
- HTML → PDF 변환으로 최종 투자 보고서 생성

---

## 📎 Appendix: Scoring Details

### 📈 시장 (35%)
- TAM: 로그 스케일 적용 (10B ~ 1000B → 0 ~ 100점)  
- CAGR: 선형 스케일 적용 (25% = 100점 기준)  
- Problem-fit: LLM 평가 (0~5점 → ×20 변환)

### 🧠 기술 (25%)
- SOTA 성능: 초과분 % → 가산점 반영  
- 체크리스트: API, 멀티테넌시, SDK 등 항목별 0/1 평가  
- IP 상태: 등록 = 85점, 출원 = 75점, 없음 = 중립  
- 확장성: 산업 확장성 언급 시 +10~20 보정

### 🥊 경쟁 (20%)
- 차별성 & Moat: 0~10 점수 → ×10  
- Overlap Penalty: (평균 Overlap – 5) × 5 감점  
- 포지셔닝: LLM 평가 (0~5점 → ×20 변환)

### 💼 실적 (10%)
- ARR: 완화 스케일 (50M USD = 100점 기준, 소규모라도 50점 기본 보장)  
- 파트너십: BigTech/포춘500 = +20, 일반 = +10  
- 펀딩 단계: Series B 이상 = +10

### 💰 투자조건 (10%)
- 정보 없음: 기본 60점 (중립)

### ⚠️ 리스크 반영
- 각 Risk item = Severity × Likelihood × Weight  
- 합산값에 따라 –5% / –10% / –15% 최종 점수에서 감점
