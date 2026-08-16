// CodeGraph Studio — Interactive Web Client (wired to the live REST API)

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initSidebarNav();
  initActions();
  loadStatus();     // health + evaluation badges + footer stats
  loadRepositories(); // repo selector + graph canvas
  loadDrift();
});

// ── Shared client state ───────────────────────────────────
const state = {
  repoId: null,
  lastPlanId: null,
  workflowId: null,
  traces: [],
};

// ── API helper with tracing + error handling ──────────────
async function api(path, options = {}) {
  const started = performance.now();
  try {
    const res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    const body = await res.json().catch(() => ({}));
    const elapsed = Math.round(performance.now() - started);
    recordTrace(path, res.ok, elapsed, body.trace_id || res.headers.get('X-Trace-ID'));
    if (!res.ok) {
      const detail = body && body.detail ? body.detail : `HTTP ${res.status}`;
      throw new Error(detail);
    }
    return body.data;
  } catch (err) {
    recordTrace(path, false, Math.round(performance.now() - started));
    throw err;
  }
}

function recordTrace(path, ok, elapsedMs, traceId) {
  state.traces.unshift({ path, ok, elapsedMs, traceId: traceId || null, at: new Date() });
  state.traces = state.traces.slice(0, 25);
  renderTraces();
}

// ── Tab Switching (WAI-ARIA pattern) ──────────────────────
function initTabs() {
  const tabs = Array.from(document.querySelectorAll('.tab-button'));
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activateTab(tab, tabs));
    tab.addEventListener('keydown', (e) => {
      if (e.key !== 'ArrowRight' && e.key !== 'ArrowLeft') return;
      e.preventDefault();
      const dir = e.key === 'ArrowRight' ? 1 : -1;
      const next = tabs[(i + dir + tabs.length) % tabs.length];
      next.focus();
      activateTab(next, tabs);
    });
  });
}

function activateTab(tab, tabs) {
  tabs.forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
    t.tabIndex = -1;
  });
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

  tab.classList.add('active');
  tab.setAttribute('aria-selected', 'true');
  tab.tabIndex = 0;
  const target = document.getElementById(tab.dataset.tab);
  if (target) target.classList.add('active');
}

function switchToTab(tabId) {
  const tab = document.querySelector(`.tab-button[data-tab="${tabId}"]`);
  if (tab) activateTab(tab, Array.from(document.querySelectorAll('.tab-button')));
}

// ── Sidebar Navigation ───────────────────────────────────
function initSidebarNav() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', () => {
      navItems.forEach(n => {
        n.classList.remove('active');
        n.removeAttribute('aria-current');
      });
      item.classList.add('active');
      item.setAttribute('aria-current', 'page');
      // Anchor default behavior scrolls to the section; also surface its tab.
      if (item.dataset.tab) switchToTab(item.dataset.tab);
    });
  });
}

// ── Toast Notifications (replaces alert()) ───────────────
function showToast(message, type = 'info') {
  let toast = document.getElementById('toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'toast';
    toast.className = 'toast';
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.className = `toast ${type}`;

  // Trigger reflow for re-animation
  void toast.offsetWidth;
  toast.classList.add('visible');

  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => {
    toast.classList.remove('visible');
  }, 3000);
}

// ── Status header / footer from live endpoints ───────────
async function loadStatus() {
  const serviceBadge = document.getElementById('hdr-service');
  const serviceText = document.getElementById('hdr-service-text');
  try {
    await api('/health');
    serviceBadge.classList.add('active');
    serviceText.textContent = 'API: healthy';
  } catch {
    serviceBadge.classList.remove('active');
    serviceText.textContent = 'API: unreachable';
  }

  try {
    const evalData = await api('/evaluations/latest');
    const quality = document.getElementById('hdr-quality');
    quality.innerHTML = '';
    quality.textContent = `Eval: ${evalData.status} (${evalData.benchmark_cases} cases)`;
    quality.classList.toggle('success', evalData.quality_gate === true);

    const recall = evalData.metrics && evalData.metrics.retrieval_recall_at_5;
    document.getElementById('hdr-conf').textContent = recall ? `Recall@5: ${recall}` : 'Recall@5: —';

    document.getElementById('stat-eval-cases').textContent = `${evalData.benchmark_cases} eval cases`;
  } catch {
    document.getElementById('hdr-quality').textContent = 'Eval: unavailable';
  }
}

