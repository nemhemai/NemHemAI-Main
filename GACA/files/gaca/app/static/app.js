/* ============================================================
   GACA Dashboard — Application Logic
   SPA Router · API Client · Charts · Animations
   ============================================================ */

const API = '';  // same origin

// ── Toast ──
function toast(msg, type = 'ok') {
  let c = document.getElementById('toast-container');
  if (!c) { c = document.createElement('div'); c.id = 'toast-container'; c.className = 'toast-container'; document.body.appendChild(c); }
  const t = document.createElement('div');
  t.className = `toast toast-${type}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3200);
}

// ── API helpers ──
async function api(path, opts = {}) {
  try {
    const r = await fetch(`${API}${path}`, {
      headers: { 'Content-Type': 'application/json', ...opts.headers },
      ...opts
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(e.detail || r.statusText);
    }
    return r.json();
  } catch (err) {
    toast(err.message, 'err');
    throw err;
  }
}

// ── Counter Animation ──
function animateCounter(el, target, suffix = '') {
  const dur = 1200;
  const start = performance.now();
  const from = 0;
  function tick(now) {
    const p = Math.min((now - start) / dur, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = from + (target - from) * ease;
    if (Number.isInteger(target)) {
      el.textContent = Math.round(val).toLocaleString() + suffix;
    } else {
      el.textContent = val.toFixed(1) + suffix;
    }
    if (p < 1) requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);
}

// ── Chart defaults ──
const chartColors = {
  green: 'rgba(6,214,160,0.8)',
  blue: 'rgba(17,138,178,0.8)',
  purple: 'rgba(123,47,247,0.8)',
  red: 'rgba(239,71,111,0.8)',
  yellow: 'rgba(255,209,102,0.8)',
  greenFill: 'rgba(6,214,160,0.15)',
  blueFill: 'rgba(17,138,178,0.15)',
  redFill: 'rgba(239,71,111,0.15)',
};

const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { labels: { color: '#8b95a8', font: { family: 'Inter', size: 11 } } },
    tooltip: {
      backgroundColor: 'rgba(15,20,35,0.95)',
      titleColor: '#e8ecf4',
      bodyColor: '#8b95a8',
      borderColor: 'rgba(80,120,200,0.2)',
      borderWidth: 1,
      cornerRadius: 8,
      padding: 10,
    }
  },
  scales: {
    x: { ticks: { color: '#555e72', font: { size: 10 } }, grid: { color: 'rgba(60,75,110,0.1)' } },
    y: { ticks: { color: '#555e72', font: { size: 10 } }, grid: { color: 'rgba(60,75,110,0.1)' } },
  }
};

let dashCharts = {};

// ── SPA Router ──
const views = [
  'dashboard', 'decisions', 'policies', 'explainability',
  'overrides', 'replay', 'appeals', 'rti', 'timeline',
  'reports', 'workflow', 'ingest'
];

function navigateTo(viewId) {
  views.forEach(v => {
    const el = document.getElementById(`view-${v}`);
    const nav = document.querySelector(`.nav-item[data-view="${v}"]`);
    if (el) el.classList.toggle('active', v === viewId);
    if (nav) nav.classList.toggle('active', v === viewId);
  });
  // Load view data
  if (viewId === 'dashboard') loadDashboard();
  window.location.hash = viewId;
}

// ── Init ──
document.addEventListener('DOMContentLoaded', () => {
  // Nav click handlers
  document.querySelectorAll('.nav-item[data-view]').forEach(item => {
    item.addEventListener('click', () => navigateTo(item.dataset.view));
  });

  // Route from hash
  const hash = window.location.hash.slice(1);
  navigateTo(views.includes(hash) ? hash : 'dashboard');

  // Bind search/action buttons
  bindDecisionSearch();
  bindPolicySearch();
  bindExplainSearch();
  bindOverrideSearch();
  bindReplaySearch();
  bindAppeals();
  bindRTI();
  bindTimeline();
  bindReports();
  bindIngest();
});

// ======================== DASHBOARD (4.17) ========================
async function loadDashboard() {
  try {
    const d = await api('/dashboard');

    // KPIs
    const kpis = [
      { id: 'kpi-apps',       value: d.applications_processed,  label: 'Applications Processed', cls: 'kpi-green' },
      { id: 'kpi-approval',   value: (d.approval_rate * 100),   label: 'Approval Rate',           cls: 'kpi-blue', suffix: '%' },
      { id: 'kpi-rejection',  value: (d.rejection_rate * 100),  label: 'Rejection Rate',          cls: 'kpi-red', suffix: '%' },
      { id: 'kpi-fraud',      value: d.fraud_indicators,        label: 'Fraud Indicators',        cls: 'kpi-red' },
      { id: 'kpi-violations', value: d.compliance_violations,   label: 'Compliance Violations',   cls: 'kpi-yellow' },
      { id: 'kpi-appeals',    value: d.appeal_statistics?.total || 0, label: 'Total Appeals',    cls: 'kpi-blue' },
      { id: 'kpi-risk',       value: d.risk_trends?.avg_risk_score || 0, label: 'Avg Risk Score', cls: 'kpi-red' },
      { id: 'kpi-assessments',value: d.risk_trends?.assessments || 0, label: 'Risk Assessments', cls: 'kpi-yellow' },
    ];

    kpis.forEach(k => {
      const el = document.getElementById(k.id);
      if (el) animateCounter(el, k.value, k.suffix || '');
    });

    // Charts
    renderApprovalChart(d);
    renderSchemeChart(d);
    renderDeptChart(d);
    renderRiskChart(d);

  } catch (e) { /* toast already shown */ }
}

function renderApprovalChart(d) {
  const ctx = document.getElementById('chart-approval');
  if (!ctx) return;
  if (dashCharts.approval) dashCharts.approval.destroy();
  dashCharts.approval = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Approved', 'Rejected', 'Other'],
      datasets: [{
        data: [d.approval_rate, d.rejection_rate, Math.max(0, 1 - d.approval_rate - d.rejection_rate)],
        backgroundColor: [chartColors.green, chartColors.red, 'rgba(85,94,114,0.3)'],
        borderWidth: 0,
        borderRadius: 4,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '72%',
      plugins: {
        legend: { position: 'bottom', labels: { color: '#8b95a8', font: { family: 'Inter', size: 11 }, padding: 16 } },
        tooltip: chartDefaults.plugins.tooltip,
      }
    }
  });
}

function renderSchemeChart(d) {
  const ctx = document.getElementById('chart-scheme');
  if (!ctx) return;
  if (dashCharts.scheme) dashCharts.scheme.destroy();
  const labels = Object.keys(d.scheme_utilization || {});
  const values = Object.values(d.scheme_utilization || {});
  dashCharts.scheme = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Applications', data: values, backgroundColor: chartColors.blue, borderRadius: 6, maxBarThickness: 40 }]
    },
    options: { ...chartDefaults, plugins: { ...chartDefaults.plugins, legend: { display: false } } }
  });
}

function renderDeptChart(d) {
  const ctx = document.getElementById('chart-dept');
  if (!ctx) return;
  if (dashCharts.dept) dashCharts.dept.destroy();
  const labels = Object.keys(d.department_performance || {});
  const values = Object.values(d.department_performance || {});
  const colors = [chartColors.green, chartColors.blue, chartColors.purple, chartColors.yellow, chartColors.red];
  dashCharts.dept = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Activity', data: values, backgroundColor: colors.slice(0, labels.length), borderRadius: 6, maxBarThickness: 40 }]
    },
    options: { ...chartDefaults, indexAxis: 'y', plugins: { ...chartDefaults.plugins, legend: { display: false } } }
  });
}

function renderRiskChart(d) {
  const ctx = document.getElementById('chart-risk');
  if (!ctx) return;
  if (dashCharts.risk) dashCharts.risk.destroy();
  dashCharts.risk = new Chart(ctx, {
    type: 'radar',
    data: {
      labels: ['Fraud Indicators', 'Compliance Violations', 'Avg Risk', 'Appeals', 'Assessments'],
      datasets: [{
        label: 'Risk Overview',
        data: [
          d.fraud_indicators || 0,
          d.compliance_violations || 0,
          (d.risk_trends?.avg_risk_score || 0) * 10,
          d.appeal_statistics?.total || 0,
          d.risk_trends?.assessments || 0,
        ],
        backgroundColor: chartColors.redFill,
        borderColor: chartColors.red,
        pointBackgroundColor: chartColors.red,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      scales: {
        r: {
          angleLines: { color: 'rgba(60,75,110,0.15)' },
          grid: { color: 'rgba(60,75,110,0.12)' },
          pointLabels: { color: '#8b95a8', font: { size: 10 } },
          ticks: { display: false }
        }
      },
      plugins: { legend: { display: false }, tooltip: chartDefaults.plugins.tooltip }
    }
  });
}

// ======================== 4.1 DECISION AUDIT ========================
function bindDecisionSearch() {
  const btn = document.getElementById('btn-decision-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const cid = document.getElementById('input-citizen-id').value.trim();
    if (!cid) return toast('Enter a Citizen ID', 'warn');
    try {
      const data = await api(`/decisions/citizen/${encodeURIComponent(cid)}`);
      const tbody = document.getElementById('decisions-tbody');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="2" class="empty-state"><p>No decisions found</p></td></tr>';
        return;
      }
      tbody.innerHTML = data.map(id =>
        `<tr><td class="mono">${escHtml(id)}</td><td><button class="btn btn-sm btn-secondary" onclick="quickExplain('${escHtml(id)}')">Explain</button> <button class="btn btn-sm btn-secondary" onclick="quickReplay('${escHtml(id)}')">Replay</button></td></tr>`
      ).join('');
    } catch (e) {}
  });
}

function quickExplain(did) {
  document.getElementById('input-explain-id').value = did;
  navigateTo('explainability');
  document.getElementById('btn-explain-search').click();
}

function quickReplay(did) {
  document.getElementById('input-replay-id').value = did;
  navigateTo('replay');
  document.getElementById('btn-replay-search').click();
}

// ======================== 4.2 POLICY VERSIONING ========================
function bindPolicySearch() {
  const btn = document.getElementById('btn-policy-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const name = document.getElementById('input-policy-name').value.trim();
    if (!name) return toast('Enter a Policy Name', 'warn');
    try {
      const data = await api(`/policies/${encodeURIComponent(name)}/versions`);
      const tbody = document.getElementById('policies-tbody');
      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="3" class="empty-state"><p>No versions found</p></td></tr>';
        return;
      }
      tbody.innerHTML = data.map(p =>
        `<tr><td class="mono">${escHtml(p.policy_id)}</td><td>${escHtml(p.rule_version || '—')}</td><td>${escHtml(p.effective_date || '—')}</td></tr>`
      ).join('');
    } catch (e) {}
  });
}

// ======================== 4.6 EXPLAINABILITY ========================
function bindExplainSearch() {
  const btn = document.getElementById('btn-explain-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const did = document.getElementById('input-explain-id').value.trim();
    if (!did) return toast('Enter a Decision ID', 'warn');
    try {
      const d = await api(`/explain/${encodeURIComponent(did)}`);
      const panel = document.getElementById('explain-result');
      panel.innerHTML = `
        <div class="detail-panel">
          <h3>🔍 ${escHtml(d.verdict)}</h3>
          <div class="detail-row"><span class="detail-label">Decision ID</span><span class="detail-value">${escHtml(d.decision_id)}</span></div>
          <div class="detail-row"><span class="detail-label">Policy Used</span><span class="detail-value">${escHtml(d.policy_used || '—')}</span></div>
          <div class="detail-row"><span class="detail-label">Rules Applied</span><span class="detail-value">${escHtml(d.rules_applied || '—')}</span></div>
          <div class="detail-row"><span class="detail-label">Confidence</span><span class="detail-value">${d.confidence_score !== null ? (d.confidence_score * 100).toFixed(1) + '%' : '—'}</span></div>
          <div class="detail-row"><span class="detail-label">AI Response</span><span class="detail-value">${escHtml(d.ai_generated_response || '—')}</span></div>
          ${d.reasons ? `<div class="detail-row"><span class="detail-label">Reasons</span><span class="detail-value">${(Array.isArray(d.reasons) ? d.reasons : [d.reasons]).map(r => `<span class="badge badge-info">${escHtml(r)}</span> `).join('')}</span></div>` : ''}
        </div>
        ${d.documents_used?.length ? `
        <div class="card-title"><span class="ct-icon">📄</span> Documents Used</div>
        <div class="evidence-chain">
          ${d.documents_used.map(doc => `<span class="evidence-node">${escHtml(doc || 'unknown')}</span>`).join('<span class="evidence-arrow">→</span>')}
        </div>` : ''}
        ${d.evidence_influencing_outcome?.length ? `
        <div class="card-title" style="margin-top:16px"><span class="ct-icon">🔗</span> Evidence Chain</div>
        <div class="data-table-wrap"><table class="data-table"><thead><tr><th>Document ID</th><th>Type</th><th>Role</th><th>Status</th></tr></thead><tbody>
          ${d.evidence_influencing_outcome.map(e => `<tr><td class="mono">${escHtml(e.document_id)}</td><td>${escHtml(e.document_type||'—')}</td><td>${escHtml(e.role||'—')}</td><td><span class="badge ${e.verification_status==='verified'?'badge-ok':'badge-warn'}">${escHtml(e.verification_status||'—')}</span></td></tr>`).join('')}
        </tbody></table></div>` : ''}
      `;
    } catch (e) {}
  });
}

// ======================== 4.7 HUMAN OVERRIDE ========================
function bindOverrideSearch() {
  const btn = document.getElementById('btn-override-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const did = document.getElementById('input-override-id').value.trim();
    if (!did) return toast('Enter a Decision ID', 'warn');
    try {
      const data = await api(`/overrides/${encodeURIComponent(did)}`);
      const panel = document.getElementById('override-result');
      if (!data.length) {
        panel.innerHTML = '<div class="empty-state"><div class="empty-icon">✅</div><p>No human overrides for this decision</p></div>';
        return;
      }
      panel.innerHTML = data.map(id => `<div class="detail-panel"><div class="detail-row"><span class="detail-label">Override ID</span><span class="detail-value">${escHtml(id)}</span></div></div>`).join('');
    } catch (e) {}
  });
}

// ======================== 4.10 DECISION REPLAY ========================
function bindReplaySearch() {
  const btn = document.getElementById('btn-replay-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const did = document.getElementById('input-replay-id').value.trim();
    if (!did) return toast('Enter a Decision ID', 'warn');
    try {
      const d = await api(`/replay/${encodeURIComponent(did)}`);
      const panel = document.getElementById('replay-result');
      panel.innerHTML = `
        <div class="detail-panel">
          <h3>🔄 Decision Replay — ${escHtml(d.decision_id)}</h3>
          <div class="detail-row"><span class="detail-label">Decision Result</span><span class="detail-value"><span class="badge ${d.decision_result?.toLowerCase().includes('eligible')||d.decision_result?.toLowerCase().includes('verified')?'badge-ok':'badge-danger'}">${escHtml(d.decision_result||'—')}</span></span></div>
          <div class="detail-row"><span class="detail-label">Model Version</span><span class="detail-value">${escHtml(d.model_version||'—')}</span></div>
          <div class="detail-row"><span class="detail-label">Prompt Template</span><span class="detail-value">${escHtml(d.prompt||'—')}</span></div>
        </div>
        <div class="charts-grid">
          <div class="card">
            <div class="card-title"><span class="ct-icon">👤</span> Citizen Profile Snapshot</div>
            <div class="json-block">${escHtml(JSON.stringify(d.citizen_profile, null, 2) || '—')}</div>
          </div>
          <div class="card">
            <div class="card-title"><span class="ct-icon">📋</span> Policy Version</div>
            <div class="json-block">${escHtml(JSON.stringify(d.policy_version, null, 2) || '—')}</div>
          </div>
        </div>
        ${d.retrieved_context ? `<div class="card"><div class="card-title"><span class="ct-icon">🔎</span> Retrieved Context</div><div class="json-block">${escHtml(JSON.stringify(d.retrieved_context, null, 2))}</div></div>` : ''}
        ${d.evidence?.length ? `
        <div class="card" style="margin-top:16px">
          <div class="card-title"><span class="ct-icon">🔗</span> Evidence</div>
          <div class="data-table-wrap"><table class="data-table"><thead><tr><th>Document ID</th><th>Type</th><th>Role</th><th>Status</th></tr></thead><tbody>
            ${d.evidence.map(e => `<tr><td class="mono">${escHtml(e.document_id)}</td><td>${escHtml(e.document_type||'—')}</td><td>${escHtml(e.role||'—')}</td><td><span class="badge ${e.verification_status==='verified'?'badge-ok':'badge-warn'}">${escHtml(e.verification_status||'—')}</span></td></tr>`).join('')}
          </tbody></table></div>
        </div>` : ''}
      `;
    } catch (e) {}
  });
}

// ======================== 4.13 APPEALS ========================
function bindAppeals() {
  const btn = document.getElementById('btn-submit-appeal');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const did = document.getElementById('input-appeal-decision').value.trim();
    const grounds = document.getElementById('input-appeal-grounds').value.trim();
    if (!did) return toast('Enter a Decision ID', 'warn');
    try {
      const d = await api(`/appeals?decision_id=${encodeURIComponent(did)}${grounds ? '&grounds=' + encodeURIComponent(grounds) : ''}`, { method: 'POST' });
      const panel = document.getElementById('appeal-result');
      panel.innerHTML = `
        <div class="detail-panel">
          <h3>📝 Appeal Submitted</h3>
          <div class="detail-row"><span class="detail-label">Appeal ID</span><span class="detail-value">${escHtml(d.appeal_id)}</span></div>
          <div class="detail-row"><span class="detail-label">Status</span><span class="detail-value"><span class="badge badge-info">${escHtml(d.status)}</span></span></div>
        </div>`;
      toast('Appeal submitted successfully', 'ok');
    } catch (e) {}
  });
}

// ======================== 4.14 RTI SUPPORT ========================
function bindRTI() {
  const btn = document.getElementById('btn-rti-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const cid = document.getElementById('input-rti-citizen').value.trim();
    if (!cid) return toast('Enter a Citizen ID', 'warn');
    try {
      const d = await api(`/rti/${encodeURIComponent(cid)}`);
      const panel = document.getElementById('rti-result');
      panel.innerHTML = `
        <div class="detail-panel">
          <h3>📋 RTI Package — ${escHtml(d.citizen_id)}</h3>
        </div>
        ${d.decision_summaries?.length ? `
        <div class="card" style="margin-bottom:16px">
          <div class="card-title"><span class="ct-icon">⚖️</span> Decision Summaries</div>
          <div class="data-table-wrap"><table class="data-table"><thead><tr><th>Decision ID</th><th>Scheme</th><th>Result</th><th>Timestamp</th></tr></thead><tbody>
            ${d.decision_summaries.map(s => `<tr><td class="mono">${escHtml(s.decision_id)}</td><td>${escHtml(s.scheme_id||'—')}</td><td><span class="badge ${s.decision_result?.toLowerCase().includes('eligible')||s.decision_result?.toLowerCase().includes('verified')?'badge-ok':'badge-danger'}">${escHtml(s.decision_result||'—')}</span></td><td class="mono">${escHtml(s.timestamp||'—')}</td></tr>`).join('')}
          </tbody></table></div>
        </div>` : ''}
        ${d.officer_actions?.length ? `
        <div class="card" style="margin-bottom:16px">
          <div class="card-title"><span class="ct-icon">👮</span> Officer Actions</div>
          <div class="data-table-wrap"><table class="data-table"><thead><tr><th>Action</th><th>Actor</th><th>Timestamp</th></tr></thead><tbody>
            ${d.officer_actions.map(a => `<tr><td>${escHtml(a.action)}</td><td class="mono">${escHtml(a.actor_id||'—')}</td><td class="mono">${escHtml(a.timestamp||'—')}</td></tr>`).join('')}
          </tbody></table></div>
        </div>` : ''}
        <div class="card">
          <div class="card-title"><span class="ct-icon">📜</span> Full RTI Package (JSON)</div>
          <div class="json-block">${escHtml(JSON.stringify(d, null, 2))}</div>
        </div>
      `;
    } catch (e) {}
  });
}

// ======================== 4.15 CITIZEN TIMELINE ========================
function bindTimeline() {
  const btn = document.getElementById('btn-timeline-search');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const cid = document.getElementById('input-timeline-citizen').value.trim();
    if (!cid) return toast('Enter a Citizen ID', 'warn');
    try {
      const data = await api(`/timeline/${encodeURIComponent(cid)}`);
      const panel = document.getElementById('timeline-result');
      if (!data.length) {
        panel.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>No timeline events found</p></div>';
        return;
      }
      panel.innerHTML = `<div class="timeline">${data.map(item => `
        <div class="timeline-item">
          <div class="tl-date">${escHtml(item.date || '—')}</div>
          <div class="tl-title">${escHtml(item.scheme || '—')}</div>
          <div class="tl-sub">${escHtml(item.department || 'Unknown Department')} · <span class="badge ${item.status === 'received' ? 'badge-info' : 'badge-ok'}">${escHtml(item.status || '—')}</span></div>
        </div>`).join('')}
      </div>`;
    } catch (e) {}
  });
}

// ======================== 4.16 REPORTS ========================
function bindReports() {
  const btn = document.getElementById('btn-generate-report');
  if (!btn) return;
  btn.addEventListener('click', async () => {
    const type = document.getElementById('input-report-type').value;
    const cid = document.getElementById('input-report-citizen').value.trim();
    const aid = document.getElementById('input-report-app').value.trim();
    const dept = document.getElementById('input-report-dept').value.trim();
    let params = new URLSearchParams();
    if (cid) params.set('citizen_id', cid);
    if (aid) params.set('application_id', aid);
    if (dept) params.set('department', dept);
    const qs = params.toString() ? '?' + params.toString() : '';
    try {
      const d = await api(`/reports/${encodeURIComponent(type)}${qs}`);
      const panel = document.getElementById('report-result');
      panel.innerHTML = `
        <div class="detail-panel">
          <h3>📊 ${escHtml(d.report_type)} Report</h3>
          <div class="detail-row"><span class="detail-label">Report ID</span><span class="detail-value">${escHtml(d.report_id)}</span></div>
        </div>
        <div class="card">
          <div class="card-title"><span class="ct-icon">📋</span> Report Content</div>
          <div class="json-block">${escHtml(JSON.stringify(d.content, null, 2))}</div>
        </div>`;
      toast('Report generated', 'ok');
    } catch (e) {}
  });
}

// ======================== SECTION 5 WORKFLOW ========================
// (visualized via the ingest response)

// ======================== SECTION 7 — EVENT INGEST ========================
function bindIngest() {
  const btn = document.getElementById('btn-ingest-event');
  if (!btn) return;

  // Pre-fill with sample entitlement event
  const sampleBtn = document.getElementById('btn-sample-entitlement');
  const sampleBtn2 = document.getElementById('btn-sample-verification');
  const textarea = document.getElementById('input-event-json');

  if (sampleBtn) {
    sampleBtn.addEventListener('click', () => {
      textarea.value = JSON.stringify({
        "event_type": "eligibility_decision",
        "responsible_agent": "entitlement",
        "citizen_id": "CIT-100045",
        "decision_id": "DEC-PMAY-" + String(Date.now()).slice(-4),
        "application_id": "APP-2026-" + String(Date.now()).slice(-4),
        "scheme_id": "PMAY",
        "decision_type": "eligibility",
        "decision_result": "Eligible",
        "confidence_score": 0.92,
        "policy_id": "POL-PMAY-2026-04",
        "profile_snapshot": {"income": 180000, "house": "none", "state": "Maharashtra", "reasons": ["Income below threshold", "No pucca house"]},
        "retrieved_context": {"reasons": ["Income below threshold", "No pucca house"]},
        "required_documents": ["Income Certificate", "Domicile Certificate"],
        "evidence_refs": [
          {"document_id": "DOC-IC-" + String(Date.now()).slice(-4), "document_type": "Income Certificate", "role": "Income Verification", "verification_status": "pending"}
        ],
        "ai_metadata": {
          "llm": "ollama/llama3", "model_version": "2026-04",
          "prompt_template": "eligibility_v3", "embedding_model": "bge-small",
          "generated_response": "Citizen meets PMAY income and housing criteria.",
          "confidence_score": 0.92, "safety_interventions": []
        }
      }, null, 2);
    });
  }

  if (sampleBtn2) {
    sampleBtn2.addEventListener('click', () => {
      textarea.value = JSON.stringify({
        "event_type": "verification_result",
        "responsible_agent": "verification",
        "citizen_id": "CIT-100045",
        "decision_id": "DEC-VER-" + String(Date.now()).slice(-4),
        "application_id": "APP-2026-0091",
        "scheme_id": "PMAY",
        "decision_type": "verification",
        "decision_result": "Verified",
        "confidence_score": 0.97,
        "policy_id": "POL-PMAY-2026-04",
        "evidence_refs": [
          {"document_id": "DOC-DC-" + String(Date.now()).slice(-4), "document_type": "Domicile Certificate", "role": "Residence Verification", "verification_status": "verified"}
        ]
      }, null, 2);
    });
  }

  btn.addEventListener('click', async () => {
    const raw = textarea.value.trim();
    if (!raw) return toast('Paste event JSON', 'warn');
    let payload;
    try { payload = JSON.parse(raw); } catch (e) { return toast('Invalid JSON: ' + e.message, 'err'); }
    try {
      const trace = await api('/events', { method: 'POST', body: JSON.stringify(payload) });
      // Render pipeline
      renderWorkflowTrace(trace);
      toast('Event ingested — 8 stages complete', 'ok');
    } catch (e) {}
  });
}

function renderWorkflowTrace(trace) {
  const panel = document.getElementById('workflow-result');
  if (!panel) return;

  // Animate pipeline stages
  const stages = document.querySelectorAll('#view-ingest .pipeline-stage, #view-workflow .pipeline-stage');
  stages.forEach((s, i) => {
    setTimeout(() => { s.classList.add('done'); }, i * 150);
  });

  const stageNames = [
    'stage_1_event_generation', 'stage_2_audit_capture', 'stage_3_evidence_association',
    'stage_4_policy_mapping', 'stage_5_compliance_validation', 'stage_6_risk_evaluation',
    'stage_7_governance_recording', 'stage_8_reporting_analytics'
  ];

  panel.innerHTML = stageNames.map((key, i) => {
    const data = trace[key];
    if (!data) return '';
    return `
      <div class="detail-panel" style="animation: fadeIn 0.3s ease ${i * 0.08}s both">
        <h3><span class="badge badge-ok">Stage ${i + 1}</span> ${key.replace(/stage_\d+_/, '').replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</h3>
        <div class="json-block">${escHtml(JSON.stringify(data, null, 2))}</div>
      </div>`;
  }).join('');
}

// ======================== WORKFLOW VIEW ========================
// The workflow view just shows the 8-stage pipeline + last trace

// ── Helpers ──
function escHtml(str) {
  if (str === null || str === undefined) return '—';
  const d = document.createElement('div');
  d.textContent = String(str);
  return d.innerHTML;
}
