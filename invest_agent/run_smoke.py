# invest_agent/run_smoke.py
from .workflow import app
from types import SimpleNamespace

class ReportConfig(SimpleNamespace):
    version: str = "v1.0"
    author: str = "SKALA 4반 3조"
    renderer: str = "none"
    out_dir: str = "./outputs"

if __name__ == "__main__":
    init_state = {
        "query": "한국 생성형 AI 스타트업 알려줘!", 
        "sources": {},  # ← 추가 (출처 추적용)
        "meta": {  # ← 추가 (보고서 메타 정보)
            "version": "v1.0",
            "author": "SKALA 4반 3조",
            "target_equity": "10-12%",
            "check_size": "$5-7M"
        },
        "report_config": {
            "version": "v1.0",
            "author": "SKALA 4반 3조",
            "renderer": "playwright",   # or "pdfkit" / "none"
            "out_dir": "./outputs",
            "wkhtmltopdf_path": None
        }
    }
    
    print("=" * 60)
    print(f"🚀 투자 분석 시작: {init_state['query']}")
    print("=" * 60)
    
    out = app.invoke(
        init_state,
        config={"configurable": {"thread_id": "test-thread-1"}}
    )
    
    print("\n" + "=" * 60)
    print("✅ 분석 완료")
    print("=" * 60)
    
    # 결과 출력
    print(f"\n📊 발견된 스타트업: {len(out.get('companies', []))}개")
    print(f"📝 생성된 보고서: {len(out.get('reports', []))}개")
    
    for report in out.get("reports", []):
        print(f"\n  - {report['company']}: {report['pdf']}")

# python -m invest_agent.run_smoke