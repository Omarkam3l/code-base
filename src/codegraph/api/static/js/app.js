// CodeGraph Studio — Interactive Web Client

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initSidebarNav();
  initGraphCanvas();
  initActions();
});

// ── Tab Switching ─────────────────────────────────────────
function initTabs() {
  const tabs = document.querySelectorAll('.tab-button');
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const target = document.getElementById(tab.dataset.tab);
      if (target) target.classList.add('active');
    });
  });
}

// ── Sidebar Navigation ───────────────────────────────────
function initSidebarNav() {
  const navItems = document.querySelectorAll('.nav-item');
  navItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      navItems.forEach(n => n.classList.remove('active'));
      item.classList.add('active');
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

// ── Interactive Knowledge Graph Canvas ───────────────────
function initGraphCanvas() {
  const svg = document.getElementById('graph-svg');
  if (!svg) return;

  const rect = svg.getBoundingClientRect();
  const w = rect.width || 800;
  const h = rect.height || 500;

  // Set a viewBox so coordinates are predictable and content scales
  svg.setAttribute('viewBox', `0 0 ${w} ${h}`);

  const cx = w / 2;
  const cy = h / 2;

  // Use elliptical spread — fill ~40% of each axis independently
  // so the graph adapts to wide/tall viewports without clustering
  const rx = w * 0.30;  // horizontal radius
  const ry = h * 0.30;  // vertical radius
  const padding = 60;   // keep nodes away from edges

  const nodes = [
    { id: 'UserService',  type: 'class', label: 'UserService',      angle: Math.PI,           color: '#00daf3' },
    { id: 'AuthService',  type: 'class', label: 'AuthService',      angle: -Math.PI / 5,      color: '#4edea3' },
    { id: 'PostgreSQL',   type: 'db',    label: 'PostgreSQL',       angle: Math.PI / 2.5,     color: '#ffb95f' },
    { id: 'Redis',        type: 'cache', label: 'Redis',            angle: -0.1,              color: '#ffb4ab' },
    { id: 'ArchDiagram',  type: 'doc',   label: 'architecture.png', angle: (3 * Math.PI) / 4, color: '#c3f5ff' }
  ];

  // Compute positions on an ellipse, clamped within padding
  nodes.forEach(n => {
    n.x = Math.max(padding, Math.min(w - padding, cx + Math.cos(n.angle) * rx));
    n.y = Math.max(padding, Math.min(h - padding, cy + Math.sin(n.angle) * ry));
  });

  const edges = [
    { from: 'UserService', to: 'AuthService', label: 'CALLS' },
    { from: 'UserService', to: 'PostgreSQL',  label: 'READS' },
    { from: 'AuthService', to: 'PostgreSQL',  label: 'WRITES' },
    { from: 'AuthService', to: 'Redis',       label: 'CACHE' },
    { from: 'ArchDiagram', to: 'AuthService',  label: 'DESCRIBES' }
  ];

  const nodeMap = {};
  nodes.forEach(n => { nodeMap[n.id] = n; });

  // Node sizing — scale relative to viewport for readability
  const nodeRadius = Math.max(24, Math.min(40, Math.min(w, h) * 0.05));
  const iconSize = Math.round(nodeRadius * 0.7);
  const labelSize = Math.max(11, Math.round(nodeRadius * 0.45));
  const edgeLabelSize = Math.max(10, Math.round(nodeRadius * 0.35));

  // ── Render Edges ──
  edges.forEach(edge => {
    const src = nodeMap[edge.from];
    const tgt = nodeMap[edge.to];
    if (!src || !tgt) return;

    const line = createSVG('line', {
      x1: src.x, y1: src.y,
      x2: tgt.x, y2: tgt.y,
      stroke: '#3b494c',
      'stroke-width': '1.5',
      'stroke-dasharray': edge.label === 'DESCRIBES' ? '6 4' : 'none',
      'marker-end': 'url(#arrow)'
    });
    svg.appendChild(line);

    // Edge label at midpoint
    const mx = (src.x + tgt.x) / 2;
    const my = (src.y + tgt.y) / 2;

    // Offset label perpendicular to the edge to avoid overlap
    const dx = tgt.x - src.x;
    const dy = tgt.y - src.y;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;
    const offX = -(dy / len) * 12;
    const offY =  (dx / len) * 12;

    const label = createSVG('text', {
      x: mx + offX, y: my + offY,
      'text-anchor': 'middle',
      'dominant-baseline': 'central',
      'font-size': edgeLabelSize,
      'font-family': "'JetBrains Mono', monospace",
      fill: '#5a6a6d',
      'pointer-events': 'none'
    });
    label.textContent = edge.label;
    svg.appendChild(label);
  });

  // ── Render Nodes ──
  let selectedNode = null;

  nodes.forEach(node => {
    const g = createSVG('g', {
      transform: `translate(${node.x}, ${node.y})`,
      class: 'graph-node',
      'data-id': node.id
    });

    // Outer glow ring
    const outerRing = createSVG('circle', {
      r: nodeRadius + 6, fill: 'transparent',
      stroke: node.color, 'stroke-width': '0', opacity: '0.25'
    });
    g.appendChild(outerRing);

    // Main circle
    const circle = createSVG('circle', {
      r: nodeRadius, fill: '#171f33',
      stroke: node.color, 'stroke-width': '2.5'
    });
    g.appendChild(circle);

    // Type icon inside node
    const icons = { class: '◇', db: '⬡', cache: '◎', doc: '▣' };
    const icon = createSVG('text', {
      'text-anchor': 'middle', 'dominant-baseline': 'central',
      y: '1',
      fill: node.color, 'font-size': iconSize,
      'font-family': 'sans-serif', 'pointer-events': 'none'
    });
    icon.textContent = icons[node.type] || '●';
    g.appendChild(icon);

    // Label below node
    const text = createSVG('text', {
      'text-anchor': 'middle', y: nodeRadius + labelSize + 6,
      fill: '#dae2fd', 'font-size': labelSize,
      'font-weight': '500',
      'font-family': "'JetBrains Mono', monospace",
      'pointer-events': 'none'
    });
    text.textContent = node.label;
    g.appendChild(text);

    g.addEventListener('click', () => {
      if (selectedNode) {
        const prev = svg.querySelector(`.graph-node[data-id="${selectedNode}"]`);
        if (prev) prev.classList.remove('selected');
      }
      g.classList.add('selected');
      selectedNode = node.id;
      inspectNode(node);
    });

    svg.appendChild(g);
  });
}

function inspectNode(node) {
  const header = document.getElementById('inspect-header');
  if (header) header.textContent = `Selected: ${node.label} (${node.type.toUpperCase()})`;
  showToast(`Inspecting ${node.label} — ${node.type}`, 'info');
}

function createSVG(tag, attrs) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [k, v] of Object.entries(attrs)) {
    el.setAttribute(k, v);
  }
  return el;
}

// ── Live Interactive Actions ─────────────────────────────
function initActions() {
  // Approve Plan button
  const btnApprove = document.getElementById('btn-approve');
  if (btnApprove) {
    btnApprove.addEventListener('click', () => {
      btnApprove.textContent = '✓ Plan Approved';
      btnApprove.classList.remove('btn-primary');
      btnApprove.classList.add('btn-success');
      btnApprove.disabled = true;
      showToast('Human Approval Granted — Plan approved for patch generation.', 'success');
    });
  }

  // Investigation query
  const btnQuery = document.getElementById('btn-run-query');
  if (btnQuery) {
    btnQuery.addEventListener('click', () => {
      const input = document.getElementById('search-input');
      const val = input ? input.value.trim() : '';
      if (!val) {
        showToast('Please enter a question first.', 'info');
        return;
      }
      btnQuery.textContent = 'Investigating…';
      btnQuery.disabled = true;
      showToast(`Querying: "${val}"`, 'info');

      // Simulate async investigation
      setTimeout(() => {
        btnQuery.textContent = 'Investigate';
        btnQuery.disabled = false;
        showToast('Investigation complete — 2 evidence citations found.', 'success');
      }, 1500);
    });
  }
}
