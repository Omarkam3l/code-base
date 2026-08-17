// CodeGraph Studio — Interactive Web Client v2 (Cytoscape.js)
// Backend is frozen — only this file + index.html + studio.css changed.

document.addEventListener('DOMContentLoaded', () => {
  registerCyLayouts();
  initTabs();
  initSidebarNav();
  initActions();
  buildLegend();
  loadStatus();
  loadRepositories();
  loadDrift();
  loadEvaluation();
});

// ── Shared client state ───────────────────────────────────────────
const state = {
  repoId: null,
  lastPlanId: null,
  workflowId: null,
  traces: [],
  cy: null,
  cyInitialZoom: null,
  cyInitialPan: null,
  labelsVisible: true,
  currentLayout: 'fcose',
  graphNodes: [],
  graphEdges: [],
};

// ── Node / Edge visual configuration ─────────────────────────────
const KIND_CONFIG = {
  Repository: { color: '#00daf3', shape: 'hexagon',        icon: '⬡' },
  File:       { color: '#8fa7c9', shape: 'roundrectangle', icon: '▧' },
  Module:     { color: '#6b7fa3', shape: 'roundrectangle', icon: '◫' },
  Class:      { color: '#4edea3', shape: 'ellipse',        icon: '◇' },
  Function:   { color: '#ffb95f', shape: 'roundrectangle', icon: 'ƒ' },
  Method:     { color: '#e09040', shape: 'roundrectangle', icon: 'm' },
  Image:      { color: '#b57bee', shape: 'diamond',        icon: '◉' },
  Document:   { color: '#5ec4c4', shape: 'rectangle',      icon: '☰' },
};
const DEFAULT_KIND = { color: '#c3f5ff', shape: 'ellipse', icon: '●' };

const EDGE_COLORS = {
  CALLS:    '#00daf3',
  IMPORTS:  '#ffb95f',
  DEFINES:  '#8fa7c9',
  CONTAINS: '#3b6e8a',
  INHERITS: '#4edea3',
};
const DEFAULT_EDGE_COLOR = '#3b494c';

function kindCfg(kind) {
  return KIND_CONFIG[kind] || DEFAULT_KIND;
}

function truncateLabel(text, max = 14) {
  if (!text) return '';
  return text.length > max ? text.slice(0, max - 1) + '\u2026' : text;
}

// ── Register Cytoscape layouts safely ────────────────────────────
function registerCyLayouts() {
  if (typeof cytoscape === 'undefined') return;
  if (typeof cytoscapeFcose !== 'undefined') {
    try { cytoscape.use(cytoscapeFcose); } catch (_) {}
  }
}

// ── API helper with tracing + error handling ──────────────────────
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

// ── Tab Switching (WAI-ARIA pattern) ──────────────────────────────
function initTabs() {
  const tabs = Array.from(document.querySelectorAll('.tab-button'));
  tabs.forEach((tab, i) => {
    tab.addEventListener('click', () => activateTab(tab, tabs));
    tab.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
        e.preventDefault();
        const dir = e.key === 'ArrowRight' ? 1 : -1;
        const next = tabs[(i + dir + tabs.length) % tabs.length];
        next.focus();
        activateTab(next, tabs);
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        activateTab(tab, tabs);
      }
    });
  });
}

function activateTab(tab, tabs) {
  tabs = tabs || Array.from(document.querySelectorAll('.tab-button'));
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
  if (tab) activateTab(tab);
}

// ── Sidebar Navigation ─────────────────────────────────────────────
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
      if (item.dataset.tab) switchToTab(item.dataset.tab);
    });
  });
}

// ── Toast Notifications ────────────────────────────────────────────
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
  void toast.offsetWidth;
  toast.classList.add('visible');
  clearTimeout(toast._timeout);
  toast._timeout = setTimeout(() => toast.classList.remove('visible'), 3000);
}

// ── Health + Evaluation header badges ─────────────────────────────
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
    quality.textContent = `Eval: ${evalData.status} (${evalData.benchmark_cases} cases)`;
    quality.classList.toggle('success', evalData.quality_gate === true);
    const recall = evalData.metrics && evalData.metrics.retrieval_recall_at_5;
    document.getElementById('hdr-conf').textContent = recall ? `Recall@5: ${recall}` : 'Recall@5: \u2014';
    document.getElementById('stat-eval-cases').textContent = `${evalData.benchmark_cases} eval cases`;
  } catch {
    document.getElementById('hdr-quality').textContent = 'Eval: unavailable';
  }
}

// ── Repository custom selector ─────────────────────────────────────
async function loadRepositories() {
  let repos = [];
  try {
    repos = await api('/repositories');
  } catch {
    showToast('Could not load repositories \u2014 is the API running?', 'error');
    return;
  }
  document.getElementById('stat-repos').textContent = `repositories: ${repos.length}`;
  populateRepoSelector(repos);
}

function populateRepoSelector(repos) {
  const btn = document.getElementById('repo-selector-btn');
  const dropdown = document.getElementById('repo-dropdown');
  if (!btn || !dropdown) return;

  dropdown.innerHTML = '';

  if (!repos.length) {
    const empty = document.createElement('div');
    empty.className = 'repo-dropdown-empty';
    empty.textContent = 'No repositories registered.';
    dropdown.appendChild(empty);
    return;
  }

  repos.forEach(r => {
    const item = document.createElement('div');
    item.className = 'repo-dropdown-item';
    item.setAttribute('role', 'option');
    item.setAttribute('tabindex', '0');
    item.dataset.repoId = r.repository_id;
    const statusClass = r.status === 'INDEXED' ? 'status-indexed'
                      : r.status === 'INDEXING' ? 'status-indexing' : 'status-unknown';
    item.innerHTML = `
      <span class="repo-item-name">${escapeHtml(r.name || r.repository_id)}</span>
      <span class="repo-status-badge ${statusClass}">${escapeHtml(r.status || '?')}</span>
    `;
    item.addEventListener('click', () => selectRepo(r));
    item.addEventListener('keydown', e => {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectRepo(r); }
    });
    dropdown.appendChild(item);
  });

  btn.addEventListener('click', toggleRepoDropdown);
  btn.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggleRepoDropdown(); }
    if (e.key === 'Escape') closeRepoDropdown();
  });
  document.addEventListener('click', e => {
    if (!btn.contains(e.target) && !dropdown.contains(e.target)) closeRepoDropdown();
  });

  if (repos.length > 0) selectRepo(repos[0]);
}