// ── Repository selector + live graph canvas ──────────────
async function loadRepositories() {
  const select = document.getElementById('repo-select');
  if (!select) return;
  let repos = [];
  try {
    repos = await api('/repositories');
  } catch {
    showToast('Could not load repositories — is the API running?', 'error');
    return;
  }

  select.innerHTML = '';
  repos.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.repository_id;
    opt.textContent = r.name || r.repository_id;
    select.appendChild(opt);
  });
  document.getElementById('stat-repos').textContent = `repositories: ${repos.length}`;

  const setRepo = () => {
    state.repoId = select.value || null;
    loadGraph();
    loadDrift();
  };
  select.addEventListener('change', setRepo);
  if (repos.length > 0) setRepo();
}

async function loadGraph() {
  const svg = document.getElementById('graph-svg');
  if (!svg || !state.repoId) return;

  let data;
  try {
    data = await api(`/repositories/${encodeURIComponent(state.repoId)}/graph`);
  } catch (err) {
    showToast(`Graph load failed: ${err.message}`, 'error');
    return;
  }

  const nodes = data.nodes || [];
  const edges = data.edges || [];
  document.getElementById('graph-stats').textContent =
    nodes.length ? `${nodes.length} nodes · ${edges.length} edges` : 'no data';

  if (!nodes.length) {
    renderGraphEmpty(svg, data.note || 'No indexed entities in the graph for this repository yet.');
    return;
  }
  renderGraph(svg, nodes, edges);
}

function renderGraphEmpty(svg, message) {
  clearSVG(svg);
  const text = createSVG('text', {
    x: '50%', y: '50%',
    'text-anchor': 'middle', 'dominant-baseline': 'central',
    fill: '#5a6a6d', 'font-size': '14',
    'font-family': "'JetBrains Mono', monospace",
  });
  text.textContent = message;
  svg.appendChild(text);
  document.getElementById('inspect-header').textContent = 'Interactive Knowledge Graph';
}

const KIND_COLORS = { Class: '#4edea3', Method: '#00daf3', Function: '#ffb95f' };
const KIND_ORDER = { Class: 0, Method: 1, Function: 2 };

function truncateLabel(text, max = 14) {
  return text.length > max ? text.slice(0, max - 1) + '…' : text;
}

