'use strict';

const $ = (id) => document.getElementById(id);
const els = {
  side: $('side'), tree: $('tree'), search: $('search'), sync: $('syncBtn'), bar: $('bar'),
  title: $('noteTitle'), scroller: $('scroller'), pages: $('pages'), empty: $('empty'),
  pageInput: $('pageInput'), pageTotal: $('pageTotal'), zoomFit: $('zoomFit'), toast: $('toast'),
};

const state = { treeData: [], note: null, scale: 1, fit: true, current: 0, cache: new Map(), nodes: [] };
const THICK = 1;            // multiplicador de grosor de trazo
const MAX_CACHE = 10;       // paginas con datos en memoria

// ---------- utilidades ----------
function toast(msg, ms = 3500) {
  els.toast.textContent = msg; els.toast.hidden = false;
  clearTimeout(toast.t); toast.t = setTimeout(() => { els.toast.hidden = true; }, ms);
}
async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).error || r.statusText);
  return r.json();
}
const fmtDate = (ms) => ms ? new Date(ms).toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' }) : '';
const svg = (d, color) => `<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="${color || 'currentColor'}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICON_FOLDER = (c) => svg('<path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>', c);
const ICON_NOTE = svg('<path d="M6 3h9l4 4v14H6z"/><path d="M15 3v4h4M9 12h7M9 16h7"/>');

// ---------- arbol ----------
function countNotes(n) { return n.kind === 'note' ? 1 : (n.children || []).reduce((a, c) => a + countNotes(c), 0); }

function renderTree() {
  els.tree.textContent = '';
  const q = els.search.value.trim().toLowerCase();
  if (q) {
    const hits = [];
    (function walk(list, path) {
      for (const n of list) {
        if (n.kind === 'note' && n.title.toLowerCase().includes(q)) hits.push([n, path]);
        if (n.children) walk(n.children, path.concat(n.title));
      }
    })(state.treeData, []);
    if (!hits.length) { els.tree.innerHTML = '<div class="none">Sin resultados</div>'; return; }
    for (const [n, path] of hits) els.tree.append(noteRow(n, path.join(' › ')));
    return;
  }
  if (!state.treeData.length) { els.tree.innerHTML = '<div class="none">No hay cuadernos. Pulsa «Sincronizar».</div>'; return; }
  els.tree.append(...state.treeData.map(nodeEl));
}

function nodeEl(n) {
  if (n.kind === 'note') return noteRow(n);
  const d = document.createElement('details');
  d.open = openFolders.has(n.id);
  d.addEventListener('toggle', () => { d.open ? openFolders.add(n.id) : openFolders.delete(n.id); saveOpen(); });
  const s = document.createElement('summary');
  s.className = 'row';
  s.innerHTML = `<span class="chev">▶</span>${ICON_FOLDER(n.color)}<span class="name"></span><span class="meta">${countNotes(n)}</span>`;
  s.querySelector('.name').textContent = n.title;
  d.append(s);
  const kids = document.createElement('div'); kids.className = 'kids';
  if (n.children.length) kids.append(...n.children.map(nodeEl));
  else kids.innerHTML = '<div class="none">Vacía</div>';
  d.append(kids);
  return d;
}

function noteRow(n, sub) {
  const r = document.createElement('div');
  r.className = 'row' + (state.note && state.note.id === n.id ? ' active' : '');
  r.dataset.id = n.id;
  r.innerHTML = `${ICON_NOTE}<span class="name"></span><span class="meta">${n.pages} p.</span>`;
  r.querySelector('.name').textContent = n.title;
  r.title = (sub ? sub + '\n' : '') + 'Modificado: ' + fmtDate(n.modified);
  r.addEventListener('click', () => { location.hash = '#/note/' + n.id; if (innerWidth < 760) els.side.classList.add('hidden'); });
  return r;
}

let openFolders = new Set();
try { openFolders = new Set(JSON.parse(localStorage.getItem('openFolders') || '[]')); } catch (_) { /* sin almacenamiento */ }
function saveOpen() { try { localStorage.setItem('openFolders', JSON.stringify([...openFolders])); } catch (_) { /* nada */ } }

async function loadTree() {
  state.treeData = await api('/api/tree');
  if (!openFolders.size) {                // primera vez: abrir todo
    (function all(l) { for (const n of l) if (n.children) { openFolders.add(n.id); all(n.children); } })(state.treeData);
  }
  renderTree();
}

// ---------- dibujo ----------
function drawPaper(ctx, w, h, p) {
  const sp = p.requiredItemSpace || 50;
  const L = p.leftPadding ?? 0, R = p.rightPadding ?? 0, T = p.topPadding ?? 0, B = p.bottomPadding ?? 0;
  ctx.strokeStyle = 'rgba(110,110,110,0.30)'; ctx.fillStyle = 'rgba(110,110,110,0.55)'; ctx.lineWidth = 1;
  const hlines = (step) => { ctx.beginPath(); for (let y = T; y <= h - B + 0.5; y += step) { ctx.moveTo(L, y); ctx.lineTo(w - R, y); } ctx.stroke(); };
  switch (p.style) {
    case 'NewSquarePaperStyle':
      ctx.beginPath();
      for (let x = L; x <= w - R + 0.5; x += sp) { ctx.moveTo(x, T); ctx.lineTo(x, h - B); }
      ctx.stroke(); hlines(sp); break;
    case 'NewDotPaperStyle':
      for (let y = T; y <= h - B + 0.5; y += sp) for (let x = L; x <= w - R + 0.5; x += sp) { ctx.beginPath(); ctx.arc(x, y, 1.7, 0, 6.2832); ctx.fill(); }
      break;
    case 'NewLinePaperStyle': hlines(sp); break;
    case 'LineTwoColumnPaperStyle':
      hlines(sp); ctx.beginPath(); ctx.moveTo(w / 2, T); ctx.lineTo(w / 2, h - B); ctx.stroke(); break;
    default: break;
  }
}

function drawStroke(ctx, s) {
  const p = s.p, q = s.q, n = p.length / 2;
  const alpha = s.brush.includes('pencil') ? 0.85 : 1;
  ctx.strokeStyle = s.c; ctx.fillStyle = s.c; ctx.globalAlpha = alpha; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  const width = (i) => Math.max(0.6, s.w * (0.54 + 0.9 * q[i]) * THICK);
  if (n === 1 || (n > 1 && Math.hypot(p[2 * n - 2] - p[0], p[2 * n - 1] - p[1]) < 0.01 && n < 4)) {
    ctx.beginPath(); ctx.arc(p[0], p[1], width(0) / 2, 0, 6.2832); ctx.fill();
  } else {
    let px = p[0], py = p[1];
    for (let i = 1; i < n; i++) {
      const cx = p[2 * i], cy = p[2 * i + 1];
      const mx = i < n - 1 ? (cx + p[2 * i + 2]) / 2 : cx;
      const my = i < n - 1 ? (cy + p[2 * i + 3]) / 2 : cy;
      ctx.lineWidth = width(i);
      ctx.beginPath(); ctx.moveTo(px, py); ctx.quadraticCurveTo(cx, cy, mx, my); ctx.stroke();
      px = mx; py = my;
    }
  }
  ctx.globalAlpha = 1;
}

function drawLine(ctx, e) {
  ctx.strokeStyle = e.c; ctx.lineWidth = Math.max(1.2, e.w * 1.6); ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  e.p.forEach(([x, y], i) => (i ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
  if (e.closed) ctx.closePath();
  ctx.stroke();
}

// Texto: se conserva solo formato visual; sin scripts, estilos globales ni atributos de evento.
function sanitize(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  doc.querySelectorAll('script,style,iframe,object,embed,link,meta,img,svg,form').forEach((n) => n.remove());
  for (const el of doc.body.querySelectorAll('*')) {
    for (const a of [...el.attributes]) {
      if (/^on/i.test(a.name) || /javascript:/i.test(a.value) || !['style', 'color', 'face', 'align', 'size'].includes(a.name)) el.removeAttribute(a.name);
    }
  }
  return doc.body.innerHTML;
}

function paintPage(node, data) {
  const { w, h } = data;
  const scale = state.scale, dpr = window.devicePixelRatio || 1;
  node.style.background = data.paper.bg;
  node.querySelectorAll('canvas,.tb,img.bg').forEach((n) => n.remove());
  if (data.pdf !== null) {
    const img = document.createElement('img');
    img.className = 'bg'; img.alt = ''; img.decoding = 'async';
    img.src = `/api/note/${state.note.id}/bg/${node.dataset.i}.png`;
    node.prepend(img);
  }
  const cv = document.createElement('canvas');
  cv.width = Math.round(w * scale * dpr); cv.height = Math.round(h * scale * dpr);
  node.append(cv);
  const ctx = cv.getContext('2d');
  ctx.setTransform(scale * dpr, 0, 0, scale * dpr, 0, 0);
  if (data.pdf === null) drawPaper(ctx, w, h, data.paper);
  for (const e of data.elems) {
    if (e.k === 's') drawStroke(ctx, e);
    else if (e.k === 'l') drawLine(ctx, e);
    else if (e.k === 't') {
      const t = document.createElement('div');
      t.className = 'tb';
      t.style.cssText = `left:${e.x * scale}px;top:${e.y * scale}px;width:${e.w}px;transform:scale(${scale});color:${e.c};font-size:${e.size}px`;
      t.innerHTML = sanitize(e.html);
      node.append(t);
    }
  }
}

// ---------- cuaderno ----------
const io = new IntersectionObserver((entries) => {
  for (const en of entries) {
    const node = en.target;
    if (en.isIntersecting) loadPage(node);
    else unloadPage(node);
  }
}, { root: els.scroller, rootMargin: '1400px 0px' });

async function loadPage(node) {
  const i = +node.dataset.i, note = state.note;
  if (node.dataset.state === 'ready' || node.dataset.state === 'loading') return;
  node.dataset.state = 'loading';
  try {
    let data = state.cache.get(i);
    if (!data) { data = await api(`/api/note/${note.id}/page/${i}`); }
    if (state.note !== note || node.dataset.state !== 'loading') return;
    state.cache.delete(i); state.cache.set(i, data);
    while (state.cache.size > MAX_CACHE) state.cache.delete(state.cache.keys().next().value);
    paintPage(node, data);
    node.dataset.state = 'ready';
    node.classList.remove('err');
  } catch (e) {
    node.dataset.state = ''; node.classList.add('err'); console.error(e);
  }
}
function unloadPage(node) {
  if (node.dataset.state === 'ready' || node.dataset.state === 'loading') {
    node.querySelectorAll('canvas,.tb,img.bg').forEach((n) => n.remove());
    node.dataset.state = '';
  }
}

function fitScale() {
  const maxW = Math.max(...state.note.pages.map((p) => p.w));
  const avail = els.scroller.clientWidth - 52;
  return Math.max(0.2, Math.min(1.6, avail / maxW));
}

function layoutPages() {
  const note = state.note;
  state.scale = state.fit ? fitScale() : state.scale;
  els.zoomFit.textContent = state.fit ? 'Ajustar' : Math.round(state.scale * 100) + ' %';
  els.pages.querySelectorAll('.page').forEach((node, i) => {
    const p = note.pages[i];
    node.style.width = Math.round(p.w * state.scale) + 'px';
    node.style.height = Math.round(p.h * state.scale) + 'px';
    node.dataset.state = '';
    node.querySelectorAll('canvas,.tb,img.bg').forEach((n) => n.remove());
    io.unobserve(node); io.observe(node);
  });
}

async function openNote(id, page) {
  if (state.note && state.note.id === id) { if (page != null) goPage(page, true); return; }
  els.empty.classList.add('gone');
  els.pages.textContent = '';
  state.cache.clear();
  let note;
  try { note = await api('/api/note/' + id); } catch (e) { toast('No se pudo abrir: ' + e.message); return; }
  state.note = note; state.fit = true; state.current = page || 0;
  els.pageInput.value = state.current + 1;
  els.bar.hidden = false;
  els.title.textContent = note.title;
  document.title = note.title + ' · Visor NoteIn';
  els.pageTotal.textContent = '/ ' + note.pages.length;
  els.pageInput.max = note.pages.length;
  note.pages.forEach((p, i) => {
    const d = document.createElement('div');
    d.className = 'page'; d.dataset.i = i;
    const num = document.createElement('div'); num.className = 'num'; num.textContent = i + 1;
    d.append(num);
    els.pages.append(d);
  });
  layoutPages();
  renderTree();
  if (page) requestAnimationFrame(() => goPage(page, true)); else els.scroller.scrollTop = 0;
  try { localStorage.setItem('lastNote', id); } catch (_) { /* nada */ }
}

function goPage(i, instant) {
  const n = state.note; if (!n) return;
  i = Math.max(0, Math.min(n.pages.length - 1, i));
  const node = els.pages.children[i];
  els.scroller.scrollTo({ top: node.offsetTop - 16, behavior: instant ? 'auto' : 'smooth' });
}

function updateCurrent() {
  const n = state.note; if (!n) return;
  const mid = els.scroller.scrollTop + els.scroller.clientHeight * 0.35;
  let cur = 0;
  for (const node of els.pages.children) { if (node.offsetTop <= mid) cur = +node.dataset.i; else break; }
  if (cur !== state.current) {
    state.current = cur;
    els.pageInput.value = cur + 1;
    history.replaceState(null, '', `#/note/${n.id}/${cur + 1}`);
  }
}
let scrollT;
els.scroller.addEventListener('scroll', () => { clearTimeout(scrollT); scrollT = setTimeout(updateCurrent, 80); });