function toggleRepoDropdown() {
  const btn = document.getElementById('repo-selector-btn');
  const dropdown = document.getElementById('repo-dropdown');
  const isOpen = !dropdown.hidden;
  dropdown.hidden = isOpen;
  btn.setAttribute('aria-expanded', String(!isOpen));
}

function closeRepoDropdown() {
  const dropdown = document.getElementById('repo-dropdown');
  const btn = document.getElementById('repo-selector-btn');
  if (dropdown) dropdown.hidden = true;
  if (btn) btn.setAttribute('aria-expanded', 'false');
}

function selectRepo(r) {
  state.repoId = r.repository_id;
  closeRepoDropdown();
  const label = document.getElementById('repo-selector-label');
  const statusBadge = document.getElementById('repo-selector-status');
  if (label) label.textContent = r.name || r.repository_id;
  if (statusBadge) {
    const statusClass = r.status === 'INDEXED' ? 'status-indexed'
                      : r.status === 'INDEXING' ? 'status-indexing' : 'status-unknown';
    statusBadge.className = `repo-status-badge ${statusClass}`;
    statusBadge.textContent = r.status || '';
  }
  document.querySelectorAll('.repo-dropdown-item').forEach(el => {
    el.classList.toggle('active', el.dataset.repoId === r.repository_id);
    el.setAttribute('aria-selected', String(el.dataset.repoId === r.repository_id));
  });
  loadGraph();
  loadDrift();
}

// ── Graph Loading / Empty state helpers ───────────────────────────
function showGraphLoading(visible) {
  const el = document.getElementById('graph-loading');
  if (el) el.hidden = !visible;
}

function showGraphEmpty(visible, message) {
  const el = document.getElementById('graph-empty-state');
  const msg = document.getElementById('graph-empty-message');
  if (el) el.hidden = !visible;
  if (msg && message) msg.textContent = message;
}

function hideGraphOverlays() {
  showGraphLoading(false);
  showGraphEmpty(false, '');
}

// ── Graph: load + render with Cytoscape.js ────────────────────────
async function loadGraph() {
  if (!state.repoId) return;

  if (state.cy) {
    state.cy.destroy();
    state.cy = null;
  }
  hideGraphOverlays();
  showGraphLoading(true);

  let data;
  try {
    data = await api(`/repositories/${encodeURIComponent(state.repoId)}/graph?limit=40`);
  } catch (err) {
    showGraphLoading(false);
    showGraphEmpty(true, `Graph load failed: ${err.message}`);
    showToast(`Graph load failed: ${err.message}`, 'error');
    return;
  }

  showGraphLoading(false);
  const nodes = data.nodes || [];
  const edges = data.edges || [];
  state.graphNodes = nodes;
  state.graphEdges = edges;

  const statsEl = document.getElementById('graph-stats');
  if (statsEl) statsEl.textContent = nodes.length ? `${nodes.length} nodes \u00b7 ${edges.length} edges` : 'no data';

  if (!nodes.length) {
    showGraphEmpty(true, data.note || 'No indexed entities in the graph for this repository. Index a repository with a live graph connection first.');
    const btnIndex = document.getElementById('btn-index-repo');
    if (btnIndex) btnIndex.onclick = triggerReindex;
    return;
  }

  renderGraphCytoscape(nodes, edges);
}

function renderGraphCytoscape(nodes, edges) {
  if (typeof cytoscape === 'undefined') {
    showGraphEmpty(true, 'Cytoscape.js failed to load from CDN. Check your network connection.');
    return;
  }

  const container = document.getElementById('cy-container');
  if (!container) return;

  const elements = [];

  nodes.forEach(n => {
    const cfg = kindCfg(n.kind);
    const label = cfg.icon + ' ' + truncateLabel(n.name || n.id, 14);
    elements.push({
      group: 'nodes',
      data: {
        id: String(n.id),
        label,
        fullLabel: n.name || n.id,
        qualifiedName: n.qualified_name || n.name || n.id,
        kind: n.kind || 'Unknown',
        filePath: n.file_path || '',
        color: cfg.color,
        shape: cfg.shape,
        icon: cfg.icon,
      }
    });
  });

  edges.forEach((e, i) => {
    const src = String(e.source);
    const tgt = String(e.target);
    const srcExists = nodes.some(n => String(n.id) === src);
    const tgtExists = nodes.some(n => String(n.id) === tgt);
    if (!srcExists || !tgtExists) return;
    elements.push({
      group: 'edges',
      data: {
        id: `e_${i}_${src}_${tgt}`,
        source: src,
        target: tgt,
        type: e.type || 'RELATES',
        color: EDGE_COLORS[e.type] || DEFAULT_EDGE_COLOR,
        label: e.type || '',
      }
    });
  });

  const showEdgeLabels = edges.length < 20;
  const fcoseAvailable = typeof cytoscapeFcose !== 'undefined';
  const useLayout = (state.currentLayout === 'fcose' && !fcoseAvailable) ? 'cose' : state.currentLayout;

  const cy = cytoscape({
    container,
    elements,
    style: buildCytoscapeStyle(showEdgeLabels),
    layout: buildLayoutConfig(useLayout),
    minZoom: 0.1,
    maxZoom: 5,
    wheelSensitivity: 0.3,
  });

  state.cy = cy;

  cy.ready(() => {
    cy.fit(undefined, 40);
    state.cyInitialZoom = cy.zoom();
    state.cyInitialPan = { ...cy.pan() };
    renderMinimap();
    const minimap = document.getElementById('graph-minimap');
    if (minimap) minimap.hidden = false;
    cy.on('render', () => renderMinimap());
  });

  cy.on('tap', 'node', function(evt) {
    highlightNeighbors(evt.target);
    openNodeDetailsPanel(evt.target.data());
  });

  cy.on('tap', 'edge', function(evt) {
    const edge = evt.target;
    showToast(`Edge: ${edge.data('type')} (${edge.data('source')} \u2192 ${edge.data('target')})`, 'info');
  });

  cy.on('tap', function(evt) {
    if (evt.target === cy) {
      resetHighlight();
      closeNodeDetailsPanel();
    }
  });

  initGraphFilters();
  initGraphSearch();
  buildLegend();

  const btnIndex = document.getElementById('btn-index-repo');
  if (btnIndex) btnIndex.onclick = triggerReindex;
}

