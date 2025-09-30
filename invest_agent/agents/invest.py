# agents/invest.py
from typing import Dict, Any
from invest_agent.states import GraphState
import os
import json
import math
import re
from typing import TypedDict, List, Optional, Literal, Dict, Any

from dotenv import load_dotenv
import openai
from openai import OpenAI
"""
invest_decision_agent.py

Production-ready single-file pipeline.
- External entrypoint: `run_pipeline(raw_input: dict) -> dict`
- Returns ONLY the decision block (state["decision"]) for clean downstream handoff.
"""

# -------- Init OpenAI --------
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found in environment. Please set it in your .env file.")
openai.api_key = api_key  # for legacy-style calls
client = OpenAI()         # for new-style client calls

DEFAULT_MODEL = "gpt-4o"


# ========= Schema & Constants =========

DecisionStatus = Literal["invest", "fail"]

WEIGHTS = {
    "market": 0.35,
    "technology": 0.25,
    "competition": 0.20,
    "traction": 0.10,
    "deal": 0.10,
}

INVEST_CUTOFF = 65.0

RISK_PENALTY_BUCKETS = [
    (20.0, 5.0),
    (35.0, 10.0),
    (9999.0, 15.0),
]

RED_FLAG_RULES = {
    "bigtech_keywords": [
        "Sora",
        "OpenAI",
        "Adobe",
        "Google",
        "Meta",
        "Amazon",
        "Microsoft",
    ],
}


def clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


# ========= Normalizer =========

def parse_usd_billion(text: str) -> Optional[float]:
    """'6000억 달러' → 600.0  (억=100M → billions)"""
    if not text:
        return None
    m = re.search(r"([\d\.]+)\s*억\s*달러", text)
    if m:
        return float(m.group(1)) / 10.0
    m = re.search(r"([\d\.]+)\s*백만\s*달러", text)
    if m:
        return float(m.group(1)) / 1000.0
    return None


def parse_percent(text: str) -> Optional[float]:
    """'17.3%' → 17.3"""
    if not text:
        return None
    m = re.search(r"([\d\.]+)\s*%", text)
    return float(m.group(1)) if m else None


def normalize_input(raw: Dict[str, Any]) -> Dict[str, Any]: 
    state: GraphState = {}

    # Market
    if "market" in raw:
        market_raw = raw["market"]
        state["market"] = {
            "tam_usd_b": parse_usd_billion(market_raw.get("market_size", "")),
            "cagr_pct": parse_percent(market_raw.get("cagr", "")),
            "problem_fit_text": market_raw.get("problem_fit"),
            "demand_drivers": market_raw.get("demand_drivers", []),
        }

    # Technology
    if "technology" in raw:
        tech_raw = raw["technology"]
        state["technology"] = {
            "technology_summary": tech_raw.get("technology_summary"),
            "core_technology": tech_raw.get("core_technology"),
            "sota_performance_note": tech_raw.get("sota_performance"),
            "reproduction_difficulty": tech_raw.get("reproduction_difficulty", "unknown"),
            "infrastructure_requirements": tech_raw.get("infrastructure_requirements", []),
            "ip_patent_status": tech_raw.get("ip_patent_status", "unknown"),
            "scalability_note": tech_raw.get("scalability"),
            "tech_risks_texts": tech_raw.get("tech_risks", []),
        }

    # Competition
    if "competition" in raw:
        comp_raw = raw["competition"]
        competitors = []
        for c in comp_raw.get("competitors_analysis", []):
            competitors.append(
                {
                    "name": c.get("company"),
                    "overlap_0to10": c.get("overlap"),
                    "differentiation_0to10": c.get("differentiation"),
                    "moat_0to10": c.get("moat"),
                    "positioning": c.get("positioning"),
                }
            )
        state["competition"] = {
            "competitors": competitors,
            "swot_strengths": comp_raw.get("swot", {}).get("strengths", []),
            "swot_weaknesses": comp_raw.get("swot", {}).get("weaknesses", []),
            "swot_opportunities": comp_raw.get("swot", {}).get("opportunities", []),
            "swot_threats": comp_raw.get("swot", {}).get("threats", []),
        }

    # Business
    if "business" in raw:
        biz_raw = raw["business"]
        state["business"] = {
            "arr_usd_m": parse_usd_billion(biz_raw.get("revenue_model", "")),
            "pricing_model": biz_raw.get("pricing_examples"),
            "customer_segments": biz_raw.get("customer_segments", []),
            "funding_text": raw.get("traction", {}).get("funding"),
            "investors": raw.get("traction", {}).get("investors", []),
            "partnerships": raw.get("traction", {}).get("partnerships", []),
        }

    # Meta
    if "meta" in raw:
        state["meta"] = {
            "name": raw["meta"].get("startup_name"),
            "industry": raw["meta"].get("industry"),
            "country": raw["meta"].get("country"),
            "founded_year": raw["meta"].get("founded_year"),
        }

    return state


