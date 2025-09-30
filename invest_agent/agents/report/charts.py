# invest_agent/agents/report/charts.py
import io
import base64
import matplotlib.pyplot as plt
from matplotlib import font_manager, rcParams

# ✅ 모듈 로드 시 한 번만 한글 폰트 세팅
def _set_korean_font():
    # 우선순위: Windows(맑은고딕) → 배포용(Nanum) → Apple → Noto
    candidates = [
        "Malgun Gothic",          # Windows 기본
        "NanumGothic", "Nanum Gothic",
        "Apple SD Gothic Neo",    # macOS 기본
        "Noto Sans CJK KR", "Noto Sans KR",
    ]

    # 시스템에 설치된 폰트 이름 수집
    installed = {f.name for f in font_manager.fontManager.ttflist}

    # 1) 이름으로 매칭
    for name in candidates:
        if name in installed:
            rcParams["font.family"] = name
            break
    else:
        # 2) 경로로 직접 등록 (필요 시)
        font_paths = [
            r"C:\Windows\Fonts\malgun.ttf",  # Windows
            "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # macOS
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",  # Ubuntu (nanum)
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Noto
        ]
        for p in font_paths:
            try:
                font_manager.fontManager.addfont(p)
                rcParams["font.family"] = font_manager.FontProperties(fname=p).get_name()
                break
            except Exception:
                pass

    # 마이너스 기호가 □로 나오지 않도록
    rcParams["axes.unicode_minus"] = False

_set_korean_font()  # ← 호출!

# ─────────────────────────────────────────────────────────────
# 이하 기존 함수들
def _img_bar_scores(scores: dict) -> str:
    labels = list(scores.keys())
    values = [scores[k] for k in labels if k != "total_100"]

    fig = plt.figure(figsize=(6, 3.2), dpi=150)
    plt.bar(labels[:len(values)], values)
    plt.xticks(rotation=20, ha="right")
    plt.title("컴포넌트 점수")
    plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=180); plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _img_kpi_table(kpis: dict) -> str:
    # … 기존 구현 그대로 …
    ...