function buildLayoutConfig(name) {
  const base = { name, animate: true, animationDuration: 600 };
  if (name === 'fcose') {
    return { ...base, quality: 'default', randomize: true, nodeRepulsion: 4500, idealEdgeLength: 120, edgeElasticity: 0.45, numIter: 2500, tile: true };
  }
  if (name === 'cose') {
    return { ...base, nodeRepulsion: 400000, idealEdgeLength: 120, edgeElasticity: 0.45, gravity: 80, numIter: 1000, initialTemp: 200 };
  }
  if (name === 'breadthfirst') {
    return { ...base, directed: true, spacingFactor: 1.5 };
  }
  if (name === 'concentric') {
    return { ...base, concentric: n => n.degree(), levelWidth: () => 2, spacingFactor: 1.8 };
  }
  return base;
}

function buildCytoscapeStyle(showEdgeLabels) {
  return [
    {
      selector: 'node',
      style: {
        'shape': 'data(shape)',
        'background-color': 'data(color)',
        'background-opacity': 0.15,
        'border-color': 'data(color)',
        'border-width': 2,
        'label': 'data(label)',
        'color': '#dae2fd',
        'font-family': "'JetBrains Mono', monospace",
        'font-size': 11,
        'font-weight': 500,
        'text-valign': 'bottom',
        'text-halign': 'center',
        'text-margin-y': 4,
        'text-outline-color': '#0b1326',
        'text-outline-width': 2,
        'width': 40,
        'height': 40,
        'min-zoomed-font-size': 8,
        'overlay-padding': 6,
        'z-index': 10,
        'transition-property': 'background-opacity, border-width',
        'transition-duration': '0.15s',
      }
    },
    {
      selector: 'node:selected',
      style: { 'border-width': 3, 'border-color': '#ffffff', 'background-opacity': 0.4, 'z-index': 20 }
    },
    {
      selector: 'node.highlighted',
      style: { 'border-width': 3, 'background-opacity': 0.45, 'z-index': 20 }
    },
    {
      selector: 'node.dimmed',
      style: { 'opacity': 0.18 }
    },
    {
      selector: 'node.search-match',
      style: { 'border-color': '#ffffff', 'border-width': 3, 'background-opacity': 0.5, 'z-index': 30 }
    },
    {
      selector: 'edge',
      style: {
        'width': 1.5,
        'line-color': 'data(color)',
        'target-arrow-color': 'data(color)',
        'target-arrow-shape': 'triangle',
        'arrow-scale': 0.9,
        'curve-style': 'bezier',
        'opacity': 0.7,
        'label': showEdgeLabels ? 'data(label)' : '',
        'color': '#849396',
        'font-family': "'JetBrains Mono', monospace",
        'font-size': 9,
        'text-rotation': 'autorotate',
        'text-outline-color': '#0b1326',
        'text-outline-width': 1.5,
        'min-zoomed-font-size': 8,
        'transition-property': 'opacity, width',
        'transition-duration': '0.15s',
      }
    },
    {
      selector: 'edge:selected',
      style: { 'width': 3, 'opacity': 1, 'label': 'data(label)', 'z-index': 20 }
    },
    {
      selector: 'edge.highlighted',
      style: { 'width': 2.5, 'opacity': 1, 'label': 'data(label)', 'z-index': 15 }
    },
    {
      selector: 'edge.dimmed',
      style: { 'opacity': 0.06 }
    },
  ];
}

// ── Neighbor highlighting ──────────────────────────────────────────
function highlightNeighbors(node) {
  if (!state.cy) return;
  const cy = state.cy;
  cy.elements().addClass('dimmed').removeClass('highlighted');
  const neighborhood = node.closedNeighborhood();
  neighborhood.removeClass('dimmed').addClass('highlighted');
  neighborhood.connectedEdges().removeClass('dimmed').addClass('highlighted');
  node.removeClass('dimmed').addClass('highlighted');
}

function resetHighlight() {
  if (!state.cy) return;
  state.cy.elements().removeClass('dimmed').removeClass('highlighted').removeClass('search-match');
}

// ── Node Details Panel ─────────────────────────────────────────────
function openNodeDetailsPanel(data) {
  const panel = document.getElementById('node-details-panel');
  if (!panel) return;

  const cfg = kindCfg(data.kind);
  const iconEl = document.getElementById('nd-icon');
  if (iconEl) { iconEl.textContent = cfg.icon; iconEl.style.color = cfg.color; }
  const nameEl = document.getElementById('nd-name');
  if (nameEl) nameEl.textContent = data.fullLabel || data.id;
  const kindEl = document.getElementById('nd-kind');
  if (kindEl) kindEl.textContent = data.kind || 'Unknown';

  const meta = document.getElementById('nd-meta');
  if (meta) {
    meta.innerHTML = '';
    if (data.filePath) {
      const row = document.createElement('div');
      row.className = 'nd-meta-row';
      row.innerHTML = `<span class="nd-meta-key">File</span><span class="nd-meta-val nd-monospace">${escapeHtml(data.filePath)}</span>`;
      meta.appendChild(row);
    }
    if (data.qualifiedName && data.qualifiedName !== data.fullLabel) {
      const row = document.createElement('div');
      row.className = 'nd-meta-row';
      row.innerHTML = `<span class="nd-meta-key">Qualified</span><span class="nd-meta-val nd-monospace">${escapeHtml(data.qualifiedName)}</span>`;
      meta.appendChild(row);
    }
    if (state.cy) {
      const cyNode = state.cy.getElementById(data.id);
      const inEdges = cyNode.incomers('edge');
      const outEdges = cyNode.outgoers('edge');
      if (inEdges.length || outEdges.length) {
        const row = document.createElement('div');
        row.className = 'nd-meta-row';
        row.innerHTML = `<span class="nd-meta-key">Connections</span><span class="nd-meta-val">${inEdges.length} in \u00b7 ${outEdges.length} out</span>`;
        meta.appendChild(row);
      }
    }
  }

  panel.hidden = false;

  const btnInv = document.getElementById('nd-btn-investigate');
  if (btnInv) {
    btnInv.onclick = () => {
      const input = document.getElementById('search-input');
      if (input) input.value = `Explain ${data.qualifiedName || data.fullLabel}`;
      switchToTab('tab-investigation');
      runInvestigation();
    };
  }

  const btnTrace = document.getElementById('nd-btn-trace');
  if (btnTrace) {
    btnTrace.onclick = () => showToast(`Tracing calls for ${data.fullLabel}\u2026`, 'info');
  }

  const btnImpact = document.getElementById('nd-btn-impact');
  if (btnImpact) {
    btnImpact.onclick = () => showToast(`Analyzing impact for ${data.fullLabel}\u2026`, 'info');
  }
}

