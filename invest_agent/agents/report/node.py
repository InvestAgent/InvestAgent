from typing import Dict, Any, List
import re
from .config import ReportConfig
from .render import render_html, html_to_pdf
from .llm import default_llm_refiner

def _safe_filename(name: str) -> str:
    return re.sub(r'[^가-힣a-zA-Z0-9._()-]+', '_', name).strip('_')

def _get(d: Dict[str, Any], path: List[str], default: Any = None) -> Any:
    cur = d
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def _mk_competition_table_html(comp_list: List[Dict[str, Any]]) -> str:
    if not comp_list:
        return "<p>(경쟁사 분석 데이터 없음)</p>"
    
    head = "<table><thead><tr><th>Company</th><th>Overlap</th><th>Diff.</th><th>Moat</th><th>Positioning</th></tr></thead><tbody>"
    rows = []
    for c in comp_list:
        rows.append(
            f"<tr>"
            f"<td>{c.get('company','')}</td>"
            f"<td>{c.get('overlap','N/A')}</td>"
            f"<td>{c.get('differentiation','N/A')}</td>"
            f"<td>{c.get('moat','N/A')}</td>"
            f"<td>{c.get('positioning','')}</td>"
            f"</tr>"
        )
    tail = "</tbody></table>"
    return head + "".join(rows) + tail

