from .workflow import app
from types import SimpleNamespace

class ReportConfig(SimpleNamespace):
    version: str = "v1.0"
    author: str = "팀 알파"
    renderer: str = "none"
    out_dir: str = "./outputs"

if __name__ == "__main__":
    init_state = {
        "query": "한국 생성형 AI 스타트업 알려줘!",
        "report_config": ReportConfig(),
    }
    out = app.invoke(init_state)
    print("생성된 보고서:", out.get("reports", []))
