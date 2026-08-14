// CodeGraph Studio — Interactive Web Client

document.addEventListener('DOMContentLoaded', () => {
  initTabs();
  initGraphCanvas();
  initActions();
});

// Tab Switching
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

// Interactive Knowledge Graph Canvas
function initGraphCanvas() {
  const svg = document.getElementById('graph-svg');
  if (!svg) return;

  const nodes = [
    { id: 'UserService', type: 'class', label: 'UserService', x: 200, y: 220, color: '#00daf3', icon: 'person' },
    { id: 'AuthService', type: 'class', label: 'AuthService', x: 420, y: 140, color: '#4edea3', icon: 'lock' },
    { id: 'PostgreSQL', type: 'db', label: 'PostgreSQL', x: 420, y: 320, color: '#ffb95f', icon: 'database' },
    { id: 'Redis', type: 'cache', label: 'Redis', x: 620, y: 220, color: '#ffb4ab', icon: 'memory' },
    { id: 'ArchDiagram', type: 'doc', label: 'architecture.png', x: 200, y: 360, color: '#c3f5ff', icon: 'image' }
  ];

  const edges = [
    { from: 'UserService', to: 'AuthService', label: 'CALLS' },
    { from: 'UserService', to: 'PostgreSQL', label: 'READS' },
    { from: 'AuthService', to: 'PostgreSQL', label: 'USES' },
    { from: 'AuthService', to: 'Redis', label: 'CACHE' },
    { from: 'ArchDiagram', to: 'AuthService', label: 'DESCRIBES' }
  ];

  // Render Edges
  edges.forEach(edge => {
    const src = nodes.find(n => n.id === edge.from);
    const tgt = nodes.find(n => n.id === edge.to);
    if (!src || !tgt) return;

    const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    line.setAttribute('x1', src.x);
    line.setAttribute('y1', src.y);
    line.setAttribute('x2', tgt.x);
    line.setAttribute('y2', tgt.y);
    line.setAttribute('stroke', '#3b494c');
    line.setAttribute('stroke-width', '1.5');
    line.setAttribute('marker-end', 'url(#arrow)');
    svg.appendChild(line);
  });

  // Render Nodes
  nodes.forEach(node => {
    const g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('transform', `translate(${node.x}, ${node.y})`);
    g.style.cursor = 'pointer';

    const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
    circle.setAttribute('r', '20');
    circle.setAttribute('fill', '#171f33');
    circle.setAttribute('stroke', node.color);
    circle.setAttribute('stroke-width', '2');
    g.appendChild(circle);

    const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('y', '32');
    text.setAttribute('fill', '#dae2fd');
    text.setAttribute('font-size', '11');
    text.setAttribute('font-family', 'JetBrains Mono');
    text.textContent = node.label;
    g.appendChild(text);

    g.addEventListener('click', () => {
      inspectNode(node);
    });

    svg.appendChild(g);
  });
}

function inspectNode(node) {
  const header = document.getElementById('inspect-header');
  if (header) header.textContent = `Selected: ${node.label} (${node.type.toUpperCase()})`;
}

// Live Interactive Actions
function initActions() {
  const btnApprove = document.getElementById('btn-approve');
  if (btnApprove) {
    btnApprove.addEventListener('click', () => {
      btnApprove.textContent = '✓ Plan Approved';
      btnApprove.classList.remove('btn-primary');
      btnApprove.classList.add('btn-ghost');
      alert('Human Approval Granted: Change plan approved for patch generation.');
    });
  }

  const btnQuery = document.getElementById('btn-run-query');
  if (btnQuery) {
    btnQuery.addEventListener('click', () => {
      const input = document.getElementById('search-input');
      const val = input ? input.value : 'AuthFlow';
      alert(`CodeGraph Query: Retrieving multimodal grounded context for '${val}'`);
    });
  }
}
