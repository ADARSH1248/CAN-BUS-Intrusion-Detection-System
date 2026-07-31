/* ══════════════════════════════════════════════════
   CAN BUS IDS — MASTER SCRIPT
   Handles: Canvas · Upload · Processing · Dashboard
   ══════════════════════════════════════════════════ */
'use strict';

/* ────────────────────────────────────────
   1. NETWORK CANVAS (home + upload bg)
   ──────────────────────────────────────── */
(function initNetworkCanvas() {
  const canvas = document.getElementById('networkCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  let W, H, nodes = [];

  const NODE_COUNT = 55;
  const LINK_DIST  = 130;
  const COLORS     = ['#00d4ff','#7b2ff7','#00aadd','#4a1fb0'];

  function resize() {
    W = canvas.width  = canvas.offsetWidth;
    H = canvas.height = canvas.offsetHeight;
  }
  function mkNodes() {
    nodes = Array.from({ length: NODE_COUNT }, () => ({
      x: Math.random() * W,  y: Math.random() * H,
      vx: (Math.random() - 0.5) * 0.45,
      vy: (Math.random() - 0.5) * 0.45,
      r:  Math.random() * 2.2 + 1,
      color: COLORS[Math.floor(Math.random() * COLORS.length)],
    }));
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dx = nodes[i].x - nodes[j].x, dy = nodes[i].y - nodes[j].y;
        const d  = Math.hypot(dx, dy);
        if (d < LINK_DIST) {
          ctx.beginPath();
          ctx.moveTo(nodes[i].x, nodes[i].y);
          ctx.lineTo(nodes[j].x, nodes[j].y);
          ctx.strokeStyle = `rgba(0,212,255,${0.18 * (1 - d / LINK_DIST)})`;
          ctx.lineWidth = 0.8;
          ctx.stroke();
        }
      }
    }
    nodes.forEach(n => {
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = n.color;
      ctx.shadowBlur = 8; ctx.shadowColor = n.color;
      ctx.fill(); ctx.shadowBlur = 0;
      n.x += n.vx; n.y += n.vy;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;
    });
    requestAnimationFrame(draw);
  }
  window.addEventListener('resize', () => { resize(); mkNodes(); });
  resize(); mkNodes(); draw();
})();

/* ────────────────────────────────────────
   2. NAVBAR SCROLL EFFECT
   ──────────────────────────────────────── */
(function() {
  const nav = document.querySelector('.ids-navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.boxShadow = window.scrollY > 40
      ? '0 4px 30px rgba(0,212,255,0.12)' : 'none';
  });
})();

/* ────────────────────────────────────────
   3. SMOOTH SCROLL
   ──────────────────────────────────────── */
document.querySelectorAll('a[href^="#"]').forEach(a => {
  a.addEventListener('click', e => {
    const t = document.querySelector(a.getAttribute('href'));
    if (t) { e.preventDefault(); t.scrollIntoView({ behavior: 'smooth' }); }
  });
});

/* ────────────────────────────────────────
   4. UPLOAD PAGE — FILE HANDLING
   ──────────────────────────────────────── */
(function initUpload() {
  const dropZone  = document.getElementById('dropZone');
  const fileInput = document.getElementById('fileInput');
  const preview   = document.getElementById('filePreview');
  const nameEl    = document.getElementById('fileName');
  const sizeEl    = document.getElementById('fileSize');
  const uploadBtn = document.getElementById('uploadBtn');
  const removeBtn = document.getElementById('removeFile');
  const form      = document.getElementById('uploadForm');
  if (!dropZone) return;

  function fmt(b) {
    return b < 1024 ? b + ' B' : b < 1048576
      ? (b/1024).toFixed(1) + ' KB'
      : (b/1048576).toFixed(2) + ' MB';
  }
  function showFile(file) {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      alert('Please select a .CSV file.'); return;
    }
    nameEl.textContent = file.name;
    sizeEl.textContent = fmt(file.size);
    preview.classList.remove('d-none');
    uploadBtn.removeAttribute('disabled');
  }

  dropZone.addEventListener('click', () => fileInput.click());
  fileInput.addEventListener('change', () => { if (fileInput.files[0]) showFile(fileInput.files[0]); });

  dropZone.addEventListener('dragover',  e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) { showFile(f); /* Assign to input */ try { const dt = new DataTransfer(); dt.items.add(f); fileInput.files = dt.files; } catch(_) {} }
  });

  if (removeBtn) {
    removeBtn.addEventListener('click', e => {
      e.stopPropagation();
      preview.classList.add('d-none');
      uploadBtn.setAttribute('disabled', true);
      fileInput.value = '';
    });
  }

  // When form submits — show processing overlay animation
  if (form) {
    form.addEventListener('submit', e => {
      if (!fileInput.files || !fileInput.files[0]) return;
      // Show the overlay and run animation steps (visual only)
      showProcessingOverlay();
    });
  }
})();