function renderGraph(svg, nodes, edges) {
  clearSVG(svg);

  const rect = svg.getBoundingClientRect();
  const w = rect.width || 800;
  const h = rect.height || 500;
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);

  const cx = w / 2, cy = h / 2;

  // Concentric-ring layout: classes innermost, then methods/functions,
  // spread across 1-3 rings so labels never collide at high node counts.
  const sorted = [...nodes].sort(
    (a, b) => (KIND_ORDER[a.kind] ?? 3) - (KIND_ORDER[b.kind] ?? 3)
  );
  const ringCount = Math.min(3, Math.max(1, Math.ceil(sorted.length / 14)));
  const maxR = Math.min(w, h) * 0.40;
  const minR = maxR * 0.35;
  // Distribute nodes across rings proportionally to ring circumference.
  const ringWeights = Array.from({ length: ringCount }, (_, i) => minR + (i / Math.max(1, ringCount - 1)) * (maxR - minR));
  const weightSum = ringWeights.reduce((a, b) => a + b, 0);
  const perRing = ringWeights.map(rw => Math.max(1, Math.round((rw / weightSum) * sorted.length)));
  // Trim/extend to match exactly
  let diff = sorted.length - perRing.reduce((a, b) => a + b, 0);
  let ri = 0;
  while (diff !== 0) {
    const idx = ri % ringCount;
    perRing[idx] += diff > 0 ? 1 : -1;
    diff += diff > 0 ? -1 : 1;
    ri++;
  }

  const nodeRadius = Math.max(12, Math.min(26, Math.min(w, h) * (0.5 / Math.sqrt(sorted.length))));
  const labelSize = Math.max(9, Math.round(nodeRadius * 0.42));

  const positions = {};
  let cursor = 0;
  ringWeights.forEach((ringR, ringIdx) => {
    const count = perRing[ringIdx];
    for (let i = 0; i < count && cursor < sorted.length; i++, cursor++) {
      const node = sorted[cursor];
      // Stagger ring start angles so labels don't line up radially.
      const angle = (2 * Math.PI * i) / count + (ringIdx * Math.PI) / ringCount - Math.PI / 2;
      positions[node.id] = { x: cx + Math.cos(angle) * ringR, y: cy + Math.sin(angle) * ringR, ring: ringIdx };
    }
  });

  const nodeIds = new Set(nodes.map(n => n.id));
  const visibleEdges = edges.filter(e => nodeIds.has(e.source) && nodeIds.has(e.target));
  const dense = sorted.length > 18 || visibleEdges.length > 14;

  // ── Edges ──
  const edgeLines = [];
  visibleEdges.forEach(edge => {
    const src = positions[edge.source];
    const tgt = positions[edge.target];
    if (!src || !tgt) return;

    const line = createSVG('line', {
      x1: src.x, y1: src.y, x2: tgt.x, y2: tgt.y,
      stroke: '#3b494c', 'stroke-width': '1.2',
      'marker-end': 'url(#arrow)',
    });
    svg.appendChild(line);
    edgeLines.push({ line, edge });

    // Edge labels only when the graph is sparse enough to read them.
    if (!dense) {
      const label = createSVG('text', {
        x: (src.x + tgt.x) / 2, y: (src.y + tgt.y) / 2 - 4,
        'text-anchor': 'middle', 'dominant-baseline': 'central',
        'font-size': Math.max(9, labelSize - 2),
        'font-family': "'JetBrains Mono', monospace",
        fill: '#5a6a6d', 'pointer-events': 'none',
      });
      label.textContent = edge.type;
      svg.appendChild(label);
    }
  });

  // ── Nodes ──
  let selectedNode = null;
  nodes.forEach(node => {
    const pos = positions[node.id];
    if (!pos) return;
    const color = KIND_COLORS[node.kind] || '#c3f5ff';
    const g = createSVG('g', {
      transform: `translate(${pos.x}, ${pos.y})`,
      class: 'graph-node', 'data-id': node.id,
    });

    g.appendChild(createSVG('circle', {
      r: nodeRadius, fill: '#171f33', stroke: color, 'stroke-width': '2.5',
    }));

    // Hover tooltip: full qualified name, kind, and file.
    const title = createSVG('title', {});
    title.textContent = `${node.qualified_name} (${node.kind})\n${node.file_path || ''}`;
    g.appendChild(title);

    const label = createSVG('text', {
      'text-anchor': 'middle', y: nodeRadius + labelSize + 4,
      fill: '#e6ecff', 'font-size': labelSize, 'font-weight': '500',
      'font-family': "'JetBrains Mono', monospace", 'pointer-events': 'none',
    });
    label.textContent = truncateLabel(node.name);
    g.appendChild(label);

    g.addEventListener('click', () => {
      if (selectedNode) {
        const prev = svg.querySelector(`.graph-node[data-id="${selectedNode}"]`);
        if (prev) prev.classList.remove('selected');
      }
      g.classList.add('selected');
      selectedNode = node.id;
      highlightNeighbors(svg, edgeLines, node.id);
      inspectNode(node);
    });

    svg.appendChild(g);
  });
}

// Dim nodes/edges not connected to the selected node so its neighborhood reads clearly.
function highlightNeighbors(svg, edgeLines, nodeId) {
  const adjacent = new Set([nodeId]);
  edgeLines.forEach(({ line, edge }) => {
    const connected = edge.source === nodeId || edge.target === nodeId;
    line.classList.toggle('edge-active', connected);
    if (connected) {
      adjacent.add(edge.source);
      adjacent.add(edge.target);
    }
  });
  svg.querySelectorAll('.graph-node').forEach(g => {
    g.classList.toggle('dimmed', !adjacent.has(g.dataset.id));
  });
}

function clearSVG(svg) {
  Array.from(svg.children).forEach(child => {
    if (child.tagName.toLowerCase() !== 'defs') svg.removeChild(child);
  });
}

function inspectNode(node) {
  const header = document.getElementById('inspect-header');
  if (header) header.textContent = `Selected: ${node.qualified_name} (${node.kind})`;
  showToast(`Inspecting ${node.name} — ${node.kind}`, 'info');
}

