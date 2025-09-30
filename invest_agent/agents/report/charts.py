import os
import io, base64
from typing import Dict, Any, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

def _img_bar_scores(scores: Dict[str, Any]) -> str:
    keys: List[str] = [k for k in ["founder","market","tech","moat","traction","terms"] if k in scores]
    vals = []
    for k in keys:
        try: vals.append(float(scores.get(k, 0)))
        except: vals.append(0.0)
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.bar(keys, vals)               # 색 지정 X (가이드 준수)
    ax.set_ylim(0, 10)
    ax.set_title("Scores (0–10)")
    ax.grid(True, axis="y", linestyle="--", alpha=0.4)
    plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=180); plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()

def _img_kpi_table(kpis: Dict[str, Any]) -> str:
    rows = [
        ("ARR", kpis.get("arr", "-")),
        ("QoQ %", kpis.get("qoq", "-")),
        ("NDR %", kpis.get("ndr", "-")),
        ("Gross Margin %", kpis.get("gross_margin", "-")),
        ("Burn", kpis.get("burn", "-")),
        ("Runway (months)", kpis.get("runway_months", "-")),
    ]
    fig, ax = plt.subplots(figsize=(6, 2.3))
    ax.axis("off")
    tbl = ax.table(cellText=rows, colLabels=["KPI", "Value"], loc="center")
    tbl.scale(1, 1.3)
    plt.tight_layout()
    buf = io.BytesIO(); fig.savefig(buf, format="png", dpi=180); plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()
