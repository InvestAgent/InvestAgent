# services/report.py (혹은 너가 쓰는 report_writer 정의 파일)

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


# ───────────────────────────────────────────────────────────────────
# NEW: 의사결정/스코어 정규화 유틸
# state["decision"] 에 두 가지 케이스 지원:
#  (A) 기존 스키마: {"label": "...", "scores": {...}, "total_100": ...}
#  (B) 새 스키마: {"component_scores": {comp: {"score": .., "rationale": ..}}, "status": "fail|pass|hold|...", "total_score": ..., "red_flags": [...] ...}
# 이 함수가 공통 포맷으로 변환해줌.
# ───────────────────────────────────────────────────────────────────
def _normalize_decision(decision: Dict[str, Any]) -> Dict[str, Any]:
    if not decision:
        return {
            "label": "hold",
            "scores_dict": {},
            "scores_list": [],
            "total_100": 0,
            "status": "hold",
            "red_flags": [],
            "risks": [],
            "investment_thesis": "",
            "final_note": ""
        }

    # 케이스 (B): component_scores/total_score/status 기반
    if "component_scores" in decision:
        comp = decision.get("component_scores", {}) or {}
        scores_list = []
        scores_dict = {}
        for k, v in comp.items():
            score = v.get("score", v.get("value", "-"))
            rationale = v.get("rationale", "")
            scores_list.append({"name": k, "score": score, "rationale": rationale})
            scores_dict[k] = score

        total_100 = decision.get("total_score", decision.get("total_100", 0))
        status = (decision.get("status") or "").lower()
        # 상태 → 라벨 맵(리포트용 표시)
        status_to_label = {
            "pass": "invest",
            "ok": "invest",
            "invest": "invest",
            "invest_conditional": "invest_conditional",
            "conditional": "invest_conditional",
            "hold": "hold",
            "wait": "hold",
            "fail": "reject",
            "reject": "reject"
        }
        label = status_to_label.get(status, decision.get("label", "hold"))

        return {
            "label": label,
            "scores_dict": scores_dict,
            "scores_list": scores_list,
            "total_100": total_100,
            "status": status or label,
            "red_flags": decision.get("red_flags", []),
            "risks": decision.get("risks", []),
            "investment_thesis": decision.get("investment_thesis", ""),
            "final_note": decision.get("final_note", "")
        }

    # 케이스 (A): 기존 스키마
    scores_dict = decision.get("scores", {}) or {}
    total_100 = decision.get("total_100", 0)
    # 기존 고정 키를 리스트로 풀어 주기(라쇼날 없음)
    scores_list = [{"name": k, "score": v, "rationale": ""} for k, v in scores_dict.items() if k != "total_100"]
    return {
        "label": decision.get("label", "hold"),
        "scores_dict": scores_dict,
        "scores_list": scores_list,
        "total_100": total_100,
        "status": decision.get("label", "hold"),
        "red_flags": decision.get("red_flags", []),
        "risks": decision.get("risks", []),
        "investment_thesis": decision.get("investment_thesis", ""),
        "final_note": decision.get("final_note", "")
    }