function createSVG(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v);
  }
  return el;
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// ── Agentic Investigation (real API) ─────────────────────
async function runInvestigation() {
  const input = document.getElementById('search-input');
  const btn = document.getElementById('btn-run-query');
  const container = document.getElementById('investigation-steps');
  const question = input ? input.value.trim() : '';
  if (!question) {
    showToast('Please enter a question first.', 'info');
    return;
  }
  if (!state.repoId) {
    showToast('Select a repository first.', 'info');
    return;
  }

  btn.disabled = true;
  btn.textContent = 'Investigating…';
  container.innerHTML = '<div class="card empty-state"><p class="card-desc">Running agentic investigation…</p></div>';

  try {
    const data = await api('/investigate', {
      method: 'POST',
      body: JSON.stringify({ question, repository_id: state.repoId }),
    });
    renderInvestigation(data);
    showToast('Investigation complete.', 'success');
  } catch (err) {
    container.innerHTML = `<div class="card empty-state"><p class="card-desc">Investigation failed: ${escapeHtml(err.message)}</p></div>`;
    showToast(`Investigation failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Investigate';
  }
}

function renderInvestigation(data) {
  const container = document.getElementById('investigation-steps');
  container.innerHTML = '';

  const answer = document.createElement('div');
  answer.className = 'card';
  answer.innerHTML = `
    <div class="card-title">Answer</div>
    <p class="card-desc">${escapeHtml(data.final_answer || 'No answer produced.')}</p>
    <span class="evidence-badge">trace ${escapeHtml(data.trace_id || '—')} · investigation ${escapeHtml(data.investigation_id || '—')}</span>
  `;
  container.appendChild(answer);

  const citations = data.citations || [];
  if (citations.length) {
    const step = document.createElement('div');
    step.className = 'step-card';
    step.innerHTML = `
      <div class="step-header">
        <span class="step-number">✓</span>
        <span class="step-title">Evidence Citations (${citations.length})</span>
      </div>
      ${citations.map(c => `<span class="evidence-badge">${escapeHtml(String(c))}</span>`).join(' ')}
    `;
    container.appendChild(step);
  }
}

// ── Change Plan → Approve → Patch (real gated flow) ──────
async function planChange() {
  const input = document.getElementById('change-request-input');
  const btn = document.getElementById('btn-approve');
  const patchBtn = document.getElementById('btn-generate-patch');
  const request = input ? input.value.trim() : '';
  if (!request) {
    showToast('Describe the change you want first.', 'info');
    return;
  }
  if (!state.repoId) {
    showToast('Select a repository first.', 'info');
    return;
  }

  try {
    const data = await api('/changes/plan', {
      method: 'POST',
      body: JSON.stringify({ change_request: request, repository_id: state.repoId }),
    });
    state.lastPlanId = data.plan_id;
    state.workflowId = data.workflow_id;
    renderGitState(data);
    renderDiff(null, data.is_valid
      ? `Plan ${data.plan_id} ready — targets: ${(data.target_files || []).join(', ') || 'none'}. Approve it to enable patch generation.`
      : `Plan rejected: ${data.rejection_reason || 'unknown reason'}`);
    btn.disabled = !data.is_valid;
    patchBtn.disabled = true;
    showToast(data.is_valid ? 'Change plan created — awaiting approval.' : 'Plan rejected by safety validation.', data.is_valid ? 'success' : 'error');
  } catch (err) {
    showToast(`Planning failed: ${err.message}`, 'error');
  }
}

async function approvePlan() {
  const btn = document.getElementById('btn-approve');
  const patchBtn = document.getElementById('btn-generate-patch');
  if (!state.lastPlanId) return;

  try {
    const data = await api(`/changes/${encodeURIComponent(state.lastPlanId)}/approve`, { method: 'POST' });
    btn.textContent = '✓ Plan Approved';
    btn.disabled = true;
    patchBtn.disabled = false;
    renderGitState(data);
    showToast('Human approval granted — patch generation enabled.', 'success');
  } catch (err) {
    showToast(`Approval failed: ${err.message}`, 'error');
  }
}

async function generatePatch() {
  if (!state.lastPlanId) return;
  const patchBtn = document.getElementById('btn-generate-patch');
  patchBtn.disabled = true;
  patchBtn.textContent = 'Generating…';

  try {
    const data = await api('/changes/patch', {
      method: 'POST',
      body: JSON.stringify({ plan_id: state.lastPlanId }),
    });
    renderDiff(data.patch, null);
    renderGitState(data);
    showToast(`Patch ${data.status} — see Patch Repair tab.`, data.status === 'VALIDATED' ? 'success' : 'info');
  } catch (err) {
    showToast(`Patch generation failed: ${err.message}`, 'error');
  } finally {
    patchBtn.disabled = false;
    patchBtn.textContent = 'Generate Patch';
  }
}

async function runRepair() {
  const input = document.getElementById('change-request-input');
  const failure = input && input.value.trim();
  if (!failure) {
    showToast('Enter the failure description in the change request field first.', 'info');
    return;
  }
  if (!state.repoId) return;

  try {
    const data = await api('/repairs', {
      method: 'POST',
      body: JSON.stringify({ failure_message: failure, repository_id: state.repoId }),
    });
    renderDiff(data.final_patch, `Repair ${data.repair_status} after ${data.iterations} iteration(s).`);
    showToast(`Repair ${data.repair_status}.`, data.repair_status === 'REPAIRED' ? 'success' : 'info');
  } catch (err) {
    showToast(`Repair failed: ${err.message}`, 'error');
  }
}

// Render a unified diff with proper +/- coloring, or an informational message.
function renderDiff(diffText, message) {
  const viewer = document.getElementById('diff-viewer');
  viewer.innerHTML = '';

  if (!diffText) {
    const line = document.createElement('div');
    line.className = 'diff-line diff-header';
    line.textContent = message || 'No patch generated yet.';
    viewer.appendChild(line);
    return;
  }

  diffText.split('\n').forEach(raw => {
    const line = document.createElement('div');
    line.className = 'diff-line';
    if (raw.startsWith('--- a/') || raw.startsWith('+++ b/')) line.classList.add('diff-header');
    else if (raw.startsWith('@@')) line.classList.add('diff-range');
    else if (raw.startsWith('+')) line.classList.add('diff-add');
    else if (raw.startsWith('-')) line.classList.add('diff-del');
    line.textContent = raw;
    viewer.appendChild(line);
  });
}

// ── Drift records (real endpoint) ────────────────────────
async function loadDrift() {
  const tbody = document.getElementById('drift-tbody');
  if (!tbody || !state.repoId) return;

  let data;
  try {
    data = await api(`/repositories/${encodeURIComponent(state.repoId)}/drift`);
  } catch {
    return; // keep current contents; error surfaced via trace list
  }

  const drifts = data.drifts || [];
  tbody.innerHTML = '';
  if (!drifts.length) {
    tbody.innerHTML = '<tr><td colspan="3" class="empty-state">No stored drift records for this repository yet.</td></tr>';
    return;
  }
  drifts.forEach(d => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${escapeHtml(String(d.documented_fact || d.fact || '—'))}</td>
      <td>${escapeHtml(String(d.code_reality || d.actual || '—'))}</td>
      <td><span class="${d.status === 'CONFLICT' ? 'badge-conflict' : 'badge-match'}">${escapeHtml(String(d.status || 'MATCH'))}</span></td>
    `;
    tbody.appendChild(tr);
  });
}

