
# invest_agent/run_smoke.py
from .workflow import app
from .nodes.report import ReportConfig

if __name__ == "__main__":
    cfg = ReportConfig(version="v1.0", author="팀 알파", renderer="playwright", out_dir="./reports")
    init_state = {
        "query": "한국 생성형 AI 스타트업 알려줘!",
        "report_config": cfg,
        # "llm_call": lambda sys, usr: usr,  # LLM 붙일 거면 콜백 넘기기
    }
    out = app.invoke(init_state)
    print("생성된 보고서:", out.get("reports", []))