def report_writer(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph state에서 보고서 생성

    입력(예상):
      - discovery: { items: [...] }
      - market_eval: { market: {...}, traction: {...}, business: {...} }
      - tech: { technology: {...}, meta: {...} }
      - competitor: { company: str, competitors_analysis: [...], swot: {...} }
      - decision: (기존 or 신규) -> _normalize_decision() 으로 정규화
    """

    # 0) 의사결정 정규화
    decision_raw = state.get("decision", {}) or {}
    norm = _normalize_decision(decision_raw)
    label = norm["label"]  # invest / invest_conditional / hold / reject
    # ⚠️ 예전과 달리 reject/hold라도 리포트 생성 (의사결정 근거 보존 목적)
    print(f"[REPORT] 투자 판단 '{label}' - 보고서 생성 시작")

    # 1) 회사명
    discovery_items = _get(state, ["discovery", "items"], [])
    tech_meta = _get(state, ["tech", "meta"], {})
    company = (
        tech_meta.get("startup_name")
        or state.get("current_company")
        or (discovery_items[0].get("startup_name") if discovery_items else "Unknown")
    )

    # 2) Market Eval
    market_eval = state.get("market_eval", {}) or {}
    market_blk = market_eval.get("market", {}) or {}
    traction_blk = market_eval.get("traction", {}) or {}
    business_blk = market_eval.get("business", {}) or {}

    # KPI (placeholder 유지)
    arr_raw = business_blk.get("revenue_model", "-")
    kpis = {
        "arr": arr_raw if arr_raw != "-" else "-",
        "qoq": "-",
        "ndr": "-",
        "gross_margin": "-",
        "burn": "-",
        "runway_months": "-"
    }

    # 3) 기술 정보
    tech = state.get("tech", {}) or {}
    tech_blk = tech.get("technology", {}) or {}
    meta_blk = tech.get("meta", {}) or {}
    product_tech = {
        "stack": tech_blk.get("core_technology", "-"),
        "ip": tech_blk.get("ip_patent_status", tech_blk.get("ip_status", "-")),
        "strengths": [],
        "weaknesses": [],
        "safety": "-",
        "sota_performance": tech_blk.get("sota_performance", "-"),
        "reproduction_difficulty": tech_blk.get("reproduction_difficulty", "-"),
        "infrastructure": tech_blk.get("infrastructure_requirements", "-"),
        "scalability": tech_blk.get("scalability", "-"),
    }

    # 4) 경쟁사 & SWOT
    competitor = state.get("competitor", {}) or {}
    comp_analysis = competitor.get("competitors_analysis", []) or []
    comp_table_html = _mk_competition_table_html(comp_analysis)
    swot = competitor.get("swot", {}) or {}
    if swot.get("strengths"):
        product_tech["strengths"] = swot["strengths"][:3]
    if swot.get("weaknesses"):
        product_tech["weaknesses"] = swot["weaknesses"][:3]

    # 5) 출처
    sources = []
    seen = set()
    for it in discovery_items:
        for url in it.get("source_urls", []) or []:
            if url not in seen:
                sources.append({"type": "web", "url": url})
                seen.add(url)

    # 6) 회사 개요(Discovery 매칭)
    matched_item = None
    for it in discovery_items:
        if it.get("startup_name") == company:
            matched_item = it
            break
    item = matched_item or (discovery_items[0] if discovery_items else {})
    company_overview = {
        "founded": item.get("founded_year", meta_blk.get("founded_year", "-")),
        "region": item.get("country", "-"),
        "one_liner": item.get("technology_description", "-"),
        "round": item.get("funding_status", "-"),
        "segment": item.get("industry", meta_blk.get("industry", "-")),
        "founder": item.get("founder", "-"),
        "website": item.get("website", "-"),
    }

    # 7) 시장 메타
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

    # 8) 트랙션/비즈니스
    traction_info = {
        "funding": traction_blk.get("funding", "-"),
        "investors": traction_blk.get("investors", []) or [],
        "partnerships": traction_blk.get("partnerships", []) or [],
    }
    business_info = {
        "revenue_model": business_blk.get("revenue_model", "-"),
        "pricing": business_blk.get("pricing_examples", "-"),
        "customer_segments": business_blk.get("customer_segments", []) or [],
        "monetization_stage": business_blk.get("monetization_stage", "-"),
    }

    # 9) Key Points
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

    # 10) 기술 리스크(기술 블록) + 의사결정 리스크 병합 표시
    tech_risks = (tech_blk.get("tech_risks", []) or [])
    decision_risks = norm.get("risks", []) or []
    merged_risks = list(dict.fromkeys(tech_risks + decision_risks))  # 중복 제거

    # 11) LLM 요약(옵션)
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

    # 12) 최종 JSON
    final_json = {
        "company": company,
        "decision": label,                              # invest/invest_conditional/hold/reject
        "scores": norm["scores_dict"],                  # 차트용 딕셔너리
        "score_items": norm["scores_list"],             # 표/카드용 리스트(name/score/rationale)
        "total_100": norm["total_100"],
        "kpis": kpis,
        "risks": merged_risks,
        "mitigations": [],
        "sources": sources,
        "key_points": key_points,
        "traction": traction_info,
        "business": business_info,
        "investment_thesis": norm.get("investment_thesis", ""),
        "final_note": norm.get("final_note", ""),
        "red_flags": norm.get("red_flags", []),
    }

    # 13) 템플릿 메타
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

    # 14) HTML/PDF
    html = render_html(final_json, meta)
    cfg: ReportConfig = state.get("report_config") or ReportConfig()
    fname = f"{_safe_filename(company)}_투자메모_{cfg.version}.pdf"
    out_path = f"{cfg.out_dir.rstrip('/')}/{fname}"
    if cfg.renderer != "none":
        html_to_pdf(html, out_path, renderer=cfg.renderer, wkhtmltopdf_path=cfg.wkhtmltopdf_path)

    print(f"[REPORT] 보고서 생성 완료: {out_path}")

    # 15) State 업데이트
    reports = list(state.get("reports", []))
    reports.append({"company": company, "pdf": out_path, "html": html})
    return {"reports": reports}