// ── Git workflow state panel ─────────────────────────────
function renderGitState(data) {
  const container = document.getElementById('git-state');
  if (!container || !data) return;
  const rows = [
    ['Workflow', data.workflow_id || state.workflowId || '—'],
    ['Plan', data.plan_id || state.lastPlanId || '—'],
    ['State', data.current_state || data.status || '—'],
    ['Branch / PR', data.branch ? `${data.branch}${data.pr_title ? ` · ${data.pr_title}` : ''}` : '—'],
  ];
  container.innerHTML = '';
  const card = document.createElement('div');
  card.className = 'card';
  card.innerHTML = `
    <div class="card-title">Workflow</div>
    ${rows.map(([k, v]) => `<p class="card-desc"><strong>${k}:</strong> ${escapeHtml(String(v))}</p>`).join('')}
  `;
  container.appendChild(card);
}

// ── Observability trace list ─────────────────────────────
function renderTraces() {
  const list = document.getElementById('trace-list');
  if (!list) return;
  if (!state.traces.length) return;

  list.innerHTML = '';
  state.traces.forEach(t => {
    const card = document.createElement('div');
    card.className = 'step-card';
    card.innerHTML = `
      <div class="step-header">
        <span class="step-number">${t.ok ? '✓' : '✗'}</span>
        <span class="step-title">${escapeHtml(t.path)}</span>
      </div>
      <p class="step-desc">${t.elapsedMs} ms${t.traceId ? ` · trace ${escapeHtml(t.traceId)}` : ''}</p>
    `;
    list.appendChild(card);
  });
}

// ── Wire up interactive actions ──────────────────────────
function initActions() {
  const btnQuery = document.getElementById('btn-run-query');
  if (btnQuery) btnQuery.addEventListener('click', runInvestigation);

  const btnPlan = document.getElementById('btn-plan-change');
  if (btnPlan) btnPlan.addEventListener('click', planChange);

  const btnApprove = document.getElementById('btn-approve');
  if (btnApprove) btnApprove.addEventListener('click', approvePlan);

  const btnPatch = document.getElementById('btn-generate-patch');
  if (btnPatch) btnPatch.addEventListener('click', generatePatch);

  const btnRepair = document.getElementById('btn-run-repair');
  if (btnRepair) btnRepair.addEventListener('click', runRepair);

  const searchInput = document.getElementById('search-input');
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') runInvestigation();
    });
  }
}