def report_writer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph state에서 보고서 생성
    ⚠️ 투자 판단이 "invest" 또는 "recommend"일 때만 보고서 생성
    
    입력 키 구조:
      - discovery: { items: [...] }
      - market_eval: { market: {...}, traction: {...}, business: {...} }
      - tech: { technology: {...}, meta: {...} }
      - competitor: { company: str, competitors_analysis: [...], swot: {...} }
      - decision: { label, scores, total_100, ... }
    """
    
    # ========== 0. 투자 판단 확인 - 추천이 아니면 보고서 생성 안함 ==========
    decision = state.get("decision", {}) or {}
    label = decision.get("label", "hold")
    
    # 투자 추천이 아니면 빈 리스트 반환
    if label not in ["invest", "recommend", "invest_conditional"]:
        print(f"[REPORT] 투자 판단이 '{label}'이므로 보고서를 생성하지 않습니다.")
        return {"reports": state.get("reports", [])}
    
    print(f"[REPORT] 투자 판단 '{label}' - 보고서 생성 시작")
    
    # ========== 1. 회사명 결정 ==========
    discovery_items = _get(state, ["discovery", "items"], [])
    tech_meta = _get(state, ["tech", "meta"], {})
    
    company = (
        tech_meta.get("startup_name") or 
        state.get("current_company") or 
        (discovery_items[0].get("startup_name") if discovery_items else "Unknown")
    )
    
    # ========== 2. 점수 파싱 ==========
    scores = decision.get("scores", {}) or {}
    
    # ========== 3. Market Eval 파싱 ==========
    market_eval = state.get("market_eval", {})
    market_blk = market_eval.get("market", {}) or {}
    traction_blk = market_eval.get("traction", {}) or {}
    business_blk = market_eval.get("business", {}) or {}
    
    # KPI 구성 (business 블록에서 ARR 추출, 나머지는 기본값)
    arr_raw = business_blk.get("revenue_model", "-")
    kpis = {
        "arr": arr_raw if arr_raw != "-" else "-",
        "qoq": "-",
        "ndr": "-",
        "gross_margin": "-",
        "burn": "-",
        "runway_months": "-",
    }
    
    # ========== 4. 기술 정보 파싱 ==========
    tech = state.get("tech", {})
    tech_blk = tech.get("technology", {}) or {}
    tech_meta = tech.get("meta", {}) or {}
    
    product_tech = {
        "stack": tech_blk.get("core_technology", "-"),
        "ip": tech_blk.get("ip_patent_status", "-"),
        "strengths": [],
        "weaknesses": [],
        "safety": "-",
        "sota_performance": tech_blk.get("sota_performance", "-"),
        "reproduction_difficulty": tech_blk.get("reproduction_difficulty", "-"),
        "infrastructure": tech_blk.get("infrastructure_requirements", "-"),
        "scalability": tech_blk.get("scalability", "-"),
    }
    
    # ========== 5. 경쟁사 & SWOT ==========
    competitor = state.get("competitor", {})
    comp_analysis = competitor.get("competitors_analysis", []) or []
    comp_table_html = _mk_competition_table_html(comp_analysis)
    swot = competitor.get("swot", {}) or {}
    
    if swot.get("strengths"):
        product_tech["strengths"] = swot["strengths"][:3]
    if swot.get("weaknesses"):
        product_tech["weaknesses"] = swot["weaknesses"][:3]
    
    # ========== 6. 출처 수집 ==========
    sources = []
    seen = set()
    for item in discovery_items:
        for url in item.get("source_urls", []) or []:
            if url not in seen:
                sources.append({"type": "web", "url": url})
                seen.add(url)
    
    # ========== 7. 회사 개요 ==========
    matched_item = None
    for item in discovery_items:
        if item.get("startup_name") == company:
            matched_item = item
            break
    
    item = matched_item or (discovery_items[0] if discovery_items else {})
    
    company_overview = {
        "founded": item.get("founded_year", "-"),
        "region": item.get("country", "-"),
        "one_liner": item.get("technology_description", "-"),
        "round": item.get("funding_status", "-"),
        "segment": item.get("industry", "-"),
        "founder": item.get("founder", "-"),
        "website": item.get("website", "-"),
    }
    
    # ========== 8. 시장 메타 정보 ==========
    market_meta = {
        "tam": market_blk.get("market_size", "unknown"),
        "sam": "-",
        "som": "-",
        "cagr": market_blk.get("cagr", "unknown"),
        "demand": market_blk.get("demand_drivers", []) or [],
        "risk": [],
        "sales_motion": business_blk.get("pricing_examples", "-"),
        "problem_fit": market_blk.get("problem_fit", "-"),
    }
    
    # ========== 9. 트랙션 정보 ==========
    traction_info = {
        "funding": traction_blk.get("funding", "-"),
        "investors": traction_blk.get("investors", []) or [],
        "partnerships": traction_blk.get("partnerships", []) or [],
    }
    
    # ========== 10. 비즈니스 정보 ==========
    business_info = {
        "revenue_model": business_blk.get("revenue_model", "-"),
        "pricing": business_blk.get("pricing_examples", "-"),
        "customer_segments": business_blk.get("customer_segments", []) or [],
        "monetization_stage": business_blk.get("monetization_stage", "-"),
    }
    
    # ========== 11. Key Points 생성 ==========
    key_points_raw = [
        tech_blk.get("technology_summary"),
        f"핵심기술: {product_tech['stack']}" if product_tech['stack'] != "-" else None,
        f"차별화: {tech_blk.get('differentiation', '')}" if tech_blk.get('differentiation') else None,
        f"시장 규모: {market_meta['tam']}, CAGR: {market_meta['cagr']}" if market_meta['tam'] != "unknown" else None,
        f"펀딩: {traction_info['funding']}" if traction_info['funding'] != "-" else None,
        f"투자자: {', '.join(traction_info['investors'][:3])}" if traction_info['investors'] else None,
        f"주요 파트너: {', '.join(traction_info['partnerships'][:2])}" if traction_info['partnerships'] and traction_info['partnerships'][0] != "unknown" else None,
    ]
    
    key_points = [p for p in key_points_raw if p][:4]
    
    # ========== 12. 기술 리스크 ==========
    tech_risks = tech_blk.get("tech_risks", []) or []
    
    # ========== 13. LLM 요약문 (선택) ==========
    llm_call = state.get("llm_call")
    if llm_call and company_overview.get("segment") != "-":
        raw_intro = (
            f"{company}는 {company_overview['segment']} 분야에서 "
            f"{product_tech['stack']} 기반 솔루션을 제공하며, "
            f"시장 성장성(CAGR {market_meta['cagr']})과 기술 차별화 관점에서 검토 가치가 있습니다."
        )
        refined_intro = default_llm_refiner(raw_intro, llm_call)
        if refined_intro and refined_intro not in key_points:
            key_points = [refined_intro] + key_points
            key_points = key_points[:4]
    
    # ========== 14. 최종 JSON 구성 ==========
    final_json = {
        "company": company,
        "decision": label,
        "scores": {
            "founder": scores.get("founder", "-"),
            "market": scores.get("market", "-"),
            "tech": scores.get("tech", "-"),
            "moat": scores.get("moat", "-"),
            "traction": scores.get("traction", "-"),
            "terms": scores.get("terms", "-"),
            "total_100": scores.get("total_100", 0),
        },
        "kpis": kpis,
        "risks": tech_risks,
        "mitigations": [],
        "sources": sources,
        "key_points": key_points,
        "traction": traction_info,
        "business": business_info,
        "recommendations": {
            "next_action": "심화 실사 진행",
            "required_data": [],
        },
    }
    
    # ========== 15. 템플릿용 메타 데이터 ==========
    meta = {
        "version": state.get("meta", {}).get("version", "v1.0"),
        "author": state.get("meta", {}).get("author", "투자팀"),
        "source_count": len(sources),
        "target_equity": state.get("meta", {}).get("target_equity", "10–12%"),
        "check_size": state.get("meta", {}).get("check_size", "$5–7M"),
        "company_overview": company_overview,
        "product_tech": product_tech,
        "market": market_meta,
        "competition_table": comp_table_html,
        "team": state.get("team", []),
        "kpi_scenarios_table": state.get("kpi_scenarios_table", ""),
        "swot": swot,
    }
    
    # ========== 16. HTML/PDF 생성 ==========
    html = render_html(final_json, meta)
    
    cfg: ReportConfig = state.get("report_config") or ReportConfig()
    fname = f"{_safe_filename(company)}_투자메모_{cfg.version}.pdf"
    out_path = f"{cfg.out_dir.rstrip('/')}/{fname}"
    
    if cfg.renderer != "none":
        html_to_pdf(html, out_path, renderer=cfg.renderer, wkhtmltopdf_path=cfg.wkhtmltopdf_path)
    
    print(f"[REPORT] 보고서 생성 완료: {out_path}")
    
    # ========== 17. State 업데이트 ==========
    reports = list(state.get("reports", []))
    reports.append({
        "company": company,
        "pdf": out_path,
        "html": html
    })
    
    return {"reports": reports}