# ========= Scoring =========

def _safe_avg(values):
    vals = [v for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _parse_arr_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"([\d\.]+)\s*백만\s*달러", text)
    if m:
        return float(m.group(1))
    m = re.search(r"([\d\.]+)\s*M", text)
    if m:
        return float(m.group(1))
    return None


def _extract_pct_from_text(text: Optional[str]) -> Optional[float]:
    if not text:
        return None
    m = re.search(r"([+\-]?\d+(\.\d+)?)\s*%", text)
    if not m:
        return None
    try:
        val = float(m.group(1))
        if "+" in text[m.start(): m.end()] or "대비" in text:
            return abs(val)
        return val if val <= 30 else None
    except Exception:
        return None


def score_market(market: Dict[str, Any]) -> float:
    if not market:
        return 60.0

    tam_score = None
    cagr_score = None
    pf_score = None

    if market.get("tam_usd_b"):
        tam = max(1e-6, market["tam_usd_b"])
        tam_score = clamp(((math.log10(tam) - 1) / 2) * 100, 0, 100)
    if market.get("cagr_pct") is not None:
        cagr_score = clamp((market["cagr_pct"] / 25.0) * 100, 0, 100)
    if market.get("problem_fit_score_0to5") is not None:
        pf_score = market["problem_fit_score_0to5"] * 20

    quant_candidates = [v for v in [tam_score, cagr_score] if v is not None]
    if quant_candidates:
        quant_max = max(quant_candidates)
        quant_avg = _safe_avg(quant_candidates) or quant_max
        quant = 0.6 * quant_max + 0.4 * quant_avg
    else:
        quant = None

    if pf_score is not None and quant is not None:
        final = (quant + pf_score) / 2.0
    elif pf_score is not None:
        final = pf_score
    elif quant is not None:
        final = quant
    else:
        final = 60.0

    return clamp(final, 0, 100)


def score_technology(tech: Dict[str, Any]) -> float:
    if not tech:
        return 60.0

    subs = [60]

    if tech.get("perf_delta_pct") is not None:
        subs.append(min(100, 60 + float(tech["perf_delta_pct"])))
    if tech.get("speed_delta_pct") is not None:
        subs.append(min(100, 60 + float(tech["speed_delta_pct"])))
    if tech.get("csat_pct") is not None:
        subs.append(clamp(float(tech["csat_pct"]), 0, 100))

    note = tech.get("sota_performance_note", "")
    delta = _extract_pct_from_text(note)
    if delta is not None:
        subs.append(min(100, 70 + delta))
    elif isinstance(note, str) and ("초과" in note or "우수" in note):
        subs.append(75)

    checklist = [
        tech.get(k, 0)
        for k in [
            "checklist_api",
            "checklist_multi_tenancy",
            "checklist_sdk_docs",
            "checklist_automation",
            "checklist_domain_extensibility",
        ]
    ]
    if any(v is not None for v in checklist):
        checklist_score = (sum([(v or 0) for v in checklist]) / 5.0) * 100
        subs.append(checklist_score)

    ip_txt = (tech.get("ip_patent_status") or "").lower()
    if "등록" in ip_txt or "granted" in ip_txt:
        subs.append(85)
    elif "출원" in ip_txt or "filed" in ip_txt:
        subs.append(75)
    else:
        subs.append(55)

    if tech.get("scalability_note"):
        subs.append(75)

    return clamp(sum(subs) / len(subs), 0, 100)


