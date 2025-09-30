import datetime
import re
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, BaseLoader
from .template import HTML_TMPL
from .charts import _img_bar_scores, _img_kpi_table

logger = logging.getLogger(__name__)

def _today() -> str:
    """현재 날짜를 ISO 형식으로 반환"""
    return datetime.date.today().isoformat()

def render_html(final_json: Dict[str, Any], meta: Dict[str, Any]) -> str:
    """
    최종 JSON 데이터와 메타 정보를 받아 HTML 보고서 생성
    
    Args:
        final_json: 보고서 핵심 데이터 (company, decision, scores, kpis 등)
        meta: 템플릿용 메타 데이터 (company_overview, product_tech, market 등)
    
    Returns:
        렌더링된 HTML 문자열
    """
    env = Environment(loader=BaseLoader())
    tmpl = env.from_string(HTML_TMPL)

    # 투자 판단 레이블 맵핑
    decision_map = {
        "invest": "투자 추천",
        "invest_conditional": "조건부 투자 추천",
        "hold": "보류",
        "reject": "투자 거절",
        "recommend": "투자 추천",
        "draft": "초안",
    }

    # 차트 이미지 생성
    try:
        scores_img = _img_bar_scores(final_json.get("scores", {}))
        kpi_table_img = _img_kpi_table(final_json.get("kpis", {}))
    except Exception as e:
        logger.warning(f"차트 생성 중 오류 발생: {e}")
        scores_img = ""
        kpi_table_img = ""

    # 템플릿 렌더링
    html = tmpl.render(
        # 기본 정보
        company=final_json.get("company", "Unknown"),
        version=meta.get("version", "v1.0"),
        today=_today(),
        author=meta.get("author", "투자팀"),
        source_count=meta.get("source_count", len(final_json.get("sources", []))),
        
        # 투자 판단
        decision_label=decision_map.get(
            final_json.get("decision", "hold"), 
            "분석 중"
        ),
        target_equity=meta.get("target_equity", "미정"),
        check_size=meta.get("check_size", "미정"),
        
        # 핵심 요약
        key_points=final_json.get("key_points", []),
        
        # 섹션별 데이터
        overview=meta.get("company_overview", {}),
        product=meta.get("product_tech", {}),
        market=meta.get("market", {}),
        competition_table=meta.get("competition_table", "<p>경쟁사 분석 진행 중</p>"),
        team=meta.get("team", []),
        swot=meta.get("swot", {}),
        
        # 지표 및 평가
        kpis=final_json.get("kpis", {}),
        scores=final_json.get("scores", {}),
        
        # 리스크 및 완화
        risks=final_json.get("risks", []),
        mitigations=final_json.get("mitigations", []),
        
        # 추천사항
        required_data=final_json.get("recommendations", {}).get("required_data", []),
        kpi_scenarios_table=meta.get("kpi_scenarios_table", ""),
        
        # 차트 이미지
        scores_img=scores_img,
        kpi_table_img=kpi_table_img,
        
        # 출처
        sources=final_json.get("sources", [])
    )
    
    logger.info(f"HTML 렌더링 완료: {final_json.get('company', 'Unknown')}")
    return html


def html_to_pdf(
    html: str, 
    out_path: str, 
    renderer: str = "playwright", 
    wkhtmltopdf_path: Optional[str] = None
) -> None:
    """
    HTML을 PDF로 변환
    
    Args:
        html: 변환할 HTML 문자열
        out_path: 저장할 PDF 파일 경로
        renderer: PDF 렌더러 ("playwright" 또는 "pdfkit" 또는 "none")
        wkhtmltopdf_path: wkhtmltopdf 실행 파일 경로 (pdfkit 사용 시)
    
    Raises:
        ValueError: 지원하지 않는 렌더러
        Exception: PDF 생성 실패
    """
    if renderer == "none":
        logger.info("renderer='none'이므로 PDF 생성 건너뜀")
        return
    
    if renderer == "playwright":
        try:
            from playwright.sync_api import sync_playwright
            
            logger.info(f"Playwright로 PDF 생성 중: {out_path}")
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_content(html, wait_until="load")
                page.pdf(
                    path=out_path,
                    format="A4",
                    print_background=True,
                    margin={
                        "top": "10mm",
                        "bottom": "12mm",
                        "left": "10mm",
                        "right": "10mm"
                    },
                )
                browser.close()
            logger.info(f"PDF 생성 완료: {out_path}")
            
        except ImportError:
            raise ImportError(
                "Playwright가 설치되지 않았습니다. "
                "'pip install playwright && playwright install chromium' 실행 필요"
            )
        except Exception as e:
            logger.error(f"Playwright PDF 생성 실패: {e}")
            raise
    
    elif renderer == "pdfkit":
        try:
            import pdfkit
            
            logger.info(f"pdfkit으로 PDF 생성 중: {out_path}")
            config = None
            if wkhtmltopdf_path:
                config = pdfkit.configuration(wkhtmltopdf=wkhtmltopdf_path)
            
            pdfkit.from_string(html, out_path, configuration=config)
            logger.info(f"PDF 생성 완료: {out_path}")
            
        except ImportError:
            raise ImportError(
                "pdfkit이 설치되지 않았습니다. "
                "'pip install pdfkit' 실행 및 wkhtmltopdf 설치 필요"
            )
        except Exception as e:
            logger.error(f"pdfkit PDF 생성 실패: {e}")
            raise
    
    else:
        raise ValueError(
            f"지원하지 않는 렌더러: '{renderer}'. "
            "'playwright', 'pdfkit', 또는 'none' 중 선택하세요."
        )