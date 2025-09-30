# AI Startup Investment Evaluation Agent
본 프로젝트는 인공지능 스타트업에 대한 투자 가능성을 자동으로 평가하는 에이전트를 설계하고 구현한 실습 프로젝트입니다.

## Overview

- Objective : AI 스타트업의 기술력, 시장성, 리스크 등을 기준으로 투자 적합성 분석
- Method : AI Agent + Agentic RAG 
- Tools : 

## Features

- PDF 자료 기반 정보 추출 (예: IR 자료, 기사 등)
- 투자 기준별 판단 분류 (시장성, 팀, 기술력 등)
- 종합 투자 요약 출력 (예: 투자 유망 / 보류 / 회피)

## Tech Stack 

| Category   | Details                      |
|------------|------------------------------|
| Framework  | LangGraph, LangChain, Python |
| LLM        | GPT-4o-mini via OpenAI API   |
| Retrieval  | FAISS, Chroma                |

## Agents
 
- :돋보기:스타트업 탐색 에이전트 : 유명한 AI 스타트업 정보 수집
1. 쿼리 입력 및 재구성: 사용자가 자연어 쿼리를 입력하고 핵심 키워드를 쿼리에 자동으로 추가하여 검색 효율을 높였습니다.
2. 병렬 웹 검색: Tavily 검색 API를 활용해 웹 정보를 수집합니다. 이때, 스타트업 검색과 CEO 정보에 특화된 검색을 동시에 실행하여 다양한 정보를 빠르고 효율적으로 가져옵니다.
3. 실시간 벡터 DB 생성 (Real-time Vector DB Creation)
분할 (Chunking): chunk_size=800과 chunk_overlap=150으로 구성하였습니다.
임베딩 (Embedding): FAISS와 HuggingFace 임베딩 모델을 사용해 의미를 나타내는 벡터(숫자 배열)로 변환합니다.
인덱싱 (Indexing): 벡터들을 DB에 저장합니다.
4. RAG 기반 정보 추출: 사용자의 원본 쿼리와 의미적으로 가장 유사한 텍스트 조각들을 벡터 DB에서 찾아냅니다.
이 조각들을 '참고 자료(Context)'로 삼아, 상세한 지시가 담긴 프롬프트와 함께 **gpt-4o-mini**에게 전달합니다.
5. 데이터 자동 보완 및 정제
CEO 정보 보완: 만약 1차 추출에서 CEO 정보가 누락되었다면, 에이전트는 해당 스타트업의 CEO를 찾기 위해 GPT를 통해 웹 검색을 자동으로 수행합니다.
데이터 정제: 불필요한 정보가 포함된 데이터는 정규식을 통해 깔끔하게 정리합니다. (ex. 김규식 대표 -> 김규식)
6. 최종 결과 출력 및 벡터 DB 업데이트: JSON 출력: 모든 정보가 보완된 최종 결과를 화면에 출력하고, 타임스탬프가 포함된 JSON 파일로 저장합니다.
벡터 DB 업데이트: 이번 검색을 통해 새롭게 보완되고 정제된 고품질 데이터를 다시 벡터 DB에 추가하고 파일로 저장합니다.
- :압축:기술 요약 에이전트 :
1. LLM 기반 키워드 추출 & 질문 생성 강화
단순 키워드 추출 대신, 경쟁사와 분석 항목을 포함하는 검색 질의(Queries) 목록을 생성하도록 변경하여 웹 검색의 효율을 높입니다.
2. 웹 검색 및 결과 필터링
TavilySearchResults가 단일 문자열 쿼리뿐만 아니라 쿼리 리스트를 받도록 개선하여, 여러 개의 구체적인 검색 질의를 한 번에 처리하고 더 풍부한 결과를 얻도록 합니다
3. 구조화된 요약 및 근거 제시
요약 단계(summarize_web_results)에서 정량 지표와 근거 URL을 포함하여 요약을 생성하고, 최종 JSON 생성 단계(generate_tech_summary)에서 이를 더 정확하게 매핑하도록 프롬프트를 강화합니다.
4. 시스템 프롬프트 강화 (generate_tech_summary)
핵심 변화: LLM에게 웹 요약(web_summary)에서 URL과 정량 지표를 분리하여 JSON 필드에 삽입하라고 명확하게 지시합니다
- :막대_차트:시장성 평가 에이전트 :
FAISS + BGE 임베딩으로 구축한 사내 리서치 문서를 불러와 EnsembleRetriever로 핵심 통찰을 추출
Tavily 웹 검색을 자동 보강해 TAM, CAGR, 수요 요인 등 시장 데이터를 JSON 스키마에 맞게 채움
컨텍스트 부족 시 합리적 추정치를 명시해 투자 판단에 필요한 정량·정성 지표를 모두 제공
- :권투_글러브:경쟁사 비교 에이전트 :
Vector DB 기반 유사 스타트업 검색 + 웹 검색 보완으로 4개 경쟁사(스타트업 2개, 대기업 2개) 자동 발굴
시장 중복도(Overlap), 차별화(Differentiation), 진입장벽(Moat) 3가지 지표로 경쟁사별 정량 평가 (0~10점)
VC 투자 심사역 관점의 구체적·실행 가능한 SWOT 분석 생성
# :로켓: Startup Investment Decision Engine
> 정량은 **계산**, 정성은 **LLM 해석**으로 처리해
> 스타트업 투자 판단을 자동화하는 엔진입니다.
---
## :압정: Overview
- VC Scorecard에서 **창업자(30%) 제외** 후 자동화
- 정량 계산 + LLM 해석 → **재현성 + 설명력 확보**
---
## :나침반: Evaluation Weights
| 항목       | 비중 | 주요 요소                        |
|------------|------|----------------------------------|
| 시장성     | 35%  | TAM(이론적 최대 시장), CAGR, Problem-fit *(LLM)* |
| 기술력     | 25%  | 성능, IP, 확장성                |
| 경쟁우위   | 20%  | 차별성, Moat(경쟁우위), 포지셔닝 *(LLM)* |
| 실적       | 10%  | ARR(연간 반복 매출), 파트너십, 펀딩            |
| 투자조건   | 10%  | 밸류에이션, 지분 구조          |
---
## :톱니바퀴: Scoring Logic
```text
Final Score = Σ(영역 점수 × 가중치) – Risk Penalty
---
## :흰색_확인_표시: Decision Rules
| 점수   | 판단            |
|--------|------------------|
| ≥ 70   | :흰색_확인_표시: 투자 권고     |
| 60 ~ 69| :경고: 조건부 투자   |
| < 60   | :x: 재검토 필요   |
---
## :뇌: 투자의견 생성 (LLM)
```mermaid
flowchart TB
  A[요약 생성] --> B[투자 포인트] --> C[의견 문장화] --> D[보고서용 문체]
  투자 판단 결과가 'invest' 계열일 때만 보고서를 생성해 불필요한 산출물을 줄이고 집중도를 유지
