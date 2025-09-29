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
 
- 🔍스타트업 탐색 에이전트 : 유명한 AI 스타트업 정보 수집
- 🗜️기술 요약 에이전트 : 스타트업의 기술력 핵심 요약
- 📊시장성 평가 에이전트 :	시장 성장성, 수요 분석
- 🥊경쟁사 비교 에이전트 : 경쟁 구도, 차별성 분석
- 🧮투자 판단 에이전트	: 종합 판단 (리스트, ROI 등) 
- 📝보고서 생성 에이전트 :	결과 요약 보고서 생성

## Architecture
(그래프 이미지)

## Directory Structure
├── data/                  # 스타트업 PDF 문서
├── agents/                # 평가 기준별 Agent 모듈
├── prompts/               # 프롬프트 템플릿
├── outputs/               # 평가 결과 저장
├── app.py                 # 실행 스크립트
└── README.md

## Contributors 

|                                   스타트업 탐색 에이전트                                    |                                  시장성 평가 에이전트                                  |                                  기술 요약 에이전트                                   |                           보고서 생성 에이전트                            |                                 경쟁사 비교 에이전트                                  |                                  투자 판단 에이전트                                   |
| :-------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------: | :--------------------------------------------------------------------------------: | :----------------------------------------------------------------------: | :------------------------------------------------------------------------------: | :-------------------------------------------------------------------------------: |
| <img src="https://avatars.githubusercontent.com/YunCheol07" width=400px alt="곽윤철"/> | <img src="https://avatars.githubusercontent.com/gyeongsu01" width=400px alt="김경수"/> | <img src="https://avatars.githubusercontent.com/kimhmin0814" width=400px alt="김형민"/> | <img src="https://avatars.githubusercontent.com/sjisu7525" width=400px alt="송지수"> | <img src="https://avatars.githubusercontent.com/chxiowxxk" width=400px alt="최영욱"> | <img src="https://avatars.githubusercontent.com/gksl5355" width=400px alt="조태환"> |
|                        [곽윤철](https://github.com/YunCheol07)                         |                                  [김경수](https://github.com/yeseul106)                                  |                        [김형민](https://github.com/kimhmin0814)                        |                                   [송지수](https://github.com/sjisu7525)                                    |                        [최영욱](https://github.com/chxiowxxk)                        |                        [조태환](https://github.com/gksl5355)                        |
<br>
