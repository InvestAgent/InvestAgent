
HTML_TMPL = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ company }} 투자 메모</title>
<style>
  * { box-sizing: border-box; }
  body { 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", Arial, sans-serif; 
    margin: 0; padding: 40px;
    background: #f8f9fa; color: #1a1a1a; line-height: 1.6;
  }
  .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 48px; border-radius: 12px; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
  .header { border-bottom: 3px solid #0066cc; padding-bottom: 24px; margin-bottom: 32px; }
  h1 { margin: 0 0 12px 0; font-size: 32px; font-weight: 700; color: #000; }
  .meta { color: #666; font-size: 14px; display: flex; gap: 20px; flex-wrap: wrap; }
  .meta-item { display: flex; align-items: center; gap: 6px; }
  .meta-item::before { content: "•"; color: #0066cc; }
  .decision-banner { background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%); color: #fff; padding: 24px 28px; border-radius: 8px; margin-bottom: 32px; }
  .decision-banner h2 { margin: 0 0 12px 0; font-size: 18px; font-weight: 600; opacity: 0.9; }
  .decision-label { font-size: 28px; font-weight: 700; margin-bottom: 16px; }
  .decision-details { display: flex; gap: 32px; font-size: 15px; opacity: 0.95; }
  .key-points { background: #f8f9fa; border-left: 4px solid #0066cc; padding: 20px 24px; margin: 24px 0; border-radius: 0 8px 8px 0; }
  .key-points ul { margin: 0; padding-left: 20px; }
  .section { margin-top: 48px; page-break-inside: avoid; }
  h2 { font-size: 24px; font-weight: 700; margin: 0 0 20px 0; color: #000; border-bottom: 2px solid #e5e7eb; padding-bottom: 12px; }
  h3 { font-size: 18px; font-weight: 600; margin: 16px 0 12px 0; color: #333; }
  .info-card { background: #f8f9fa; border-radius: 8px; padding: 20px; margin-bottom: 16px; }
  .row { display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 24px; }
  @media (max-width: 768px) { .row { grid-template-columns: 1fr; } }
  table { width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }
  th, td { border: 1px solid #e5e7eb; padding: 12px 16px; text-align: left; }
  th { background: #f8f9fa; font-weight: 600; color: #333; }
  tr:hover { background: #f8f9fa; }
  .swot-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px; }
  .swot-box { border-radius: 8px; padding: 20px; }
  .swot-box.strengths { background: #e8f5e9; border-left: 4px solid #4caf50; }
  .swot-box.weaknesses { background: #ffebee; border-left: 4px solid #f44336; }
  .swot-box.opportunities { background: #e3f2fd; border-left: 4px solid #2196f3; }
  .swot-box.threats { background: #fff3e0; border-left: 4px solid #ff9800; }
  .score-card { background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; padding: 24px; margin-top: 20px; }
  .score-items { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 16px; margin-bottom: 20px; }
  .score-item { text-align: center; padding: 12px; background: #fff; border-radius: 6px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
  .score-label { font-size: 12px; color: #666; text-transform: uppercase; letter-spacing: 0.5px; }
  .score-value { font-size: 20px; font-weight: 700; color: #0066cc; margin-top: 4px; }
  .score-rationale { font-size: 12px; color: #444; margin-top: 6px; line-height: 1.4; }
  .total-score { text-align: center; padding: 20px; background: #fff; border-radius: 8px; margin-top: 16px; }
  .total-score .value { font-size: 40px; font-weight: 700; color: #0066cc; }
  .total-score .label { font-size: 14px; color: #666; margin-top: 8px; }
  img { max-width: 100%; border-radius: 8px; margin-top: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }
  .tag { display: inline-block; padding: 4px 12px; border-radius: 16px; font-size: 13px; font-weight: 500; margin: 4px; }
  .tag.primary { background: #e3f2fd; color: #1976d2; }
  .tag.success { background: #e8f5e9; color: #388e3c; }
  .tag.warning { background: #fff3e0; color: #f57c00; }
  .tag.danger { background: #ffebee; color: #d32f2f; }
  .sources-list { font-size: 13px; line-height: 1.8; }
  .sources-list li { margin: 8px 0; word-break: break-all; }
  .source-type { display: inline-block; padding: 2px 8px; background: #0066cc; color: #fff; border-radius: 4px; font-size: 11px; font-weight: 600; margin-right: 8px; text-transform: uppercase; }
  .source-stage { color: #666; font-size: 12px; margin-left: 8px; }
  @media print { 
    body { background: #fff; padding: 0; } 
    .container { box-shadow: none; page-break-inside: avoid; }
    .section { page-break-inside: avoid; }
  }
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>{{ company }} 투자 메모</h1>
    <div class="meta">
      <span class="meta-item">버전: {{ version }}</span>
      <span class="meta-item">작성일: {{ today }}</span>
      <span class="meta-item">분석자: {{ author }}</span>
      <span class="meta-item">출처: {{ source_count }}개</span>
    </div>
  </div>

  <div class="decision-banner">
    <h2>투자 판단</h2>
    <div class="decision-label">{{ decision_label }}</div>
    <div class="decision-details">
      <div>목표 지분: <strong>{{ target_equity }}</strong></div>
      <div>투자 규모: <strong>{{ check_size }}</strong></div>
    </div>
  </div>

  {% if key_points %}
  <div class="key-points">
    <h3 style="margin-top:0;">핵심 요약 (Executive Summary)</h3>
    <ul>
      {% for p in key_points if p %}<li>{{ p }}</li>{% endfor %}
    </ul>
  </div>
  {% endif %}

  <div class="section">
    <h2>1. 회사 개요</h2>
    <div class="info-card">
      <div class="row">
        <div>
          <p><strong>설립:</strong> {{ overview.founded or '-' }}</p>
          <p><strong>지역:</strong> {{ overview.region or '-' }}</p>
          <p><strong>창업자/CEO:</strong> {{ overview.founder or '-' }}</p>
        </div>
        <div>
          <p><strong>산업:</strong> {{ overview.segment or '-' }}</p>
          <p><strong>웹사이트:</strong> {{ overview.website or '-' }}</p>
          <p><strong>최근 라운드:</strong> {{ overview.round or '-' }}</p>
        </div>
      </div>
      <p style="margin-top:16px;padding-top:16px;border-top:1px solid #e5e7eb;">
        <strong>소개:</strong> {{ overview.one_liner or '-' }}
      </p>
    </div>
  </div>

  <div class="section">
    <h2>2. 제품 및 기술</h2>
    <div class="row">
      <div class="info-card">
        <h3>핵심 기술</h3>
        <p><strong>기술 스택:</strong> {{ product.stack or '-' }}</p>
        <p><strong>IP/특허 현황:</strong> {{ product.ip or '-' }}</p>
        <p><strong>SOTA 성능:</strong> {{ product.sota_performance or '-' }}</p>
        <p><strong>재현 난이도:</strong> {{ product.reproduction_difficulty or '-' }}</p>
      </div>
      <div class="info-card">
        <h3>확장성 & 인프라</h3>
        <p><strong>확장성:</strong> {{ product.scalability or '-' }}</p>
        <p><strong>인프라 요구사항:</strong> {{ product.infrastructure or '-' }}</p>
        <p><strong>보안/프라이버시:</strong> {{ product.safety or '-' }}</p>
      </div>
    </div>
    {% if product.strengths or product.weaknesses %}
    <div class="row" style="margin-top:20px;">
      <div class="info-card" style="background:#e8f5e9;">
        <h3>기술 강점</h3>
        <ul>{% for s in product.strengths %}<li>{{ s }}</li>{% endfor %}{% if not product.strengths %}<li>분석 중</li>{% endif %}</ul>
      </div>
      <div class="info-card" style="background:#ffebee;">
        <h3>기술 약점</h3>
        <ul>{% for w in product.weaknesses %}<li>{{ w }}</li>{% endfor %}{% if not product.weaknesses %}<li>분석 중</li>{% endif %}</ul>
      </div>
    </div>
    {% endif %}
  </div>

  <div class="section">
    <h2>3. 시장 분석</h2>
    <div class="info-card">
      <div class="row">
        <div>
          <p><strong>TAM:</strong> {{ market.tam or '-' }}</p>
          <p><strong>SAM:</strong> {{ market.sam or '-' }}</p>
          <p><strong>SOM:</strong> {{ market.som or '-' }}</p>
        </div>
        <div>
          <p><strong>CAGR:</strong> <span class="tag success">{{ market.cagr or '-' }}</span></p>
          <p><strong>세일즈 모션:</strong> {{ market.sales_motion or '-' }}</p>
        </div>
      </div>
      {% if market.problem_fit != '-' %}
      <p style="margin-top:16px;padding-top:16px;border-top:1px solid #e5e7eb;"><strong>Problem-Market Fit:</strong> {{ market.problem_fit }}</p>
      {% endif %}
      {% if market.demand %}
      <p style="margin-top:12px;"><strong>수요 동인:</strong></p>
      <ul style="margin:8px 0;">{% for d in market.demand %}<li>{{ d }}</li>{% endfor %}</ul>
      {% endif %}
      {% if market.risk %}
      <p style="margin-top:12px;"><strong>규제/진입장벽:</strong></p>
      <ul style="margin:8px 0;">{% for r in market.risk %}<li>{{ r }}</li>{% endfor %}</ul>
      {% endif %}
    </div>
  </div>

  <div class="section">
    <h2>4. 경쟁 분석</h2>
    {{ competition_table }}
  </div>

  {% if swot %}
  <div class="section">
    <h2>4-1. SWOT 분석</h2>
    <div class="swot-grid">
      <div class="swot-box strengths"><h3>💪 Strengths</h3><ul>{% for x in swot.strengths or [] %}<li>{{ x }}</li>{% endfor %}</ul></div>
      <div class="swot-box weaknesses"><h3>⚠️ Weaknesses</h3><ul>{% for x in swot.weaknesses or [] %}<li>{{ x }}</li>{% endfor %}</ul></div>
      <div class="swot-box opportunities"><h3>🚀 Opportunities</h3><ul>{% for x in swot.opportunities or [] %}<li>{{ x }}</li>{% endfor %}</ul></div>
      <div class="swot-box threats"><h3>⚡ Threats</h3><ul>{% for x in swot.threats or [] %}<li>{{ x }}</li>{% endfor %}</ul></div>
    </div>
  </div>
  {% endif %}

  <div class="section">
    <h2>5. 트랙션 및 재무 지표</h2>
    <div class="row">
      <div>
        <div class="info-card">
          <h3>주요 지표 (KPIs)</h3>
          {% if kpi_table_img %}
          <img src="data:image/png;base64,{{ kpi_table_img }}" alt="KPI Table">
          {% else %}
          <table>
            <tr><th>지표</th><th>값</th></tr>
            <tr><td>ARR</td><td>{{ kpis.arr }}</td></tr>
            <tr><td>QoQ 성장률</td><td>{{ kpis.qoq }}</td></tr>
            <tr><td>NDR</td><td>{{ kpis.ndr }}</td></tr>
            <tr><td>Gross Margin</td><td>{{ kpis.gross_margin }}</td></tr>
            <tr><td>Burn Rate</td><td>{{ kpis.burn }}</td></tr>
            <tr><td>Runway</td><td>{{ kpis.runway_months }}</td></tr>
          </table>
          {% endif %}
        </div>
        <div class="info-card" style="margin-top:16px;">
          <h3>트랙션</h3>
          <p><strong>펀딩:</strong> {{ traction.funding if traction else '-' }}</p>
          <p><strong>투자자:</strong> {{ ', '.join(traction.investors) if traction.investors and traction.investors[0] != 'unknown' else '-' }}</p>
          <p><strong>파트너십:</strong> {{ ', '.join(traction.partnerships[:3]) if traction.partnerships and traction.partnerships[0] != 'unknown' else '-' }}</p>
        </div>
      </div>
      <div>
        <div class="info-card">
          <h3>평가 점수</h3>
          <div class="score-card">
            <div class="score-items">
              {% for it in score_items %}
              <div class="score-item">
                <div class="score-label">{{ it.name }}</div>
                <div class="score-value">{{ it.score }}</div>
                {% if it.rationale %}<div class="score-rationale">{{ it.rationale }}</div>{% endif %}
              </div>
              {% endfor %}
            </div>
            <div class="total-score">
              <div class="value">{{ total_100 }}</div>
              <div class="label">총점 (100점 만점)</div>
            </div>
          </div>
          {% if scores_img %}
          <img src="data:image/png;base64,{{ scores_img }}" alt="Scores Bar" style="margin-top:16px;">
          {% endif %}
        </div>
      </div>
    </div>
  </div>

  {% if investment_thesis or red_flags or final_note %}
  <div class="section">
    <h2>6. 투자 논리 & 레드 플래그</h2>
    <div class="row">
      <div class="info-card">
        <h3>Investment Thesis</h3>
        <p style="line-height:1.8;">{{ investment_thesis or '작성 없음' }}</p>
        {% if final_note %}
        <p style="margin-top:16px;padding-top:16px;border-top:1px solid #e5e7eb;"><strong>최종 의견:</strong> {{ final_note }}</p>
        {% endif %}
      </div>
      <div class="info-card">
        <h3>Red Flags</h3>
        {% if red_flags %}
        <ul>{% for rf in red_flags %}<li><span class="tag danger">{{ rf }}</span></li>{% endfor %}</ul>
        {% else %}
        <p>특이사항 없음</p>
        {% endif %}
      </div>
    </div>
  </div>
  {% endif %}

  <div class="section">
    <h2>7. 팀 구성</h2>
    {% if team %}
    <div class="info-card"><ul>{% for t in team %}<li>{{ t }}</li>{% endfor %}</ul></div>
    {% else %}
    <div class="info-card"><p>정보 없음</p></div>
    {% endif %}
  </div>

  <div class="section">
    <h2>8. 리스크 분석 및 완화 방안</h2>
    <div class="row">
      {% if risks %}
      <div class="info-card" style="background:#fff3e0;">
        <h3>주요 리스크</h3>
        <ul>{% for r in risks %}<li>{{ r }}</li>{% endfor %}</ul>
      </div>
      {% endif %}
      {% if mitigations %}
      <div class="info-card" style="background:#e8f5e9;">
        <h3>완화 방안</h3>
        <ul>{% for m in mitigations %}<li>{{ m }}</li>{% endfor %}</ul>
      </div>
      {% endif %}
      {% if not risks and not mitigations %}
      <div class="info-card"><p>리스크 분석 진행 중</p></div>
      {% endif %}
    </div>
  </div>

  <div class="section">
    <h2>9. 추천 및 조건</h2>
    <div class="info-card">
      <p><strong>제안:</strong> <span class="tag primary">{{ decision_label }}</span></p>
      {% if required_data %}
      <p style="margin-top:16px;"><strong>선행 조건:</strong></p>
      <ul>{% for d in required_data %}<li>{{ d }}</li>{% endfor %}</ul>
      {% endif %}
      {{ kpi_scenarios_table or "" }}
    </div>
  </div>

  <div class="section">
    <h2>10. 참고 자료 및 출처</h2>
    {% if sources %}
    <div class="info-card">
      <p><strong>총 {{ sources|length }}개 출처</strong></p>
      <div style="display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;">
        <span class="tag primary">Discovery: {{ sources|selectattr('type', 'equalto', 'discovery')|list|length }}개</span>
        <span class="tag success">Tech: {{ sources|selectattr('type', 'equalto', 'tech')|list|length }}개</span>
        <span class="tag warning">Market: {{ (sources|selectattr('type', 'equalto', 'market')|list|length) + (sources|selectattr('type', 'equalto', 'report')|list|length) }}개</span>
        <span class="tag danger">Competitor: {{ sources|selectattr('type', 'equalto', 'competitor')|list|length }}개</span>
      </div>
    </div>
    
    <!-- 단계별 출처 구분 -->
    {% for stage_name in ['기업 탐색', '기술 분석', '시장 분석', '시장 분석 (리서치 보고서)', '경쟁사 분석'] %}
      {% set stage_sources = sources|selectattr('stage', 'equalto', stage_name)|list %}
      {% if stage_sources %}
      <div class="info-card" style="margin-top:16px;">
        <h3>{{ stage_name }}</h3>
        <ul class="sources-list">
          {% for s in stage_sources %}
          <li>
            <span class="source-type">{{ s.type }}</span>
            {% if s.url.startswith('http') %}
            <a href="{{ s.url }}" target="_blank" style="color:#0066cc;">{{ s.url|truncate(100) }}</a>
            {% else %}
            <span>{{ s.url }}</span>
            {% endif %}
          </li>
          {% endfor %}
        </ul>
      </div>
      {% endif %}
    {% endfor %}
    
    {% else %}
    <div class="info-card"><p>출처 정보 준비 중</p></div>
    {% endif %}
  </div>

  <!-- Appendix: 평가 방법론 -->
  {% if appendix %}
  <div class="section">
    <h2>Appendix: 평가 방법론</h2>
    <div class="info-card">
      <h3>점수 산출 방식</h3>
      <p>{{ appendix.scoring_methodology.description }}</p>
      <table style="margin-top:12px;">
        <thead>
          <tr><th>영역</th><th>가중치</th><th>평가 기준</th></tr>
        </thead>
        <tbody>
          {% for comp in appendix.scoring_methodology.components %}
          <tr>
            <td><strong>{{ comp.name }}</strong></td>
            <td><strong>{{ comp.weight }}</strong></td>
            <td>{{ comp.criteria }}</td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <p style="margin-top:16px;"><strong>리스크 페널티:</strong> {{ appendix.scoring_methodology.risk_penalty }}</p>
    </div>
    
    <div class="info-card" style="margin-top:16px;">
      <h3>투자 판단 기준</h3>
      <ul>
        <li><strong>투자 권고 (Recommend):</strong> {{ appendix.decision_threshold.recommend }}</li>
        <li><strong>조건부 검토 (Conditional):</strong> {{ appendix.decision_threshold.conditional }}</li>
        <li><strong>보류/거절 (Reject):</strong> {{ appendix.decision_threshold.reject }}</li>
      </ul>
    </div>
  </div>
  {% endif %}

</div>

</body>
</html>
"""