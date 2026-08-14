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

  // Scale node positions to fill the viewport
  const cx = w / 2;
  const cy = h / 2;
  const spread = Math.min(w, h) * 0.32;

  const nodes = [
    { id: 'UserService',  type: 'class', label: 'UserService',      angle: Math.PI,       dist: spread,       color: '#00daf3' },
    { id: 'AuthService',  type: 'class', label: 'AuthService',      angle: -Math.PI / 4,  dist: spread * 0.9, color: '#4edea3' },
    { id: 'PostgreSQL',   type: 'db',    label: 'PostgreSQL',       angle: Math.PI / 3,   dist: spread * 1.1, color: '#ffb95f' },
    { id: 'Redis',        type: 'cache', label: 'Redis',            angle: 0,             dist: spread * 1.0, color: '#ffb4ab' },
    { id: 'ArchDiagram',  type: 'doc',   label: 'architecture.png', angle: (3 * Math.PI) / 4, dist: spread * 0.85, color: '#c3f5ff' }
  ];

  // Compute absolute positions from polar coordinates
  nodes.forEach(n => {
    n.x = cx + Math.cos(n.angle) * n.dist;
    n.y = cy + Math.sin(n.angle) * n.dist;
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

  // ── Render Edges ──
  edges.forEach(edge => {
    const src = nodeMap[edge.from];
    const tgt = nodeMap[edge.to];
    if (!src || !tgt) return;

    const line = createSVG('line', {
      x1: src.x, y1: src.y,
      x2: tgt.x, y2: tgt.y,
      stroke: '#2d3449',
      'stroke-width': '1.5',
      'stroke-dasharray': edge.label === 'DESCRIBES' ? '4 3' : 'none',
      'marker-end': 'url(#arrow)'
    });
    svg.appendChild(line);

    // Edge label at midpoint
    const mx = (src.x + tgt.x) / 2;
    const my = (src.y + tgt.y) / 2;
    const label = createSVG('text', {
      x: mx, y: my - 6,
      'text-anchor': 'middle',
      class: 'edge-label'
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

    // Outer glow ring (invisible, expands on hover via CSS)
    const outerRing = createSVG('circle', {
      r: '26', fill: 'transparent',
      stroke: node.color, 'stroke-width': '0', opacity: '0.3'
    });
    g.appendChild(outerRing);

    // Main circle
    const circle = createSVG('circle', {
      r: '22', fill: '#171f33',
      stroke: node.color, 'stroke-width': '2'
    });
    g.appendChild(circle);

    // Type icon (single character shorthand)
    const icons = { class: '◇', db: '⬡', cache: '◎', doc: '▣' };
    const icon = createSVG('text', {
      'text-anchor': 'middle', y: '5',
      fill: node.color, 'font-size': '14',
      'font-family': 'sans-serif', 'pointer-events': 'none'
    });
    icon.textContent = icons[node.type] || '●';
    g.appendChild(icon);

    // Label below node
    const text = createSVG('text', {
      'text-anchor': 'middle', y: '38',
      fill: '#dae2fd', 'font-size': '10',
      'font-family': "'JetBrains Mono', monospace",
      'pointer-events': 'none'
    });
    text.textContent = node.label;
    g.appendChild(text);

    g.addEventListener('click', () => {
      // Deselect previous
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