function closeNodeDetailsPanel() {
  const panel = document.getElementById('node-details-panel');
  if (panel) panel.hidden = true;
}

// ── Graph Toolbar controls ─────────────────────────────────────────
function initGraphToolbar() {
  const btnZoomIn = document.getElementById('btn-zoom-in');
  if (btnZoomIn) btnZoomIn.addEventListener('click', () => {
    if (state.cy) state.cy.zoom({ level: state.cy.zoom() * 1.3, renderedPosition: { x: state.cy.width() / 2, y: state.cy.height() / 2 } });
  });

  const btnZoomOut = document.getElementById('btn-zoom-out');
  if (btnZoomOut) btnZoomOut.addEventListener('click', () => {
    if (state.cy) state.cy.zoom({ level: state.cy.zoom() / 1.3, renderedPosition: { x: state.cy.width() / 2, y: state.cy.height() / 2 } });
  });

  const btnFit = document.getElementById('btn-fit');
  if (btnFit) btnFit.addEventListener('click', () => {
    if (state.cy) state.cy.fit(undefined, 40);
  });

  const btnReset = document.getElementById('btn-reset');
  if (btnReset) btnReset.addEventListener('click', () => {
    if (state.cy && state.cyInitialZoom !== null) {
      state.cy.zoom(state.cyInitialZoom);
      state.cy.pan(state.cyInitialPan);
    }
  });

  const btnLabels = document.getElementById('btn-labels-toggle');
  if (btnLabels) btnLabels.addEventListener('click', () => {
    if (!state.cy) return;
    state.labelsVisible = !state.labelsVisible;
    btnLabels.setAttribute('aria-pressed', String(state.labelsVisible));
    btnLabels.classList.toggle('active', state.labelsVisible);
    state.cy.style().selector('node').style('label', state.labelsVisible ? 'data(label)' : '').update();
  });

  const layoutSel = document.getElementById('layout-selector');
  if (layoutSel) layoutSel.addEventListener('change', () => {
    state.currentLayout = layoutSel.value;
    if (state.cy) {
      const fcoseAvailable = typeof cytoscapeFcose !== 'undefined';
      const useLayout = (state.currentLayout === 'fcose' && !fcoseAvailable) ? 'cose' : state.currentLayout;
      state.cy.layout(buildLayoutConfig(useLayout)).run();
    }
  });

  const filterToggle = document.getElementById('filter-panel-toggle');
  const filterBody = document.getElementById('filter-panel-body');
  if (filterToggle && filterBody) {
    filterToggle.addEventListener('click', () => {
      const expanded = filterBody.hidden;
      filterBody.hidden = !expanded;
      filterToggle.setAttribute('aria-expanded', String(expanded));
    });
  }

  const ndClose = document.getElementById('node-details-close');
  if (ndClose) ndClose.addEventListener('click', closeNodeDetailsPanel);
}

// ── Graph Filters ──────────────────────────────────────────────────
function initGraphFilters() {
  document.querySelectorAll('.node-type-filter').forEach(cb => {
    cb.addEventListener('change', applyGraphFilters);
  });
  document.querySelectorAll('.edge-type-filter').forEach(cb => {
    cb.addEventListener('change', applyGraphFilters);
  });
}

function applyGraphFilters() {
  if (!state.cy) return;
  const enabledNodeTypes = new Set(
    Array.from(document.querySelectorAll('.node-type-filter:checked')).map(c => c.value)
  );
  const enabledEdgeTypes = new Set(
    Array.from(document.querySelectorAll('.edge-type-filter:checked')).map(c => c.value)
  );

  state.cy.nodes().forEach(n => {
    const kind = n.data('kind') || 'Unknown';
    n.style('display', enabledNodeTypes.has(kind) ? 'element' : 'none');
  });

  state.cy.edges().forEach(e => {
    const type = e.data('type') || '';
    const srcVisible = e.source().style('display') !== 'none';
    const tgtVisible = e.target().style('display') !== 'none';
    e.style('display', (enabledEdgeTypes.has(type) && srcVisible && tgtVisible) ? 'element' : 'none');
  });
}

// ── Graph Search ───────────────────────────────────────────────────
function initGraphSearch() {
  const input = document.getElementById('graph-search');
  if (!input) return;

  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    if (!state.cy) return;
    state.cy.elements().removeClass('search-match').removeClass('dimmed');
    if (!q) return;

    const matches = state.cy.nodes().filter(n => {
      return (n.data('fullLabel') || '').toLowerCase().includes(q) ||
             (n.data('qualifiedName') || '').toLowerCase().includes(q) ||
             (n.data('kind') || '').toLowerCase().includes(q);
    });

    if (matches.length) {
      state.cy.nodes().addClass('dimmed');
      state.cy.edges().addClass('dimmed');
      matches.removeClass('dimmed').addClass('search-match');
      state.cy.animate({ fit: { eles: matches.first(), padding: 80 }, duration: 400 });
    }
  });

  input.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      input.value = '';
      if (state.cy) state.cy.elements().removeClass('search-match').removeClass('dimmed');
    }
  });
}

