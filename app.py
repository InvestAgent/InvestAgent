import argparse
from invest_agent.workflow import app
from types import SimpleNamespace

class ReportConfig(SimpleNamespace):
    version: str = "v1.0"
    author: str = "팀 알파"
    renderer: str = "none"
    out_dir: str = "./outputs"

def main():
    parser = argparse.ArgumentParser(description="InvestAgent CLI")
    parser.add_argument("--query", required=True, help="자연어 쿼리")
    parser.add_argument("--out-dir", default="outputs")
    args = parser.parse_args()

    state = {
        "query": args.query,
        "report_config": ReportConfig(out_dir=args.out_dir),
    }
    out = app.invoke(state)
    print("✅ reports:", out.get("reports", []))

if __name__ == "__main__":
    main()

# python app.py --query "한국 생성형 AI 스타트업 알려줘!"