// ---------- zoom y controles ----------
function setZoom(s) {
  if (!state.note) return;
  const frac = (els.scroller.scrollTop + 100) / Math.max(1, els.pages.scrollHeight);
  state.fit = false; state.scale = Math.max(0.2, Math.min(3, s));
  layoutPages();
  els.scroller.scrollTop = frac * els.pages.scrollHeight - 100;
}
$('zoomIn').onclick = () => setZoom(state.scale * 1.2);
$('zoomOut').onclick = () => setZoom(state.scale / 1.2);
$('zoomFit').onclick = () => { if (!state.note) return; state.fit = true; layoutPages(); goPage(state.current, true); };
$('prev').onclick = () => goPage(state.current - 1);
$('next').onclick = () => goPage(state.current + 1);
$('toggleSide').onclick = () => els.side.classList.toggle('hidden');
els.pageInput.addEventListener('change', () => goPage((parseInt(els.pageInput.value, 10) || 1) - 1));
els.search.addEventListener('input', renderTree);

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.ctrlKey || e.metaKey || e.altKey) return;
  if (e.key === 'ArrowRight') { goPage(state.current + 1); e.preventDefault(); }
  else if (e.key === 'ArrowLeft') { goPage(state.current - 1); e.preventDefault(); }
  else if (e.key === '+' || e.key === '=') setZoom(state.scale * 1.2);
  else if (e.key === '-') setZoom(state.scale / 1.2);
  else if (e.key.toLowerCase() === 'f') $('zoomFit').click();
  else if (e.key === '/') { els.search.focus(); e.preventDefault(); }
});