// ── Minimap ────────────────────────────────────────────────────────
function renderMinimap() {
  if (!state.cy) return;
  const canvas = document.getElementById('minimap-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const W = canvas.width;
  const H = canvas.height;

  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = 'rgba(11,19,38,0.9)';
  ctx.fillRect(0, 0, W, H);

  const bb = state.cy.elements(':visible').boundingBox();
  if (!bb || bb.w === 0 || bb.h === 0) return;

  const scaleX = (W - 12) / bb.w;
  const scaleY = (H - 12) / bb.h;
  const scale = Math.min(scaleX, scaleY);
  const offsetX = 6 + (W - 12 - bb.w * scale) / 2;
  const offsetY = 6 + (H - 12 - bb.h * scale) / 2;

  state.cy.edges(':visible').forEach(e => {
    const sp = e.source().position();
    const tp = e.target().position();
    ctx.beginPath();
    ctx.moveTo(offsetX + (sp.x - bb.x1) * scale, offsetY + (sp.y - bb.y1) * scale);
    ctx.lineTo(offsetX + (tp.x - bb.x1) * scale, offsetY + (tp.y - bb.y1) * scale);
    ctx.strokeStyle = 'rgba(100,120,160,0.4)';
    ctx.lineWidth = 0.8;
    ctx.stroke();
  });

  state.cy.nodes(':visible').forEach(n => {
    const pos = n.position();
    const mx = offsetX + (pos.x - bb.x1) * scale;
    const my = offsetY + (pos.y - bb.y1) * scale;
    ctx.beginPath();
    ctx.arc(mx, my, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = n.data('color') || '#c3f5ff';
    ctx.fill();
  });

  const pan = state.cy.pan();
  const zoom = state.cy.zoom();
  const vw = state.cy.width() / zoom;
  const vh = state.cy.height() / zoom;
  const vpx = -pan.x / zoom;
  const vpy = -pan.y / zoom;
  const rx = offsetX + (vpx - bb.x1) * scale;
  const ry = offsetY + (vpy - bb.y1) * scale;
  ctx.strokeStyle = 'rgba(0,218,243,0.6)';
  ctx.lineWidth = 1;
  ctx.strokeRect(rx, ry, vw * scale, vh * scale);
}

// ── Legend ─────────────────────────────────────────────────────────
function buildLegend() {
  const legend = document.getElementById('graph-legend');
  const body = document.getElementById('legend-body');
  const toggle = document.getElementById('legend-toggle');
  if (!legend || !body || !toggle) return;

  body.innerHTML = '';
  Object.entries(KIND_CONFIG).forEach(([kind, cfg]) => {
    body.appendChild(legendRow(kind, cfg.color, 'node'));
  });
  Object.entries(EDGE_COLORS).forEach(([type, color]) => {
    body.appendChild(legendRow(type, color, 'edge'));
  });

  toggle.onclick = () => {
    const collapsed = legend.classList.toggle('collapsed');
    toggle.setAttribute('aria-expanded', String(!collapsed));
  };
}

function legendRow(name, color, variant) {
  const row = document.createElement('div');
  row.className = 'legend-row';
  const swatch = document.createElement('span');
  swatch.className = `legend-swatch${variant === 'edge' ? ' edge' : ''}`;
  swatch.style.background = color;
  const label = document.createElement('span');
  label.textContent = name;
  row.appendChild(swatch);
  row.appendChild(label);
  return row;
}

// ── Trigger re-index ───────────────────────────────────────────────
async function triggerReindex() {
  if (!state.repoId) return;
  showToast('Re-indexing repository\u2026', 'info');
  try {
    await api(`/repositories/${encodeURIComponent(state.repoId)}/index`, { method: 'POST' });
    showToast('Re-index triggered.', 'success');
    setTimeout(() => loadGraph(), 2000);
  } catch (err) {
    showToast(`Re-index failed: ${err.message}`, 'error');
  }
}

// ── Agentic Investigation ──────────────────────────────────────────
async function runInvestigation() {
  const input = document.getElementById('search-input');
  const btn = document.getElementById('btn-run-query');
  const question = input ? input.value.trim() : '';

  if (!question) { showToast('Please enter a question first.', 'info'); return; }
  if (!state.repoId) { showToast('Select a repository first.', 'info'); return; }

  btn.disabled = true;
  btn.textContent = 'Investigating\u2026';

  const emptyEl = document.getElementById('investigation-empty');
  if (emptyEl) emptyEl.hidden = true;

  const statusEl = document.getElementById('investigation-status');
  const statusDot = document.getElementById('inv-status-dot');
  const statusText = document.getElementById('inv-status-text');
  if (statusEl) statusEl.hidden = false;
  if (statusDot) statusDot.className = 'inv-status-dot inv-active';
  if (statusText) statusText.textContent = 'Investigating\u2026';

  ['investigation-evidence', 'investigation-answer'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.hidden = true;
  });

  try {
    const data = await api('/investigate', {
      method: 'POST',
      body: JSON.stringify({ question, repository_id: state.repoId }),
    });
    renderInvestigation(data);
    if (statusDot) statusDot.className = 'inv-status-dot inv-complete';
    if (statusText) statusText.textContent = '\u2713 Complete';
    showToast('Investigation complete.', 'success');
  } catch (err) {
    if (statusDot) statusDot.className = 'inv-status-dot inv-error';
    if (statusText) statusText.textContent = `Failed: ${err.message}`;
    if (emptyEl) {
      emptyEl.hidden = false;
      const desc = emptyEl.querySelector('.card-desc');
      if (desc) desc.textContent = `Investigation failed: ${err.message}`;
    }
    showToast(`Investigation failed: ${err.message}`, 'error');
  } finally {
    btn.disabled = false;
    btn.textContent = 'Investigate';
  }
}

function renderInvestigation(data) {
  const answerEl = document.getElementById('investigation-answer');
  const answerText = document.getElementById('investigation-answer-text');
  const metaEl = document.getElementById('investigation-meta');
  if (answerEl) answerEl.hidden = false;
  if (answerText) answerText.textContent = data.final_answer || 'No answer produced.';
  if (metaEl) {
    metaEl.innerHTML = '';
    if (data.trace_id) {
      const b = document.createElement('span');
      b.className = 'evidence-badge';
      b.textContent = `trace ${data.trace_id}`;
      metaEl.appendChild(b);
    }
    if (data.investigation_id) {
      const b = document.createElement('span');
      b.className = 'evidence-badge';
      b.textContent = `investigation ${data.investigation_id}`;
      metaEl.appendChild(b);
    }
  }

  const citations = data.citations || [];
  const evidenceEl = document.getElementById('investigation-evidence');
  const evidenceItems = document.getElementById('investigation-evidence-items');
  if (evidenceEl && evidenceItems) {
    if (citations.length) {
      evidenceEl.hidden = false;
      evidenceItems.innerHTML = '';
      citations.forEach((c, i) => {
        const badge = document.createElement('span');
        badge.className = 'evidence-badge';
        badge.textContent = `[E${i + 1}] ${String(c)}`;
        badge.title = `Click to highlight in graph: ${String(c)}`;
        badge.setAttribute('role', 'button');
        badge.setAttribute('tabindex', '0');
        badge.addEventListener('click', () => highlightGraphNodeByPath(String(c)));
        badge.addEventListener('keydown', e => { if (e.key === 'Enter') highlightGraphNodeByPath(String(c)); });
        evidenceItems.appendChild(badge);
      });
    } else {
      evidenceEl.hidden = true;
    }
  }
}

function highlightGraphNodeByPath(pathHint) {
  if (!state.cy) return;
  const lower = pathHint.toLowerCase();
  const match = state.cy.nodes().filter(n => {
    return (n.data('filePath') || '').toLowerCase().includes(lower) ||
           (n.data('fullLabel') || '').toLowerCase().includes(lower) ||
           (n.data('qualifiedName') || '').toLowerCase().includes(lower);
  });
  if (match.length) {
    resetHighlight();
    match.addClass('search-match');
    state.cy.animate({ fit: { eles: match.first(), padding: 100 }, duration: 500 });
  }
}

// ── Change Plan → Approve → Patch ─────────────────────────────────
async function planChange() {
  const input = document.getElementById('change-request-input');
  const btnApprove = document.getElementById('btn-approve');
  const patchBtn = document.getElementById('btn-generate-patch');
  const request = input ? input.value.trim() : '';

  if (!request) { showToast('Describe the change you want first.', 'info'); return; }
  if (!state.repoId) { showToast('Select a repository first.', 'info'); return; }

  try {
    const data = await api('/changes/plan', {
      method: 'POST',
      body: JSON.stringify({ change_request: request, repository_id: state.repoId }),
    });
    state.lastPlanId = data.plan_id;
    state.workflowId = data.workflow_id;
    renderGitState(data);
    renderDiff(null, data.is_valid
      ? `Plan ${data.plan_id} ready \u2014 targets: ${(data.target_files || []).join(', ') || 'none'}. Approve to enable patch generation.`
      : `Plan rejected: ${data.rejection_reason || 'unknown reason'}`);

    const planInfo = document.getElementById('patch-plan-info');
    const planDetails = document.getElementById('patch-plan-details');
    if (planInfo && planDetails) {
      planInfo.hidden = false;
      planDetails.innerHTML = `
        <div class="nd-meta-row"><span class="nd-meta-key">Plan ID</span><span class="nd-meta-val nd-monospace">${escapeHtml(String(data.plan_id || '\u2014'))}</span></div>
        <div class="nd-meta-row"><span class="nd-meta-key">Valid</span><span class="nd-meta-val">${data.is_valid ? '\u2713 Yes' : '\u2717 No'}</span></div>
        <div class="nd-meta-row"><span class="nd-meta-key">Files</span><span class="nd-meta-val nd-monospace">${escapeHtml((data.target_files || []).join(', ') || 'none')}</span></div>
        ${data.rejection_reason ? `<div class="nd-meta-row"><span class="nd-meta-key">Rejected</span><span class="nd-meta-val">${escapeHtml(data.rejection_reason)}</span></div>` : ''}
      `;
    }

    const riskRow = document.getElementById('patch-risk-row');
    const riskBadge = document.getElementById('patch-risk-badge');
    if (riskRow && riskBadge) {
      const risk = data.risk_level || (data.is_valid ? 'LOW' : 'HIGH');
      riskRow.hidden = false;
      riskBadge.textContent = risk;
      riskBadge.className = 'risk-badge risk-' + risk.toLowerCase();
    }

    if (btnApprove) btnApprove.disabled = !data.is_valid;
    if (patchBtn) patchBtn.disabled = true;
    const actionRow = document.getElementById('patch-action-row');
    if (actionRow && data.is_valid) actionRow.style.display = 'flex';

    showToast(data.is_valid ? 'Change plan created \u2014 awaiting approval.' : 'Plan rejected by safety validation.', data.is_valid ? 'success' : 'error');
  } catch (err) {
    showToast(`Planning failed: ${err.message}`, 'error');
  }
}

async function approvePlan() {
  const btn = document.getElementById('btn-approve');
  const btnApproveProminent = document.getElementById('btn-approve-prominent');
  const patchBtn = document.getElementById('btn-generate-patch');
  if (!state.lastPlanId) return;

  try {
    const data = await api(`/changes/${encodeURIComponent(state.lastPlanId)}/approve`, { method: 'POST' });
    if (btn) { btn.textContent = '\u2713 Plan Approved'; btn.disabled = true; }
    if (btnApproveProminent) { btnApproveProminent.textContent = '\u2713 Approved'; btnApproveProminent.disabled = true; }
    if (patchBtn) patchBtn.disabled = false;
    renderGitState(data);
    showToast('Human approval granted \u2014 patch generation enabled.', 'success');
  } catch (err) {
    showToast(`Approval failed: ${err.message}`, 'error');
  }
}

async function generatePatch() {
  if (!state.lastPlanId) return;
  const patchBtn = document.getElementById('btn-generate-patch');
  if (patchBtn) { patchBtn.disabled = true; patchBtn.textContent = 'Generating\u2026'; }

  try {
    const data = await api('/changes/patch', {
      method: 'POST',
      body: JSON.stringify({ plan_id: state.lastPlanId, run_tests: true }),
    });
    renderDiff(data.patch, null);
    renderGitState(data);

    const testMetrics = document.getElementById('patch-test-metrics');
    if (testMetrics) {
      if (data.validation_failures && data.validation_failures.length) {
        testMetrics.innerHTML = `<span style="color:var(--crimson);">\u2717 Tests Failed: ${escapeHtml(data.validation_failures.join(', '))}</span>`;
      } else {
        testMetrics.innerHTML = `<span style="color:var(--secondary);">\u2713 Tests Verified PASSED</span>`;
      }
    }

    const btnApproveGit = document.getElementById('btn-approve-git');
    if (btnApproveGit) btnApproveGit.disabled = false;

    showToast(`Patch ${data.status} \u2014 see diff below.`, data.status === 'VALIDATED' ? 'success' : 'info');
  } catch (err) {
    showToast(`Patch generation failed: ${err.message}`, 'error');
  } finally {
    if (patchBtn) { patchBtn.disabled = false; patchBtn.textContent = 'Generate Patch'; }
  }
}

async function runRepair() {
  const input = document.getElementById('change-request-input');
  const failure = input && input.value.trim();
  if (!failure) { showToast('Enter the failure description in the change request field first.', 'info'); return; }
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

async function runDedicatedRepair() {
  const input = document.getElementById('repair-traceback-input');
  const failure = input && input.value.trim();
  if (!failure) { showToast('Paste failure traceback or error message first.', 'info'); return; }
  if (!state.repoId) return;

  const btn = document.getElementById('btn-execute-repair-dedicated');
  if (btn) { btn.disabled = true; btn.textContent = 'Repairing\u2026'; }

  try {
    const data = await api('/repairs', {
      method: 'POST',
      body: JSON.stringify({ failure_message: failure, repository_id: state.repoId }),
    });
    renderDiff(data.final_patch, `Repair ${data.repair_status} after ${data.iterations} iteration(s). Stopping reason: ${data.stopping_reason || 'N/A'}`);
    showToast(`Repair ${data.repair_status}.`, data.repair_status === 'REPAIRED' ? 'success' : 'info');
  } catch (err) {
    showToast(`Repair failed: ${err.message}`, 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = 'Run Repair Loop'; }
  }
}

async function approveGitCommit() {
  if (!state.lastPlanId) return;
  const btnApproveGit = document.getElementById('btn-approve-git');
  const btnExecuteGit = document.getElementById('btn-execute-git-pr');
  if (btnApproveGit) { btnApproveGit.disabled = true; btnApproveGit.textContent = 'Approving\u2026'; }

  try {
    const data = await api(`/changes/${encodeURIComponent(state.lastPlanId)}/approve-git`, { method: 'POST' });
    if (btnApproveGit) { btnApproveGit.textContent = '\u2713 Git Approved'; btnApproveGit.disabled = true; }
    if (btnExecuteGit) btnExecuteGit.disabled = false;
    renderGitState(data);
    showToast('Git commit approved.', 'success');
  } catch (err) {
    showToast(`Git approval failed: ${err.message}`, 'error');
    if (btnApproveGit) { btnApproveGit.disabled = false; btnApproveGit.textContent = 'Approve Git Commit'; }
  }
}

async function executeGitCommit() {
  if (!state.lastPlanId) return;
  const btnExecuteGit = document.getElementById('btn-execute-git-pr');
  const chkPush = document.getElementById('chk-request-push');
  if (btnExecuteGit) { btnExecuteGit.disabled = true; btnExecuteGit.textContent = 'Executing\u2026'; }

  try {
    const data = await api('/changes/commit', {
      method: 'POST',
      body: JSON.stringify({ plan_id: state.lastPlanId, request_push: Boolean(chkPush && chkPush.checked) }),
    });
    renderGitState(data);
    showToast(`Git & PR workflow ${data.status} \u2014 commit: ${data.commit || 'created'}.`, 'success');
  } catch (err) {
    showToast(`Git commit execution failed: ${err.message}`, 'error');
    if (btnExecuteGit) { btnExecuteGit.disabled = false; btnExecuteGit.textContent = 'Create Commit & PR'; }
  }
}

function renderDiff(diffText, message) {
  const viewer = document.getElementById('diff-viewer');
  if (!viewer) return;
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

// ── Drift Inspector (card-based) ───────────────────────────────────
async function loadDrift() {
  const container = document.getElementById('drift-cards-container');
  if (!container || !state.repoId) return;

  let data;
  try {
    data = await api(`/repositories/${encodeURIComponent(state.repoId)}/drift`);
  } catch {
    return;
  }

  const drifts = data.drifts || [];
  container.innerHTML = '';

  if (!drifts.length) {
    container.innerHTML = '<div class="card empty-state"><p class="card-desc">No stored drift records for this repository yet.</p></div>';
    return;
  }

  drifts.forEach(d => {
    const status = String(d.status || 'UNKNOWN').toUpperCase();
    const severityClass = {
      'MATCH': 'severity-match',
      'CONFLICT': 'severity-conflict',
      'MISSING IN CODE': 'severity-missing',
      'MISSING IN DOCS': 'severity-missing',
      'MISSING_IN_CODE': 'severity-missing',
      'MISSING_IN_DOCS': 'severity-missing',
      'UNRESOLVED': 'severity-unresolved',
    }[status] || 'severity-unresolved';

    const card = document.createElement('div');
    card.className = `drift-card ${severityClass}`;
    card.setAttribute('role', 'button');
    card.setAttribute('tabindex', '0');
    card.innerHTML = `
      <div class="drift-card-header">
        <span class="drift-severity-badge ${severityClass}">${escapeHtml(status)}</span>
      </div>
      <div class="drift-card-body">
        <div class="drift-card-fact">${escapeHtml(String(d.documented_fact || d.fact || '\u2014'))}</div>
        <div class="drift-card-arrow">\u2192</div>
        <div class="drift-card-reality">${escapeHtml(String(d.code_reality || d.actual || '\u2014'))}</div>
      </div>
    `;
    const handler = () => {
      const hint = d.documented_fact || d.fact || '';
      if (hint) highlightGraphNodeByPath(String(hint));
    };
    card.addEventListener('click', handler);
    card.addEventListener('keydown', e => { if (e.key === 'Enter') handler(); });
    container.appendChild(card);
  });
}

// ── Git workflow state panel ───────────────────────────────────────
function renderGitState(data) {
  const container = document.getElementById('git-state');
  if (!container || !data) return;
  const rows = [
    ['Workflow', data.workflow_id || state.workflowId || '\u2014'],
    ['Plan', data.plan_id || state.lastPlanId || '\u2014'],
    ['State', data.current_state || data.status || '\u2014'],
    ['Branch / PR', data.branch ? `${data.branch}${data.pr_title ? ` \u00b7 ${data.pr_title}` : ''}` : '\u2014'],
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

// ── Observability trace list (waterfall) ──────────────────────────
function renderTraces() {
  const list = document.getElementById('trace-list');
  if (!list) return;
  if (!state.traces.length) return;

  const maxMs = Math.max(...state.traces.map(t => t.elapsedMs), 1);
  list.innerHTML = '';

  state.traces.forEach(t => {
    const barPct = Math.max(4, Math.round((t.elapsedMs / maxMs) * 100));
    const card = document.createElement('div');
    card.className = 'trace-row';
    card.innerHTML = `
      <div class="trace-row-header">
        <span class="trace-status-icon">${t.ok ? '\u2713' : '\u2717'}</span>
        <span class="trace-path">${escapeHtml(t.path)}</span>
        <span class="trace-duration">${t.elapsedMs} ms</span>
      </div>
      <div class="trace-bar-track">
        <div class="trace-bar ${t.ok ? 'trace-bar-ok' : 'trace-bar-err'}" style="width:${barPct}%;"></div>
      </div>
      ${t.traceId ? `<div class="trace-id">trace ${escapeHtml(t.traceId)}</div>` : ''}
    `;
    list.appendChild(card);
  });
}

// ── Evaluation Dashboard ───────────────────────────────────────────
async function loadEvaluation() {
  const grid = document.getElementById('eval-metrics-grid');
  if (!grid) return;

  let data;
  try {
    data = await api('/evaluations/latest');
  } catch {
    grid.innerHTML = '<div class="card empty-state"><p class="card-desc">Failed to load evaluation data.</p></div>';
    return;
  }

  grid.innerHTML = '';

  const gateColor = data.quality_gate === true ? 'var(--secondary)' : data.quality_gate === false ? 'var(--crimson)' : 'var(--text-muted)';
  const statusCard = document.createElement('div');
  statusCard.className = 'eval-metric-card';
  statusCard.innerHTML = `
    <div class="eval-metric-value" style="color:${gateColor};">${escapeHtml(String(data.status || 'UNKNOWN'))}</div>
    <div class="eval-metric-label">Status</div>
    <div class="eval-metric-sub">${data.quality_gate === true ? '\u2713 Quality Gate Passed' : data.quality_gate === false ? '\u2717 Quality Gate Failed' : 'Quality Gate Unknown'}</div>
  `;
  grid.appendChild(statusCard);

  const casesCard = document.createElement('div');
  casesCard.className = 'eval-metric-card';
  casesCard.innerHTML = `
    <div class="eval-metric-value">${escapeHtml(String(data.benchmark_cases ?? '\u2014'))}</div>
    <div class="eval-metric-label">Benchmark Cases</div>
  `;
  grid.appendChild(casesCard);

  const metrics = data.metrics || {};
  Object.entries(metrics).forEach(([key, val]) => {
    const card = document.createElement('div');
    card.className = 'eval-metric-card';
    card.innerHTML = `
      <div class="eval-metric-value">${escapeHtml(String(val))}</div>
      <div class="eval-metric-label">${escapeHtml(key.replace(/_/g, ' '))}</div>
    `;
    grid.appendChild(card);
  });
}

// ── Wire up interactive actions ────────────────────────────────────
function initActions() {
  const btnQuery = document.getElementById('btn-run-query');
  if (btnQuery) btnQuery.addEventListener('click', runInvestigation);

  const searchInput = document.getElementById('search-input');
  if (searchInput) searchInput.addEventListener('keydown', e => { if (e.key === 'Enter') runInvestigation(); });

  const btnPlan = document.getElementById('btn-plan-change');
  if (btnPlan) btnPlan.addEventListener('click', planChange);

  const crInput = document.getElementById('change-request-input');
  if (crInput) crInput.addEventListener('keydown', e => { if (e.key === 'Enter') planChange(); });

  const btnApprove = document.getElementById('btn-approve');
  if (btnApprove) btnApprove.addEventListener('click', approvePlan);

  const btnApproveProminent = document.getElementById('btn-approve-prominent');
  if (btnApproveProminent) btnApproveProminent.addEventListener('click', approvePlan);

  const btnReject = document.getElementById('btn-reject-plan');
  if (btnReject) btnReject.addEventListener('click', () => {
    state.lastPlanId = null;
    const actionRow = document.getElementById('patch-action-row');
    if (actionRow) actionRow.style.display = 'none';
    renderDiff(null, 'Plan rejected.');
    showToast('Plan rejected.', 'info');
  });

  const btnPatch = document.getElementById('btn-generate-patch');
  if (btnPatch) btnPatch.addEventListener('click', generatePatch);

  const btnRepair = document.getElementById('btn-run-repair');
  if (btnRepair) btnRepair.addEventListener('click', runRepair);

  const btnRepairDedicated = document.getElementById('btn-execute-repair-dedicated');
  if (btnRepairDedicated) btnRepairDedicated.addEventListener('click', runDedicatedRepair);

  const btnApproveGit = document.getElementById('btn-approve-git');
  if (btnApproveGit) btnApproveGit.addEventListener('click', approveGitCommit);

  const btnExecuteGit = document.getElementById('btn-execute-git-pr');
  if (btnExecuteGit) btnExecuteGit.addEventListener('click', executeGitCommit);

  const btnOpenReg = document.getElementById('btn-open-register-modal');
  const btnCloseReg = document.getElementById('btn-close-register-modal');
  const modalReg = document.getElementById('register-repo-modal');
  const btnSubmitReg = document.getElementById('btn-submit-register-repo');

  if (btnOpenReg && modalReg) btnOpenReg.onclick = () => { modalReg.hidden = false; };
  if (btnCloseReg && modalReg) btnCloseReg.onclick = () => { modalReg.hidden = true; };
  if (btnSubmitReg) {
    btnSubmitReg.onclick = async () => {
      const pathInput = document.getElementById('reg-repo-path');
      const nameInput = document.getElementById('reg-repo-name');
      const path = pathInput ? pathInput.value.trim() : '';
      const name = nameInput ? nameInput.value.trim() : '';
      if (!path) { showToast('Please enter a folder path.', 'info'); return; }
      try {
        const res = await api('/repositories', {
          method: 'POST',
          body: JSON.stringify({ path, name: name || undefined }),
        });
        showToast(`Repository ${res.name || res.repository_id} registered.`, 'success');
        if (modalReg) modalReg.hidden = true;
        if (pathInput) pathInput.value = '';
        if (nameInput) nameInput.value = '';
        loadRepositories();
      } catch (err) {
        showToast(`Registration failed: ${err.message}`, 'error');
      }
    };
  }

  initGraphToolbar();
}

// ── Utility ────────────────────────────────────────────────────────
function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}
