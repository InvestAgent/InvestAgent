# agents/report/node.py

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


# ===== LLM Executive Summary 생성 함수 (report_writer 밖으로 이동) =====
def _generate_executive_summary(
    company: str,
    tech_blk: Dict[str, Any],
    market_meta: Dict[str, Any],
    traction_info: Dict[str, Any],
    norm: Dict[str, Any],
    llm_call
) -> List[str]:
    """LLM으로 임원 요약 생성"""
    if not llm_call:
        return []
    
    prompt = f"""
다음 정보를 바탕으로 투자위원회용 Executive Summary를 3-4개 bullet point로 작성하세요.

회사: {company}
핵심 기술: {tech_blk.get('core_technology', '-')}
차별화: {tech_blk.get('differentiation', '-')}
시장 규모: {market_meta.get('tam', '-')}
CAGR: {market_meta.get('cagr', '-')}
펀딩: {traction_info.get('funding', '-')}
투자 점수: {norm['total_100']}/100
판단: {norm['label']}

요구사항:
1. 각 포인트는 한 문장으로 구체적 수치 포함
2. 투자 매력도를 명확히 전달
3. 비즈니스 임팩트 중심
4. 한국어, 간결체

출력 형식:
- 포인트 1
- 포인트 2
- 포인트 3
"""
    
    try:
        response = llm_call(prompt)
        # 응답에서 bullet point 추출
        lines = [line.strip() for line in response.split('\n') if line.strip().startswith('-')]
        return [line.lstrip('- ').strip() for line in lines][:4]
    except Exception as e:
        print(f"  ⚠️ LLM Summary 생성 실패: {e}")
        return []


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

    입력:
      - discovery: 기업 탐색 결과
      - tech: 기술 분석 결과
      - market_eval: 시장 분석 결과
      - competitor: 경쟁사 분석 결과
      - decision: 투자 판단 결과
      - sources: 각 에이전트가 수집한 출처
    """

    # 0) 의사결정 정규화
    decision_raw = state.get("decision", {}) or {}
    norm = _normalize_decision(decision_raw)
    label = norm["label"]
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

    # 5) 출처 통합
    sources = []
    seen = set()

    # Discovery 출처
    for it in discovery_items:
        for url in (it.get("source_urls") or []):
            if url and url not in seen:
                sources.append({
                    "type": "discovery",
                    "url": url,
                    "stage": "기업 탐색"
                })
                seen.add(url)

    # State에서 각 에이전트 출처 수집
    state_sources = state.get("sources", {})

    # Tech 출처
    for url in (state_sources.get("tech") or []):
        if url and url not in seen:
            sources.append({
                "type": "tech",
                "url": url,
                "stage": "기술 분석"
            })
            seen.add(url)

    # Market 출처
    for url in (state_sources.get("market") or []):
        if url and url not in seen:
            if "pdf" in url.lower() or "ai-dossier" in url or "dossier" in url.lower():
                sources.append({
                    "type": "report",
                    "url": url,
                    "stage": "시장 분석 (리서치 보고서)"
                })
            else:
                sources.append({
                    "type": "market",
                    "url": url,
                    "stage": "시장 분석"
                })
            seen.add(url)

    # Competitor 출처
    for url in (state_sources.get("competitor") or []):
        if url and url not in seen:
            sources.append({
                "type": "competitor",
                "url": url,
                "stage": "경쟁사 분석"
            })
            seen.add(url)

    print(f"[REPORT] 총 출처: {len(sources)}개 수집")

    # 6) 회사 개요
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
        "round": item.get("funding_stage", "-"),
        "segment": item.get("industry", meta_blk.get("industry", "-")),
        "founder": item.get("ceo", "-"),
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

    # 9) 기술 리스크 + 의사결정 리스크 병합
    tech_risks = (tech_blk.get("tech_risks", []) or [])
    decision_risks = norm.get("risks", []) or []
    merged_risks = list(dict.fromkeys(tech_risks + decision_risks))

    # 10) Key Points (LLM Executive Summary 우선)
    key_points_basic = [
        f"핵심기술: {product_tech['stack']}" if product_tech['stack'] != "-" else None,
        f"시장 규모: {market_meta['tam']}, CAGR: {market_meta['cagr']}" if market_meta['tam'] != "unknown" else None,
        f"펀딩: {traction_info['funding']}" if traction_info['funding'] != "-" else None,
    ]
    key_points_basic = [p for p in key_points_basic if p]

    # LLM Executive Summary 생성
    llm_call = state.get("llm_call")
    executive_summary = _generate_executive_summary(
        company, tech_blk, market_meta, traction_info, norm, llm_call
    )

    # LLM 요약 우선, 기본 포인트 보충
    if executive_summary:
        key_points = executive_summary + key_points_basic
    else:
        key_points = key_points_basic

    key_points = key_points[:5]

    # 11) Appendix: 평가 로직
    appendix = {
        "scoring_methodology": {
            "description": "5개 영역 가중 평가 (총 100점)",
            "components": [
                {"name": "시장", "weight": "35%", "criteria": "TAM, CAGR, Problem-Market Fit"},
                {"name": "기술", "weight": "25%", "criteria": "SOTA 성능, IP, 확장성, 재현 난이도"},
                {"name": "경쟁", "weight": "20%", "criteria": "차별성, Moat, 경쟁 Overlap"},
                {"name": "실적", "weight": "10%", "criteria": "ARR, 파트너십, 투자 유치"},
                {"name": "딜 조건", "weight": "10%", "criteria": "밸류에이션, 지분율"}
            ],
            "risk_penalty": "리스크 심각도×발생가능성 합산 → 20점 이하(5%), 21-35점(10%), 36점 이상(15%) 감점"
        },
        "decision_threshold": {
            "recommend": "≥ 50점: 투자 적극 권고",
            "conditional": "30-49점: 조건부 투자 검토",
            "reject": "< 30점: 투자 보류/거절"
        }
    }

    # 12) 최종 JSON
    final_json = {
        "company": company,
        "decision": label,
        "scores": norm["scores_dict"],
        "score_items": norm["scores_list"],
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
        "appendix": appendix,  # ✅ Appendix 추가
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
    cfg_data = state.get("report_config") or {}
    if isinstance(cfg_data, ReportConfig):
        cfg = cfg_data
    else:
        cfg = ReportConfig(
            version=cfg_data.get("version", "v1.0"),
            author=cfg_data.get("author", "투자팀"),
            renderer=cfg_data.get("renderer", "playwright"),
            out_dir=cfg_data.get("out_dir", "./outputs"),
            wkhtmltopdf_path=cfg_data.get("wkhtmltopdf_path"),
        )
    fname = f"{_safe_filename(company)}_투자메모_{cfg.version}.pdf"
    out_path = f"{cfg.out_dir.rstrip('/')}/{fname}"
    if cfg.renderer != "none":
        html_to_pdf(html, out_path, renderer=cfg.renderer, wkhtmltopdf_path=cfg.wkhtmltopdf_path)

    print(f"[REPORT] 보고서 생성 완료: {out_path}")

    # 15) State 업데이트
    reports = list(state.get("reports", []))
    reports.append({"company": company, "pdf": out_path, "html": html})
    return {"reports": reports}