def score_competition(comp: Dict[str, Any]) -> float:
    if not comp:
        return 60.0

    diffs, moats, overlaps = [], [], []
    for c in comp.get("competitors", []):
        if c.get("differentiation_0to10") is not None:
            diffs.append(c["differentiation_0to10"] * 10)
        if c.get("moat_0to10") is not None:
            moats.append(c["moat_0to10"] * 10)
        if c.get("overlap_0to10") is not None:
            overlaps.append(c["overlap_0to10"])

    if diffs or moats:
        base = 0.6 * (_safe_avg(diffs) or 60) + 0.4 * (_safe_avg(moats) or 60)
    else:
        base = 60.0

    penalty = 0.0
    if overlaps:
        avg_overlap = sum(overlaps) / len(overlaps)
        penalty = max(0.0, (avg_overlap - 5.0) * 5.0)

    base_adj = clamp(base - penalty, 0, 100)

    qpos = comp.get("qual_positioning_score_0to5")
    if qpos is not None:
        qpos_score = qpos * 20
        return clamp((base_adj + qpos_score) / 2.0, 0, 100)
    return base_adj


def score_traction(biz: Dict[str, Any]) -> float:
    if not biz:
        return 60.0

    score = 60.0

    arr = biz.get("arr_usd_m")
    if arr is None and biz.get("revenue_model"):
        arr = _parse_arr_text(biz["revenue_model"])
    if arr is not None:
        arr_score = max(50.0, min(100.0, (float(arr) / 50.0) * 100.0))
        score = arr_score

    partners = biz.get("partnerships", [])
    if partners:
        if any(
            "포춘" in p
            or any(big in p for big in ["Microsoft", "AWS", "Amazon", "Google", "Meta"])
            for p in partners
        ):
            score += 20
        else:
            score += 10

    ftxt = biz.get("funding_text") or ""
    if isinstance(ftxt, str) and ("억" in ftxt or "million" in ftxt.lower()):
        score += 5

    return clamp(score, 0, 100)


def score_deal_terms(state: GraphState) -> float:
    return 60.0


def compute_scores(state: GraphState) -> GraphState:
    scores: Dict[str, Any] = {
        "market": score_market(state.get("market", {})),
        "technology": score_technology(state.get("technology", {})),
        "competition": score_competition(state.get("competition", {})),
        "traction": score_traction(state.get("business", {})),
        "deal": score_deal_terms(state),
        "risk_penalty_pct": 0.0,
    }
    state["scores"] = scores
    return state


# ========= LLM Helpers & Evaluators =========

def llm_call_json(prompt: str, model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """
    OpenAI chat completion with JSON response_format.
    """
    resp = openai.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a strict JSON generator. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ],
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)


def eval_problem_fit(state: GraphState) -> GraphState:
    text = state.get("market", {}).get("problem_fit_text")
    drivers = state.get("market", {}).get("demand_drivers", [])
    if not text:
        return state

    prompt = f"""
Input:
Problem Fit: {text}
Demand Drivers: {drivers}

Scoring Rules (0–5 scale):
0 = 문제 언급 없음/모호
1 = 추상적
2 = 구체적이나 긴급성 불분명
3 = 구체적 + 긴급성
4 = 구체적 + 긴급성 + 지불의지 증거
5 = 구체적 + 긴급성 + 지불의지 + 대체재 부재

Return JSON:
{{
  "problem_fit_score": <0-5 integer>,
  "rationale": "<short explanation>"
}}
"""
    out = llm_call_json(prompt)
    score = int(out.get("problem_fit_score", 0))
    state.setdefault("market", {})["problem_fit_score_0to5"] = score
    state["market"]["problem_fit_rationale"] = [out.get("rationale", "")]
    return state


def eval_tech_checklist(state: GraphState) -> GraphState:
    note = state.get("technology", {}).get("scalability_note", "")
    summary = state.get("technology", {}).get("technology_summary", "")

    prompt = f"""
Input:
Technology Summary: {summary}
Scalability Note: {note}

Checklist (0 or 1 each):
- api: API 제공 여부
- multi_tenancy: 엔터프라이즈/멀티테넌시 지원
- sdk_docs: SDK/문서화 제공
- automation: 자동화 기능
- domain_extensibility: 여러 산업 확장성

Return JSON:
{{
  "checklist": {{
    "api": 0 or 1,
    "multi_tenancy": 0 or 1,
    "sdk_docs": 0 or 1,
    "automation": 0 or 1,
    "domain_extensibility": 0 or 1
  }},
  "rationale": "<short explanation>"
}}
"""
    out = llm_call_json(prompt)
    checklist = out.get("checklist", {})
    for key in ["api", "multi_tenancy", "sdk_docs", "automation", "domain_extensibility"]:
        state.setdefault("technology", {})[f"checklist_{key}"] = int(checklist.get(key, 0))
    return state