/* ────────────────────────────────────────
   5. PROCESSING OVERLAY ANIMATION
      (visual feedback while server processes)
   ──────────────────────────────────────── */
function showProcessingOverlay() {
  const overlay = document.getElementById('processingOverlay');
  if (!overlay) return;
  overlay.classList.remove('d-none');

  const STEPS = [
    { id:'step1', ss:'ss1', label:'Uploading File...',      pct: 15 },
    { id:'step2', ss:'ss2', label:'Extracting Features...', pct: 38 },
    { id:'step3', ss:'ss3', label:'Loading ML Model...',    pct: 60 },
    { id:'step4', ss:'ss4', label:'Predicting Attacks...',  pct: 82 },
    { id:'step5', ss:'ss5', label:'Generating Dashboard...',pct:100 },
  ];
  const fill    = document.getElementById('procProgressFill');
  const pct     = document.getElementById('procPercent');
  const stepLbl = document.getElementById('procStep');
  const DONE    = '<i class="fa-solid fa-circle-check" style="color:var(--green)"></i>';
  const SPIN    = '<i class="fa-solid fa-circle-notch fa-spin"></i>';
  const WAIT    = '<i class="fa-regular fa-clock"></i>';

  STEPS.forEach(s => {
    const el = document.getElementById(s.id);
    const ss = document.getElementById(s.ss);
    if (el) el.classList.remove('active','done');
    if (ss) ss.innerHTML = WAIT;
  });

  function run(i) {
    if (i >= STEPS.length) return;
    const s  = STEPS[i];
    const el = document.getElementById(s.id);
    const ss = document.getElementById(s.ss);
    if (i > 0) {
      const p  = STEPS[i-1];
      const pe = document.getElementById(p.id);
      const ps = document.getElementById(p.ss);
      if (pe) { pe.classList.remove('active'); pe.classList.add('done'); }
      if (ps) ps.innerHTML = DONE;
    }
    if (el) el.classList.add('active');
    if (ss) ss.innerHTML = SPIN;
    if (stepLbl) stepLbl.textContent = s.label;
    if (fill) fill.style.width = s.pct + '%';
    if (pct)  pct.textContent  = s.pct + '%';
    // Each visual step takes 600-900 ms; actual redirect is server-driven
    setTimeout(() => run(i + 1), 700 + Math.random() * 400);
  }
  run(0);
}

/* ────────────────────────────────────────
   6. DASHBOARD — CLOCK
   ──────────────────────────────────────── */
(function() {
  const el = document.getElementById('topbarTime');
  if (!el) return;
  function tick() { el.textContent = new Date().toLocaleTimeString('en-IN', { hour12: false }); }
  tick(); setInterval(tick, 1000);
})();

/* ────────────────────────────────────────
   7. DASHBOARD — SIDEBAR TOGGLE
   ──────────────────────────────────────── */
(function() {
  const toggle   = document.getElementById('sidebarToggle');
  const sidebar  = document.getElementById('sidebar');
  const wrapper  = document.getElementById('dashboardWrapper');
  const closeBtn = document.getElementById('sidebarClose');
  if (!toggle || !sidebar) return;

  toggle.addEventListener('click', () => {
    if (window.innerWidth < 992) {
      sidebar.classList.toggle('open');
    } else {
      sidebar.classList.toggle('collapsed');
      wrapper && wrapper.classList.toggle('sidebar-hidden');
    }
  });
  closeBtn && closeBtn.addEventListener('click', () => sidebar.classList.remove('open'));
  document.addEventListener('click', e => {
    if (window.innerWidth < 992 && sidebar.classList.contains('open')
        && !sidebar.contains(e.target) && e.target !== toggle) {
      sidebar.classList.remove('open');
    }
  });
})();

/* ────────────────────────────────────────
   8. DASHBOARD — COUNTER ANIMATION
   ──────────────────────────────────────── */