let resizeT;
window.addEventListener('resize', () => {
  if (!resizeT) updateCurrent();           // fija la pagina visible antes de recalcular el tamano
  clearTimeout(resizeT);
  resizeT = setTimeout(() => {
    resizeT = 0;
    if (state.note && state.fit) { const cur = state.current; layoutPages(); goPage(cur, true); }
  }, 150);
});

// ---------- sincronizacion ----------
els.sync.addEventListener('click', async () => {
  els.sync.disabled = true; els.sync.classList.add('spin');
  toast('Sincronizando con Google Drive…', 60000);
  try {
    const r = await api('/api/sync', { method: 'POST', headers: { 'X-NoteIn': '1' } });
    toast(r.ok ? 'Sincronizado' : 'Error al sincronizar:\n' + r.log, r.ok ? 3000 : 9000);
    await loadTree();
    if (state.note) { const id = state.note.id, pg = state.current + 1; state.note = null; await openNote(id, pg); }
  } catch (e) { toast('Error: ' + e.message, 7000); }
  els.sync.disabled = false; els.sync.classList.remove('spin');
});

// ---------- ruta ----------
function route() {
  const m = location.hash.match(/^#\/note\/([0-9a-f-]{36})(?:\/(\d+))?/);
  if (m) openNote(m[1], m[2] ? +m[2] - 1 : null);
}
window.addEventListener('hashchange', route);

(async function init() {
  try { await loadTree(); } catch (e) { toast('No se pudo leer la carpeta: ' + e.message, 8000); }
  if (location.hash) route();
})();