def eval_competition_positioning(state: GraphState) -> GraphState:
    comp = state.get("competition", {})
    comps = comp.get("competitors", [])
    if not comps:
        return state

    comp_texts = [f"{c.get('name')}: {c.get('positioning')}" for c in comps]

    prompt = f"""
Target company positioning vs competitors:
{comp_texts}

Scoring Rules (0–5 scale):
0 = 포지셔닝 없음/경쟁사와 동일
1 = 아주 약한 차별성
2 = 특정 기능/세그먼트 국한 차별성
3 = 세그먼트 집중 뚜렷, 일부 파트너십
4 = 뚜렷한 세그먼트 집중 + 파트너십 구체적 + 차별화 명확
5 = 독자 생태계/네트워크 효과 + 차별화 확고

Return JSON:
{{
  "qual_positioning_score": <0-5 integer>,
  "notes": ["..."]
}}
"""
    out = llm_call_json(prompt)
    state.setdefault("competition", {})["qual_positioning_score_0to5"] = int(out.get("qual_positioning_score", 0))
    state["competition"]["qual_positioning_notes"] = out.get("notes", [])
    return state


def eval_risks(state: GraphState) -> GraphState:
    texts: List[str] = []
    texts += state.get("technology", {}).get("tech_risks_texts", [])
    texts += state.get("competition", {}).get("swot_weaknesses", [])
    texts += state.get("competition", {}).get("swot_threats", [])
    if not texts:
        return state

    prompt = f"""
Input risk texts:
{texts}

Task:
- Group similar risks
- Assign type: cost, data, regulatory, competitive, ops, product, other
- Assign severity (1=low, 2=medium, 3=high)
- Assign likelihood (1=low, 2=medium, 3=high)

Return JSON:
{{
  "risks": [
    {{"type": "regulatory", "text": "...", "severity": 2, "likelihood": 3}},
    ...
  ]
}}
"""
    out = llm_call_json(prompt)
    risks = out.get("risks", [])
    state["risks"] = risks
    return state


# ========= Aggregator & Decision =========

def apply_risk_penalty(state: GraphState) -> float:
    risks = state.get("risks", [])
    if not risks:
        return 0.0

    agg = 0.0
    for r in risks:
        sev = r.get("severity_1to3", 1)
        lik = r.get("likelihood_1to3", 1)
        w = r.get("weight", 1.0)
        agg += float(sev) * float(lik) * float(w)

    for max_val, pct in RISK_PENALTY_BUCKETS:
        if agg <= max_val:
            state.setdefault("scores", {})["risk_penalty_pct"] = pct
            return pct
    return 0.0


def generate_investment_thesis(state: GraphState) -> str:
    comp_scores = state["decision"]["component_scores"]
    risks = state["decision"]["risks"]

    prompt = f"""
당신은 벤처캐피탈 투자심사역입니다. 아래 데이터를 기반으로 투자 의견을 작성하세요.
- 시장 점수: {comp_scores['market']['score']:.1f}
- 기술 점수: {comp_scores['technology']['score']:.1f}
- 경쟁 점수: {comp_scores['competition']['score']:.1f}
- 실적 점수: {comp_scores['traction']['score']:.1f}
- 딜 점수: {comp_scores['deal']['score']:.1f}
- 주요 리스크: {', '.join(risks) if risks else '없음'}

조건:
1. 4~5문장으로 작성
2. 시장성과 기회 요인을 먼저 언급
3. 기술/경쟁 리스크를 구체적으로 지적
4. 마지막에 투자 권고/조건부 권고/재검토 필요 중 하나로 결론
5. 한국어, 투자위원회 보고서 스타일
"""
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=400,
    )
    return response.choices[0].message.content.strip()


