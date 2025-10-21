import datetime
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader
from .template import HTML_TMPL
from .charts import _img_bar_scores, _img_kpi_table

logger = logging.getLogger(__name__)

def _today() -> str:
    return datetime.date.today().isoformat()

def render_html(final_json: Dict[str, Any], meta: Dict[str, Any]) -> str:
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(HTML_TMPL)

    decision_map = {
        "invest": "투자 추천",
        "invest_conditional": "조건부 투자 추천",
        "hold": "보류",
        "reject": "투자 거절",
        "recommend": "투자 추천",
        "draft": "초안",
    }

    try:
        scores_img = _img_bar_scores(final_json.get("scores", {}))
        kpi_table_img = _img_kpi_table(final_json.get("kpis", {}))
    except Exception as e:
        logger.warning(f"차트 생성 중 오류 발생: {e}")
        scores_img = ""
        kpi_table_img = ""

    html = tmpl.render(
        company=final_json.get("company", "Unknown"),
        version=meta.get("version", "v1.0"),
        today=_today(),
        author=meta.get("author", "투자팀"),
        source_count=meta.get("source_count", len(final_json.get("sources", []))),
        decision_label=decision_map.get(final_json.get("decision", "hold"), "분석 중"),
        target_equity=meta.get("target_equity", "미정"),
        check_size=meta.get("check_size", "미정"),
        key_points=final_json.get("key_points", []),
        overview=meta.get("company_overview", {}),
        product=meta.get("product_tech", {}),
        market=meta.get("market", {}),
        competition_table=meta.get("competition_table", "<p>경쟁사 분석 진행 중</p>"),
        team=meta.get("team", []),
        swot=meta.get("swot", {}),
        kpis=final_json.get("kpis", {}),
        scores=final_json.get("scores", {}),
        score_items=final_json.get("score_items", []),  # ✅ 추가
        total_100=final_json.get("total_100", 0),  # ✅ 추가
        risks=final_json.get("risks", []),
        mitigations=final_json.get("mitigations", []),
        required_data=final_json.get("recommendations", {}).get("required_data", []),
        kpi_scenarios_table=meta.get("kpi_scenarios_table", ""),
        scores_img=scores_img,
        kpi_table_img=kpi_table_img,
        sources=final_json.get("sources", []),
        # ✅ 추가: 누락된 변수들
        traction=final_json.get("traction", {}),
        business=final_json.get("business", {}),
        investment_thesis=final_json.get("investment_thesis", ""),
        final_note=final_json.get("final_note", ""),
        red_flags=final_json.get("red_flags", []),
        appendix=final_json.get("appendix", {}),
    )
    logger.info(f"HTML 렌더링 완료: {final_json.get('company', 'Unknown')}")
    return html


def html_to_pdf(
    html: str,
    out_path: str,
    renderer: str = "playwright",
    wkhtmltopdf_path: Optional[str] = None,
) -> None:
    """HTML → PDF 변환 (Playwright 기반)"""
    if renderer == "none":
        logger.info("renderer=none → PDF 생성 스킵")
        return

    if renderer == "playwright":
        try:
            from playwright.sync_api import sync_playwright

            logger.info(f"Playwright PDF 생성 시작: {out_path}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html, wait_until="load")
                page.pdf(
                    path=out_path,
                    format="A4",
                    print_background=True,
                    margin={"top": "10mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
                )
                browser.close()
            logger.info(f"Playwright PDF 생성 완료: {out_path}")
        except Exception as e:
            logger.error(f"Playwright PDF 생성 실패: {e}")
            raise

    else:
        raise ValueError(f"지원하지 않는 renderer: {renderer}")