(function() {
  const counters = document.querySelectorAll('.stat-card-num[data-target]');
  if (!counters.length) return;
  const obs = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const el     = entry.target;
      const target = parseInt(el.dataset.target, 10) || 0;
      const dur    = 1600;
      const t0     = performance.now();
      function step(now) {
        const p = Math.min((now - t0) / dur, 1);
        el.textContent = Math.floor((1 - Math.pow(1 - p, 3)) * target).toLocaleString();
        if (p < 1) requestAnimationFrame(step);
        else el.textContent = target.toLocaleString();
      }
      requestAnimationFrame(step);
      obs.unobserve(el);
    });
  }, { threshold: 0.3 });
  counters.forEach(c => obs.observe(c));
})();

/* ────────────────────────────────────────
   9. DASHBOARD — CHARTS (from IDS_RESULTS)
   ──────────────────────────────────────── */
(function initCharts() {
  if (typeof Chart === 'undefined' || typeof IDS_RESULTS === 'undefined') return;

  Chart.defaults.color = '#64748b';
  Chart.defaults.font.family = "'Segoe UI', system-ui, sans-serif";

  const C = { benign:'#22c55e', masquerade:'#eab308', real:'#ef4444', suspension:'#f97316' };
  const grid = { color:'rgba(255,255,255,0.05)', drawBorder: false };
  const tooltip = { backgroundColor:'rgba(10,22,40,0.95)', borderColor:'rgba(0,212,255,0.3)', borderWidth:1 };

  const pieData = IDS_RESULTS.chart.pie;   // [benign, masq, real, susp]
  const barData = IDS_RESULTS.chart.bar;
  const area    = IDS_RESULTS.chart.area;

  /* PIE */
  const pieCtx = document.getElementById('pieChart');
  if (pieCtx) {
    new Chart(pieCtx, {
      type: 'doughnut',
      data: {
        labels: ['Benign','Masquerade','Real Attack','Suspension'],
        datasets: [{
          data: pieData,
          backgroundColor: [C.benign, C.masquerade, C.real, C.suspension],
          borderColor: '#050d1a', borderWidth: 3, hoverOffset: 12,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '68%',
        plugins: {
          legend: { display: false },
          tooltip: { ...tooltip, callbacks: {
            label: ctx => {
              const total = pieData.reduce((a,b)=>a+b,0) || 1;
              return ` ${ctx.label}: ${ctx.parsed.toLocaleString()} (${((ctx.parsed/total)*100).toFixed(1)}%)`;
            }
          }},
        },
      },
    });
  }

  /* BAR */
  const barCtx = document.getElementById('barChart');
  if (barCtx) {
    new Chart(barCtx, {
      type: 'bar',
      data: {
        labels: ['Benign','Masquerade','Real Attack','Suspension'],
        datasets: [{
          label: 'Count',
          data: barData,
          backgroundColor: [C.benign, C.masquerade, C.real, C.suspension],
          borderRadius: 6, borderSkipped: false,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip },
        scales: {
          x: { grid, ticks: { color:'#64748b', font:{size:10} } },
          y: { grid, ticks: { color:'#64748b', font:{size:10}, callback: v => v.toLocaleString() } },
        },
      },
    });
  }

  /* AREA */
  const areaCtx = document.getElementById('areaChart');
  if (areaCtx) {
    new Chart(areaCtx, {
      type: 'line',
      data: {
        labels: area.labels,
        datasets: [
          { label:'Benign',     data: area.benign,      borderColor: C.benign,      backgroundColor:'rgba(34,197,94,0.08)',  fill:true, tension:0.4, pointRadius:3, borderWidth:2 },
          { label:'Masquerade', data: area.masquerade,  borderColor: C.masquerade,  backgroundColor:'rgba(234,179,8,0.08)', fill:true, tension:0.4, pointRadius:3, borderWidth:2 },
          { label:'Real Attack',data: area.real_attack, borderColor: C.real,        backgroundColor:'rgba(239,68,68,0.08)',  fill:true, tension:0.4, pointRadius:3, borderWidth:2 },
          { label:'Suspension', data: area.suspension,  borderColor: C.suspension,  backgroundColor:'rgba(249,115,22,0.08)',fill:true, tension:0.4, pointRadius:3, borderWidth:2 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        interaction: { mode:'index', intersect:false },
        plugins: {
          legend: { position:'top', align:'end', labels:{ boxWidth:10, padding:14, font:{size:11}, color:'#94a3b8' } },
          tooltip,
        },
        scales: {
          x: { grid, ticks:{ color:'#64748b', font:{size:10} } },
          y: { grid, ticks:{ color:'#64748b', font:{size:10}, callback: v => v.toLocaleString() } },
        },
      },
    });
  }
})();

/* ────────────────────────────────────────
   10. PREDICTIONS TABLE (from IDS_RESULTS)
   ──────────────────────────────────────── */
const RISK_CLS = { Low:'risk-low', Medium:'risk-medium', High:'risk-high', Critical:'risk-critical' };
const PRED_CLS = { Benign:'pred-benign', Masquerade:'pred-masquerade', 'Real Attack':'pred-real', Suspension:'pred-suspension' };
const PAGE_SIZE = 15;
let _currentPage = 1;
let _filteredRows = [];

function renderTable(filter = 'all') {
  const tbody = document.getElementById('tableBody');
  if (!tbody || typeof IDS_RESULTS === 'undefined') return;
  _filteredRows = filter === 'all'
    ? IDS_RESULTS.rows
    : IDS_RESULTS.rows.filter(r => r.prediction === filter);
  _currentPage = 1;
  renderPage();
}

function renderPage() {
  const tbody = document.getElementById('tableBody');
  const info  = document.getElementById('tableInfo');
  if (!tbody) return;
  const start = (_currentPage - 1) * PAGE_SIZE;
  const end   = Math.min(start + PAGE_SIZE, _filteredRows.length);
  const slice = _filteredRows.slice(start, end);

  tbody.innerHTML = slice.map(r => `
    <tr>
      <td>${r.index}</td>
      <td style="font-size:0.75rem;font-family:monospace;color:var(--text-muted)">${r.timestamp}</td>
      <td class="can-id">${r.can_id}</td>
      <td class="${PRED_CLS[r.prediction] || ''}">${r.prediction}</td>
      <td><span class="risk-badge ${RISK_CLS[r.risk] || ''}">${r.risk}</span></td>
      <td>${r.status === 'Normal'
        ? '<span class="status-badge risk-low">Normal</span>'
        : r.status === 'Suspicious'
        ? '<span class="status-badge risk-medium">Suspicious</span>'
        : '<span class="status-badge risk-critical">⚠ Attack</span>'}</td>
    </tr>`).join('');

  if (info) info.textContent = `Showing ${start+1}–${end} of ${_filteredRows.length} records`;
  renderPagination();
}

function renderPagination() {
  const nav   = document.getElementById('pagination');
  if (!nav) return;
  const pages = Math.ceil(_filteredRows.length / PAGE_SIZE);
  let html = `<li class="page-item ${_currentPage===1?'disabled':''}">
    <a class="page-link" href="#" onclick="goPage(${_currentPage-1});return false;">&laquo;</a></li>`;
  for (let i = 1; i <= Math.min(pages, 6); i++) {
    html += `<li class="page-item ${i===_currentPage?'active':''}">
      <a class="page-link" href="#" onclick="goPage(${i});return false;">${i}</a></li>`;
  }
  if (pages > 6) html += `<li class="page-item disabled"><a class="page-link">…</a></li>`;
  html += `<li class="page-item ${_currentPage===pages?'disabled':''}">
    <a class="page-link" href="#" onclick="goPage(${_currentPage+1});return false;">&raquo;</a></li>`;
  nav.innerHTML = html;
}

function goPage(p) {
  const pages = Math.ceil(_filteredRows.length / PAGE_SIZE);
  if (p < 1 || p > pages) return;
  _currentPage = p;
  renderPage();
}

function filterTable() {
  const val = document.getElementById('filterSelect')?.value || 'all';
  renderTable(val);
}

function exportCSV() {
  if (typeof IDS_RESULTS === 'undefined') return;
  const hdr = 'Index,Timestamp,CAN_ID,Prediction,Risk,Status\n';
  const body = IDS_RESULTS.rows.map(r =>
    `${r.index},"${r.timestamp}","${r.can_id}","${r.prediction}","${r.risk}","${r.status}"`).join('\n');
  const a   = document.createElement('a');
  a.href    = URL.createObjectURL(new Blob([hdr + body], { type:'text/csv' }));
  a.download= 'canids_predictions.csv';
  a.click();
}

document.addEventListener('DOMContentLoaded', () => {
  if (typeof IDS_RESULTS !== 'undefined') renderTable();
});
