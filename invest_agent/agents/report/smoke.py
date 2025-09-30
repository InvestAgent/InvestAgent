"""
보고서 생성 테스트 스크립트
독립 실행 가능 버전
"""
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

from nodes.report.config import ReportConfig
from nodes.report.node import report_writer
# from nodes.report.llm import local_llm_call  # 필요시 주석 해제


def create_test_state(decision_label: str = "invest") -> dict:
    """테스트용 state 생성"""
    return {
        "discovery": {
            "items": [
                {
                    "startup_name": "트웰브랩스",
                    "technology_description": "트웰브랩스는 AI 기반의 비디오 이해 및 검색 기술을 개발하여, 사용자들이 쉽게 고품질의 시각 콘텐츠를 제작할 수 있도록 돕는 플랫폼입니다.",
                    "website": "https://www.twelvelabs.ai",
                    "founded_year": 2021,
                    "country": "한국",
                    "founder": "김지훈",
                    "funding_status": "2023년 시리즈 A 투자 유치, 70억 원, 주요 투자자: 네이버 D2SF, 카카오벤처스",
                    "industry": "미디어 및 콘텐츠 생성",
                    "core_technology": "텍스트-이미지 생성",
                    "source_urls": [
                        "https://www.twelvelabs.ai",
                        "https://techcrunch.com/2023/twelvelabs-funding"
                    ]
                },
            ]
        },
        "market_eval": {
            "market": {
                "market_size": "6000억 달러 (estimated)",
                "cagr": "17.3%",
                "problem_fit": "AI 비디오 생성 시장에서 크리에이터들의 콘텐츠 제작 효율성 요구 증가",
                "demand_drivers": [
                    "AI 기술의 발전",
                    "크리에이터 이코노미 성장",
                    "비디오 콘텐츠 수요 증가"
                ]
            },
            "traction": {
                "funding": "70억 원 (2023년 시리즈 A)",
                "investors": ["네이버 D2SF", "카카오벤처스", "AI엔젤클럽"],
                "partnerships": ["포춘 글로벌 500대 기업"]
            },
            "business": {
                "revenue_model": "ARR 15.5백만 달러 (estimated)",
                "pricing_examples": "구독 기반 모델 (월 $49-299)",
                "customer_segments": ["프로페셔널 크리에이터", "기업 마케팅팀"],
                "monetization_stage": "성장 단계"
            }
        },
        "tech": {
            "technology": {
                "technology_summary": "트웰브랩스는 AI 기반의 비디오 이해 및 검색 기술을 제공합니다.",
                "core_technology": "멀티모달 AI 기반 비디오 이해 및 검색",
                "differentiation": "독창적인 비디오 네이티브 AI 모델",
                "sota_performance": "벤치마크 15% 초과 성능",
                "reproduction_difficulty": "높음",
                "infrastructure_requirements": "NVIDIA A100 GPU 클러스터",
                "ip_patent_status": "핵심 알고리즘 3건 특허 출원 중",
                "scalability": "클라우드 네이티브 아키텍처",
                "tech_risks": ["GPU 인프라 비용 압박", "오픈소스 모델 발전 위험"]
            },
            "meta": {
                "startup_name": "트웰브랩스",
                "industry": "AI 비디오 분석",
                "country": "한국",
                "founded_year": "2021"
            }
        },
        "competitor": {
            "company": "트웰브랩스",
            "competitors_analysis": [
                {"company": "Runway", "overlap": 8.5, "differentiation": 7.0, "moat": 6.5, "positioning": "크리에이터 시장 선도"},
                {"company": "Adobe", "overlap": 6.5, "differentiation": 5.5, "moat": 8.0, "positioning": "엔터프라이즈 강점"}
            ],
            "swot": {
                "strengths": ["렌더링 품질 15% 우수", "사용자 이탈률 5%"],
                "weaknesses": ["GPU 비용 높음", "브랜드 인지도 낮음"],
                "opportunities": ["시장 CAGR 150%", "크리에이터 이코노미 성장"],
                "threats": ["OpenAI 경쟁", "오픈소스 모델 발전"]
            }
        },
        "decision": {
            "label": decision_label,
            "scores": {
                "founder": 8.5, "market": 9.0, "tech": 8.0,
                "moat": 7.0, "traction": 7.5, "terms": 8.0,
                "total_100": 79
            }
        },
    }


def main():
    print("=" * 60)
    print("투자 보고서 생성 테스트")
    print("=" * 60)
    
    cfg = ReportConfig(
        version="v1.0",
        author="투자분석팀",
        renderer="playwright",
        out_dir="./output"
    )
    
    Path(cfg.out_dir).mkdir(parents=True, exist_ok=True)
    
    # 투자 추천 케이스만 테스트
    state = create_test_state(decision_label="invest")
    state["report_config"] = cfg
    
    try:
        result = report_writer(state)
        reports = result.get("reports", [])
        
        if reports:
            rep = reports[0]
            print(f"\n보고서 생성 성공!")
            print(f"회사: {rep['company']}")
            print(f"PDF: {rep['pdf']}")
            
            html_path = Path(cfg.out_dir) / f"{rep['company']}_preview.html"
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(rep["html"])
            print(f"HTML: {html_path.resolve()}")
        else:
            print("보고서 생성 안됨")
            
    except Exception as e:
        print(f"에러: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()