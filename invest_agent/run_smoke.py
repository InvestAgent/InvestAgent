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
        
    }
    out = app.invoke(
        init_state,
        config={"configurable": {"thread_id": "test-thread-1"}}
    )
    print("생성된 보고서:", out.get("reports", []))

# python -m invest_agent.run_smoke