기술·시장·경쟁·비즈니스 블록에서 KPI·SWOT·차별화 포인트를 추출해 HTML 템플릿에 자동 매핑
LangGraph state에 쌓인 출처 URL을 정제해 참고 자료를 구성하고, HTML→PDF 렌더링 옵션으로 전달용 보고서 완성

## Architecture
![에이전트 스크린샷](images/image.png)

## Directory Structure
```
├── data/                  # 스타트업 PDF 문서
├── agents/                # 평가 기준별 Agent 모듈
├── prompts/               # 프롬프트 템플릿
├── outputs/               # 평가 결과 저장
├── app.py                 # 실행 스크립트
└── README.md
```

## Contributors 

|                                   스타트업 탐색 에이전트                                    |                                  시장성 평가 에이전트                                  |                                  기술 요약 에이전트                                   |                           보고서 생성 에이전트                            |                                 경쟁사 비교 에이전트                                  |                                  투자 판단 에이전트                                   |
| :-------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------: | :----------------------------------------------------------------------: | :------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------: |
| <img src="https://avatars.githubusercontent.com/YunCheol07" width=400px alt="곽윤철"/> | <img src="https://avatars.githubusercontent.com/gyeongsu01" width=400px alt="김경수"/> | <img src="https://avatars.githubusercontent.com/kimhmin0814" width=400px alt="김형민"/> | <img src="https://avatars.githubusercontent.com/sjisu7525" width=400px alt="송지수"> | <img src="https://avatars.githubusercontent.com/chxiowxxk" width=400px alt="최영욱"> | <img src="https://avatars.githubusercontent.com/gksl5355" width=400px alt="조태환"> |
|                        [곽윤철](https://github.com/YunCheol07)                         |                                  [김경수](https://github.com/yeseul106)                                  |                        [김형민](https://github.com/kimhmin0814)                        |                                   [송지수](https://github.com/sjisu7525)                                    |                        [최영욱](https://github.com/chxiowxxk)                        |                        [조태환](https://github.com/gksl5355)                        |
<br>
