HTML_TMPL = r"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{ company }} 투자 메모</title>
<style>
  * { box-sizing: border-box; }
  body { 
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Noto Sans KR", Arial, sans-serif; 
    margin: 0; 
    padding: 40px;
    background: #f8f9fa;
    color: #1a1a1a;
    line-height: 1.6;
  }
  .container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    padding: 48px;
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.08);
  }
  
  /* Header */
  .header {
    border-bottom: 3px solid #0066cc;
    padding-bottom: 24px;
    margin-bottom: 32px;
  }
  h1 { 
    margin: 0 0 12px 0; 
    font-size: 32px;
    font-weight: 700;
    color: #000;
  }
  .meta { 
    color: #666; 
    font-size: 14px;
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
  }
  .meta-item {
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .meta-item::before {
    content: "•";
    color: #0066cc;
  }
  
  /* Decision Banner */
  .decision-banner {
    background: linear-gradient(135deg, #0066cc 0%, #0052a3 100%);
    color: white;
    padding: 24px 28px;
    border-radius: 8px;
    margin-bottom: 32px;
  }
  .decision-banner h2 {
    margin: 0 0 12px 0;
    font-size: 18px;
    font-weight: 600;
    opacity: 0.9;
  }
  .decision-label {
    font-size: 28px;
    font-weight: 700;
    margin-bottom: 16px;
  }
  .decision-details {
    display: flex;
    gap: 32px;
    font-size: 15px;
    opacity: 0.95;
  }
  
  /* Key Points */
  .key-points {
    background: #f8f9fa;
    border-left: 4px solid #0066cc;
    padding: 20px 24px;
    margin: 24px 0;
    border-radius: 0 8px 8px 0;
  }
  .key-points ul {
    margin: 0;
    padding-left: 20px;
  }
  .key-points li {
    margin: 8px 0;
    color: #333;
  }
  
  /* Sections */
  .section { 
    margin-top: 48px; 
  }
  h2 { 
    font-size: 24px;
    font-weight: 700;
    margin: 0 0 20px 0;
    color: #000;
    border-bottom: 2px solid #e5e7eb;
    padding-bottom: 12px;
  }
  h3 { 
    font-size: 18px;
    font-weight: 600;
    margin: 16px 0 12px 0;
    color: #333;
  }
  
  /* Info Cards */
  .info-card {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
  }
  .info-card h3 {
    margin-top: 0;
    border: none;
    padding: 0;
    font-size: 16px;
    color: #0066cc;
  }
  .info-card ul {
    margin: 8px 0;
    padding-left: 20px;
  }
  .info-card li {
    margin: 6px 0;
    color: #444;
  }
  
  /* Grid Layout */
  .row { 
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-top: 24px;
  }
  @media (max-width: 768px) {
    .row { grid-template-columns: 1fr; }
  }
  
  /* Tables */
  table { 
    width: 100%; 
    border-collapse: collapse; 
    margin-top: 16px;
    font-size: 14px;
  }
  th, td { 
    border: 1px solid #e5e7eb; 
    padding: 12px 16px; 
    text-align: left;
  }
  th { 
    background: #f8f9fa;
    font-weight: 600;
    color: #333;
  }
  tr:hover {
    background: #f8f9fa;
  }
  
  /* SWOT Grid */
  .swot-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-top: 20px;
  }
  .swot-box {
    border-radius: 8px;
    padding: 20px;
  }
  .swot-box.strengths { background: #e8f5e9; border-left: 4px solid #4caf50; }
  .swot-box.weaknesses { background: #ffebee; border-left: 4px solid #f44336; }
  .swot-box.opportunities { background: #e3f2fd; border-left: 4px solid #2196f3; }
  .swot-box.threats { background: #fff3e0; border-left: 4px solid #ff9800; }
  .swot-box h3 {
    margin-top: 0;
    font-size: 16px;
  }
  .swot-box ul {
    margin: 8px 0;
    padding-left: 20px;
    font-size: 14px;
  }
  
  /* Score Card */
  .score-card {
    background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
    border-radius: 8px;
    padding: 24px;
    margin-top: 20px;
  }
  .score-items {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 16px;
    margin-bottom: 20px;
  }
  .score-item {
    text-align: center;
    padding: 12px;
    background: white;
    border-radius: 6px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
  }
  .score-label {
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  .score-value {
    font-size: 24px;
    font-weight: 700;
    color: #0066cc;
    margin-top: 4px;
  }
  .total-score {
    text-align: center;
    padding: 20px;
    background: white;
    border-radius: 8px;
    margin-top: 16px;
  }
  .total-score .value {
    font-size: 48px;
    font-weight: 700;
    color: #0066cc;
  }
  .total-score .label {
    font-size: 14px;
    color: #666;
    margin-top: 8px;
  }
  
  /* Charts */
  img { 
    max-width: 100%;
    border-radius: 8px;
    margin-top: 16px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
  
  /* Tags */
  .tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 16px;
    font-size: 13px;
    font-weight: 500;
    margin: 4px;
  }
  .tag.primary { background: #e3f2fd; color: #1976d2; }
  .tag.success { background: #e8f5e9; color: #388e3c; }
  .tag.warning { background: #fff3e0; color: #f57c00; }
  .tag.danger { background: #ffebee; color: #d32f2f; }
  
  /* Sources */
  .sources-list {
    font-size: 13px;
  }
  .sources-list li {
    margin: 8px 0;
    word-break: break-all;
  }
  .source-type {
    display: inline-block;
    padding: 2px 8px;
    background: #0066cc;
    color: white;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
    margin-right: 8px;
  }
  
  /* Print styles */
  @media print {
    body { background: white; padding: 0; }
    .container { box-shadow: none; }
  }
</style>
</head>
<body>

<div class="container">
  <!-- Header -->
  <div class="header">
    <h1>{{ company }} 투자 메모</h1>
    <div class="meta">
      <span class="meta-item">버전: {{ version }}</span>
      <span class="meta-item">작성일: {{ today }}</span>
      <span class="meta-item">분석자: {{ author }}</span>
      <span class="meta-item">출처: {{ source_count }}개</span>
    </div>
  </div>

  <!-- Decision Banner -->
  <div class="decision-banner">
    <h2>투자 판단</h2>
    <div class="decision-label">{{ decision_label }}</div>
    <div class="decision-details">
      <div>목표 지분: <strong>{{ target_equity }}</strong></div>
      <div>투자 규모: <strong>{{ check_size }}</strong></div>
    </div>
  </div>

  <!-- Key Points -->
  {% if key_points %}
  <div class="key-points">
    <h3 style="margin-top: 0;">핵심 요약</h3>
    <ul>
      {% for p in key_points if p %}<li>{{ p }}</li>{% endfor %}
    </ul>
  </div>
  {% endif %}

  <!-- 1. 회사 개요 -->
  <div class="section">
    <h2>1. 회사 개요</h2>
    <div class="info-card">
      <div class="row">
        <div>
          <p><strong>설립:</strong> {{ overview.founded or '-' }}</p>
          <p><strong>지역:</strong> {{ overview.region or '-' }}</p>
          <p><strong>창업자:</strong> {{ overview.founder or '-' }}</p>
        </div>
        <div>
          <p><strong>산업:</strong> {{ overview.segment or '-' }}</p>
          <p><strong>웹사이트:</strong> {{ overview.website or '-' }}</p>
          <p><strong>최근 라운드:</strong> {{ overview.round or '-' }}</p>
        </div>
      </div>
      <p style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
        <strong>소개:</strong> {{ overview.one_liner or '-' }}
      </p>
    </div>
  </div>

  <!-- 2. 제품·기술 -->
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
    <div class="row" style="margin-top: 20px;">
      <div class="info-card" style="background: #e8f5e9;">
        <h3>기술 강점</h3>
        <ul>
          {% for s in product.strengths %}<li>{{ s }}</li>{% endfor %}
          {% if not product.strengths %}<li>분석 중</li>{% endif %}
        </ul>
      </div>
      <div class="info-card" style="background: #ffebee;">
        <h3>기술 약점</h3>
        <ul>
          {% for w in product.weaknesses %}<li>{{ w }}</li>{% endfor %}
          {% if not product.weaknesses %}<li>분석 중</li>{% endif %}
        </ul>
      </div>
    </div>
    {% endif %}
  </div>

  <!-- 3. 시장 분석 -->
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
      <p style="margin-top: 16px; padding-top: 16px; border-top: 1px solid #e5e7eb;">
        <strong>Problem-Market Fit:</strong> {{ market.problem_fit }}
      </p>
      {% endif %}
      
      {% if market.demand %}
      <p style="margin-top: 12px;"><strong>수요 동인:</strong></p>
      <ul style="margin: 8px 0;">
        {% for d in market.demand %}<li>{{ d }}</li>{% endfor %}
      </ul>
      {% endif %}
      
      {% if market.risk %}
      <p style="margin-top: 12px;"><strong>규제/진입장벽:</strong></p>
      <ul style="margin: 8px 0;">
        {% for r in market.risk %}<li>{{ r }}</li>{% endfor %}
      </ul>
      {% endif %}
    </div>
  </div>

  <!-- 4. 경쟁 구도 -->
  <div class="section">
    <h2>4. 경쟁 분석</h2>
    {{ competition_table }}
  </div>

  <!-- 4-1. SWOT -->
  {% if swot %}
  <div class="section">
    <h2>4-1. SWOT 분석</h2>
    <div class="swot-grid">
      <div class="swot-box strengths">
        <h3>💪 Strengths (강점)</h3>
        <ul>
          {% for x in swot.strengths or [] %}<li>{{ x }}</li>{% endfor %}
        </ul>
      </div>
      <div class="swot-box weaknesses">
        <h3>⚠️ Weaknesses (약점)</h3>
        <ul>
          {% for x in swot.weaknesses or [] %}<li>{{ x }}</li>{% endfor %}
        </ul>
      </div>
      <div class="swot-box opportunities">
        <h3>🚀 Opportunities (기회)</h3>
        <ul>
          {% for x in swot.opportunities or [] %}<li>{{ x }}</li>{% endfor %}
        </ul>
      </div>
      <div class="swot-box threats">
        <h3>⚡ Threats (위협)</h3>
        <ul>
          {% for x in swot.threats or [] %}<li>{{ x }}</li>{% endfor %}
        </ul>
      </div>
    </div>
  </div>
  {% endif %}

  <!-- 5-6. 트랙션 & 재무 -->
  <div class="section">
    <h2>5. 트랙션 및 재무 지표</h2>
    <div class="row">
      <div>
        <div class="info-card">
          <h3>주요 지표 (KPIs)</h3>
          <img src="data:image/png;base64,{{ kpi_table_img }}" alt="KPI Table">
        </div>
      </div>
      <div>
        <div class="info-card">
          <h3>평가 점수</h3>
          <img src="data:image/png;base64,{{ scores_img }}" alt="Scores Bar">
        </div>
      </div>
    </div>
  </div>

  <!-- 7. 팀 -->
  {% if team %}
  <div class="section">
    <h2>7. 팀 구성</h2>
    <div class="info-card">
      <ul>
        {% for t in team %}<li>{{ t }}</li>{% endfor %}
      </ul>
    </div>
  </div>
  {% endif %}

  <!-- 8. 리스크 & 완화 -->
  <div class="section">
    <h2>8. 리스크 분석 및 완화 방안</h2>
    <div class="row">
      {% if risks %}
      <div class="info-card" style="background: #fff3e0;">
        <h3>주요 리스크</h3>
        <ul>
          {% for r in risks %}<li>{{ r }}</li>{% endfor %}
        </ul>
      </div>
      {% endif %}
      {% if mitigations %}
      <div class="info-card" style="background: #e8f5e9;">
        <h3>완화 방안</h3>
        <ul>
          {% for m in mitigations %}<li>{{ m }}</li>{% endfor %}
        </ul>
      </div>
      {% endif %}
      {% if not risks and not mitigations %}
      <div class="info-card">
        <p>리스크 분석 진행 중</p>
      </div>
      {% endif %}
    </div>
  </div>

  <!-- 9. 평가 스코어 -->
  <div class="section">
    <h2>9. 종합 평가 점수</h2>
    <div class="score-card">
      <div class="score-items">
        <div class="score-item">
          <div class="score-label">Founder</div>
          <div class="score-value">{{ scores.founder }}</div>
        </div>
        <div class="score-item">
          <div class="score-label">Market</div>
          <div class="score-value">{{ scores.market }}</div>
        </div>
        <div class="score-item">
          <div class="score-label">Tech</div>
          <div class="score-value">{{ scores.tech }}</div>
        </div>
        <div class="score-item">
          <div class="score-label">Moat</div>
          <div class="score-value">{{ scores.moat }}</div>
        </div>
        <div class="score-item">
          <div class="score-label">Traction</div>
          <div class="score-value">{{ scores.traction }}</div>
        </div>
        <div class="score-item">
          <div class="score-label">Terms</div>
          <div class="score-value">{{ scores.terms }}</div>
        </div>
      </div>
      <div class="total-score">
        <div class="value">{{ scores.total_100 }}</div>
        <div class="label">총점 (100점 만점)</div>
      </div>
    </div>
  </div>

  <!-- 10. 추천사항 -->
  <div class="section">
    <h2>10. 투자 추천 및 조건</h2>
    <div class="info-card">
      <p><strong>제안:</strong> <span class="tag primary">{{ decision_label }}</span></p>
      {% if required_data %}
      <p style="margin-top: 16px;"><strong>선행 조건:</strong></p>
      <ul>
        {% for d in required_data %}<li>{{ d }}</li>{% endfor %}
      </ul>
      {% endif %}
      {{ kpi_scenarios_table or "" }}
    </div>
  </div>

  <!-- 11. 출처 -->
  <div class="section">
    <h2>11. 참고 자료 및 출처</h2>
    {% if sources %}
    <ul class="sources-list">
      {% for s in sources %}
      <li>
        <span class="source-type">{{ (s.type or 'WEB') | upper }}</span>
        <a href="{{ s.url or '#' }}" target="_blank">{{ s.url or '' }}</a>
      </li>
      {% endfor %}
    </ul>
    {% else %}
    <div class="info-card">
      <p>출처 정보 준비 중</p>
    </div>
    {% endif %}
  </div>

</div>

</body>
</html>"""