def aggregate_scores(state: Dict[str, Any]) -> Dict[str, Any]:
    comp_scores: Dict[str, Dict[str, Any]] = {
        "market": {"score": state["scores"]["market"], "rationale": "TAM·CAGR·problem-fit 기준 고성장 시장 평가"},
        "technology": {"score": state["scores"]["technology"], "rationale": "SOTA/성능·확장성·IP·체크리스트 반영"},
        "competition": {"score": state["scores"]["competition"], "rationale": "Moat/차별성·overlap penalty·포지셔닝"},
        "traction": {"score": state["scores"]["traction"], "rationale": "ARR 규모·성장·파트너십·투자스테이지"},
        "deal": {"score": state["scores"]["deal"], "rationale": "조건 정보 제한 → 중립"},
    }

    total = sum(WEIGHTS[k] * comp_scores[k]["score"] for k in WEIGHTS)

    penalty_pct = apply_risk_penalty(state)
    adjusted = total * (1 - penalty_pct / 100.0)

    if adjusted >= 50:
        status = "invest"
        final_note = "투자 권고"
    elif adjusted >= 30:
        status = "invest"
        final_note = "조건부 투자 권고"
    else:
        status = "fail"
        final_note = "재검토 필요"

    risks_texts = [r.get("text", "") for r in state.get("risks", [])]

    state["decision"] = {
        "status": status,
        "total_score": adjusted,
        "component_scores": comp_scores,
        "risks": risks_texts,
        "red_flags": [],
        "investment_thesis": "LLM_PENDING",
        "final_note": final_note,
    }

    thesis = generate_investment_thesis(state)
    state["decision"]["investment_thesis"] = thesis
    return state


# ========= Public Entrypoint =========

def run_pipeline(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full pipeline and return ONLY the decision dict.
    """
    state = normalize_input(raw_input)
    state = compute_scores(state)
    state = eval_problem_fit(state)
    state = eval_tech_checklist(state)
    state = eval_competition_positioning(state)
    state = eval_risks(state)
    state = aggregate_scores(state)

    decision = state.get("decision")
    if not isinstance(decision, dict):
        raise KeyError("`state['decision']` was not produced or is not a dict.")
    return decision


__all__ = ["run_pipeline"]


def investment_decision(state: GraphState) -> GraphState:
    """
    투자 판단 노드 (Workflow용 래퍼)
    
    입력:
        - discovery, tech, market_eval, competitor
    
    출력:
        - decision: {...}
    """
    current_company = state.get("current_company", "")
    print(f"[투자 판단] 시작: {current_company}")
    
    # GraphState → 네 원본 입력 형식으로 변환
    raw_input = {
        "meta": state.get("tech", {}).get("meta", {}),
        "technology": state.get("tech", {}).get("technology", {}),
        "market": state.get("market_eval", {}).get("market", {}),
        "traction": state.get("market_eval", {}).get("traction", {}),
        "business": state.get("market_eval", {}).get("business", {}),
        "competition": state.get("competitor", {}),
    }
    
    try:
        # 네 원본 파이프라인 실행
        decision_output = run_pipeline(raw_input)
        
        print(f"  ✓ 총점: {decision_output.get('total_score', 0):.1f}")
        print(f"  ✓ 판단: {decision_output.get('status', 'unknown')}")
        
        # status를 workflow 호환 label로 변환
        status = decision_output.get("status", "fail")
        if status == "invest":
            if decision_output.get("total_score", 0) >= 50:
                label = "recommend"
            else:
                label = "invest_conditional"
        else:
            label = "reject"
        
        # decision 형식 통일
        unified_decision = {
            "label": label,
            "total_100": int(decision_output.get("total_score", 0)),
            "component_scores": decision_output.get("component_scores", {}),
            "risks": decision_output.get("risks", []),
            "red_flags": decision_output.get("red_flags", []),
            "investment_thesis": decision_output.get("investment_thesis", ""),
            "final_note": decision_output.get("final_note", ""),
        }
        
        return {
            **state,
            "decision": unified_decision
        }
        
    except Exception as e:
        print(f"  ❌ 투자 판단 실패: {e}")
        # fallback
        return {
            **state,
            "decision": {
                "label": "reject",
                "total_100": 0,
                "component_scores": {},
                "risks": [str(e)],
                "red_flags": [],
                "investment_thesis": "분석 실패",
                "final_note": "재검토 필요",
            }
        }