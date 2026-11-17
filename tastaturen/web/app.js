// Keyboard Index: Facettensuche im Browser.
// Die Seite ist ohne JavaScript benutzbar (vorgerenderte Liste, Detailseiten unter k/). Dieses Skript lädt danach den
// kompakten Index (idx.*.json) und filtert lokal; Zählungen je Wert nach dem Muster der disjunktiven Facettensuche.
(() => {
  'use strict';
  const D = document, $ = (s, e = D) => e.querySelector(s), $$ = (s, e = D) => [...e.querySelectorAll(s)];
  const C = JSON.parse($('#cfg').textContent), FI = {};
  C.F.forEach(f => { FI[f.k] = f; });
  const A = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz-_', AV = new Int8Array(128);
  for (let i = 0; i < 64; i++) AV[A.charCodeAt(i)] = i;
  const U = -1e9;
  const fmt = n => n.toLocaleString('en-US');
  const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const norm = s => s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '');
  const lab = (k, v) => v === '?' ? 'Unknown' : (C.L[k] && C.L[k][v]) || v;

  let X = null, pend = false, part = false, touched = false, res = [], cc = {}, loaded = 0;
  const S = { sel: {}, rng: {}, q: '', sort: 'rel', lim: 50 };

  // ---------------------------------------------------------------- Index laden und entpacken
  function dec(s, w) {
    const n = s.length / w, a = new Int32Array(n);
    for (let i = 0, p = 0; i < n; i++) { let v = 0; for (let j = 0; j < w; j++) v = v * 64 + AV[s.charCodeAt(p++)]; a[i] = v; }
    return a;
  }
  const slug = n => n.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '') || 'tastatur';
  // eine Index-Stufe entpacken
  function prep(J) {
    const x = { n: J.n, name: J.name, slug: J.name.map((nm, i) => J.sx[i] || slug(nm)), src: dec(J.src, 1), f: {} };
    for (const k in J.f) {
      const g = J.f[k];
      if (g.t === 'c') x.f[k] = { t: 'c', v: g.v, code: dec(g.c, g.w), k: g.k || [[]].concat(g.v.map((_, i) => [i])) };
      else {
        const lo = dec(g.lo, g.w), d = dec(g.d, g.wd), hi = new Int32Array(x.n);
        for (let i = 0; i < x.n; i++) { if (lo[i]) { lo[i] += g.o - 1; hi[i] = lo[i] + d[i]; } else lo[i] = hi[i] = U; }
        x.f[k] = { t: 'r', lo, hi };
      }
    }
    return x;
  }
  // Stufe b an a anhängen: Wertelisten vereinigen, Kombinationen und Codes umschreiben
  function merge(a, b) {
    const n = a.n + b.n, x = { n, name: a.name.concat(b.name), slug: a.slug.concat(b.slug), f: {} };
    const cat = (p, q, T) => { const r = new T(n); r.set(p); r.set(q, a.n); return r; };
    x.src = cat(a.src, b.src, Int32Array);
    for (const k of new Set([...Object.keys(a.f), ...Object.keys(b.f)])) {
      const p = a.f[k], q = b.f[k], t = (p || q).t;
      if (t === 'r') {
        const fill = m => { const r = new Int32Array(m); r.fill(U); return r; };
        const pl = p ? p.lo : fill(a.n), ph = p ? p.hi : fill(a.n), ql = q ? q.lo : fill(b.n), qh = q ? q.hi : fill(b.n);
        x.f[k] = { t: 'r', lo: cat(pl, ql, Int32Array), hi: cat(ph, qh, Int32Array) };
        continue;
      }
      const P = p || { v: [], k: [[]], code: new Int32Array(a.n) }, Q = q || { v: [], k: [[]], code: new Int32Array(b.n) };
      const v = P.v.slice(), vi = new Map(v.map((w, i) => [w, i]));
      for (const w of Q.v) if (!vi.has(w)) { vi.set(w, v.length); v.push(w); }
      const kk = P.k.slice(), ki = new Map(kk.map((c, i) => [c.join(), i]));
      const re = Q.k.map(c => {
        const m = c.map(j => vi.get(Q.v[j])).sort((s, t) => s - t), key = m.join();
        if (!ki.has(key)) { ki.set(key, kk.length); kk.push(m); }
        return ki.get(key);
      });
      const code = new Int32Array(n);
      code.set(P.code);
      for (let i = 0; i < b.n; i++) code[a.n + i] = re[Q.code[i]];
      x.f[k] = { t: 'c', v, k: kk, code };
    }
    return x;
  }
  function finish(x) {
    x.vi = {};
    for (const k in x.f) if (x.f[k].t === 'c') x.vi[k] = new Map(x.f[k].v.map((v, i) => [v, i]));
    x.hay = x.name.map((n, i) => norm(n + ' ' + maker(x, i) + ' ' + x.slug[i]));
    x.ord = new Int32Array(x.n);
    [...x.name.keys()].sort((a, b) => x.name[a].localeCompare(x.name[b], 'en', { sensitivity: 'base' }))
      .forEach((i, r) => { x.ord[i] = r; });
    return x;
  }
  function maker(x, i) { const f = x.f.maker; if (!f) return ''; const c = f.code[i]; return c ? f.v[f.k[c][0]] : ''; }
  function vals(k, i) { const f = X.f[k]; return f && f.t === 'c' ? f.k[f.code[i]].map(j => f.v[j]) : []; }

  function fetchIdx(n) {
    return fetch(C.idx[n]).then(r => {
      if (!r.ok) throw new Error(r.status);
      if (!r.body || !r.body.getReader) return r.text();
      const rd = r.body.getReader(), td = new TextDecoder(), parts = [];
      const pump = () => rd.read().then(({ done, value }) => {
        if (done) { parts.push(td.decode()); return parts.join(''); }
        parts.push(td.decode(value, { stream: true })); loaded += value.length; progress(); return pump();
      });
      return pump();
    }).then(t => prep(JSON.parse(t)));
  }
  function load() {
    fetchIdx(0).then(a => {
      X = finish(a); part = true;
      if (pend || touched) run();
      return fetchIdx(1).then(b => {
        X = finish(merge(a, b)); part = false;
        if (touched) run();
      });
    }).catch(() => { $('#cnt').textContent = 'Could not load the index. Reload to try again.'; });
  }
  function progress() {
    const all = C.raw[0] + C.raw[1];
    if (pend) $('#cnt').innerHTML = 'Loading index… <b>' + Math.min(99, Math.round(100 * loaded / C.raw[0])) + '%</b>';
    else if (part) { const s = $('#cnt small'); if (s) s.textContent = ' · ' + fmt(C.na) + ' of ' + fmt(C.n) + ' searched, rest loading ' + Math.round(100 * loaded / all) + '%'; }
  }

  // ---------------------------------------------------------------- Filtern und Zählen
  function filters() {
    const L = [];
    for (const k in S.sel) {
      const s = S.sel[k], f = X.f[k];
      if (!s.size || !f) continue;
      const ok = new Uint8Array(f.k.length);
      ok[0] = s.has('?') ? 1 : 0;
      for (let c = 1; c < f.k.length; c++) ok[c] = f.k[c].some(j => s.has(f.v[j])) ? 1 : 0;
      L.push({ k, t: 0, code: f.code, ok });
    }
    for (const k in S.rng) {
      const r = S.rng[k], f = X.f[k];
      if (!f || (r.lo == null && r.hi == null)) continue;
      L.push({ k, t: 1, lo: f.lo, hi: f.hi, a: r.lo == null ? U : r.lo, b: r.hi == null ? -U : r.hi, u: !!r.u });
    }
    return L;
  }
  function run() {
    if (!X) { pend = true; D.body.classList.add('busy'); $('#ls').classList.add('busy'); progress(); return; }
    pend = false; touched = true;
    $('#ls').classList.remove('busy');
    const L = filters(), q = norm(S.q.trim()).split(/\s+/).filter(Boolean), FK = Object.keys(X.f);
    res = []; cc = {};
    for (const k of FK) { const f = X.f[k]; cc[k] = new Int32Array(f.t === 'c' ? f.k.length : (FI[k].pre || []).length + 1); }
    const add = (k, i) => {
      const f = X.f[k];
      if (f.t === 'c') { cc[k][f.code[i]]++; return; }
      const lo = f.lo[i], pre = FI[k].pre || [], c = cc[k];
      if (lo === U) { c[pre.length]++; return; }
      for (let p = 0; p < pre.length; p++) if (f.hi[i] >= pre[p][0] && lo <= pre[p][1]) c[p]++;
    };
    for (let i = 0; i < X.n; i++) {
      if (q.length) { const h = X.hay[i]; let m = true; for (const t of q) if (h.indexOf(t) < 0) { m = false; break; } if (!m) continue; }
      let bad = -1, nb = 0;
      for (let j = 0; j < L.length; j++) {
        const l = L[j];
        let p;
        if (l.t === 0) p = l.ok[l.code[i]];
        else { const lo = l.lo[i]; p = lo === U ? l.u : (l.hi[i] >= l.a && lo <= l.b); }
        if (!p) { nb++; bad = j; if (nb > 1) break; }
      }
      if (nb > 1) continue;
      if (nb === 0) { res.push(i); for (const k of FK) add(k, i); } else add(L[bad].k, i);
    }
    const key = { name: i => X.ord[i], keys: i => { const v = X.f.keys.lo[i]; return v === U ? 1e9 : v; },
      'keys-desc': i => { const v = X.f.keys.hi[i]; return v === U ? 1e9 : -v; },
      year: i => { const v = X.f.year.hi[i]; return v === U ? 1e9 : -v; } }[S.sort];
    if (key) res.sort((a, b) => key(a) - key(b) || a - b);
    list(); paint(); applied(); url();
  }

  // ---------------------------------------------------------------- Darstellung
  function summ(i) {
    const p = [], sp = vals('split', i)[0];
    if (sp) p.push(C.SL[sp] || lab('split', sp));
    const f = X.f.keys;
    if (f && f.lo[i] !== U) p.push((f.lo[i] === f.hi[i] ? f.lo[i] : f.lo[i] + '–' + f.hi[i]) + ' keys');
    const st = vals('stagger', i); if (st.length) p.push(lab('stagger', st[0]));
    const sw = vals('switch_interface', i); if (sw.length) p.push(sw.slice(0, 2).map(v => lab('switch_interface', v)).join('/'));
    const w = vals('wireless', i)[0]; if (w === 'yes') p.push('Wireless'); else if (w === 'optional') p.push('Wireless optional');
    const pt = vals('pointing_device_type', i);
    if (pt.length) p.push(pt.map(v => lab('pointing_device_type', v)).join('/'));
    else if (['yes', 'optional'].includes(vals('pointing_device', i)[0])) p.push('Pointing device');
    const fw = vals('firmware', i); if (fw.length) p.push(fw.slice(0, 3).map(v => lab('firmware', v)).join('/'));
    return p.join(' · ');
  }
  function row(i) {
    const s = X.slug[i], m = maker(X, i);
    return '<li><a href="k/' + s + '.html" data-s="' + s + '"><b>' + esc(X.name[i]) + '</b>' + (m ? ' <span>' + esc(m) + '</span>' : '') +
      '</a><div class=sp>' + esc(summ(i)) + '</div><span class=sc title="Number of sources">' + X.src[i] + ' src</span></li>';
  }
  function list() {
    const n = res.length;
    $('#ls').innerHTML = n ? res.slice(0, S.lim).map(row).join('') :
      '<li class=empty>No keyboard matches all filters. Remove a filter or include unknown values.</li>';
    $('#mo').hidden = n <= S.lim;
    $('#mo').textContent = 'Show ' + Math.min(50, n - S.lim) + ' more';
    const t = (n === 1 ? ' keyboard' : ' keyboards');
    $('#cnt').innerHTML = '<b>' + fmt(n) + '</b>' + t + (part ? '<small></small>' : '');
    if (part) progress();
    $('#fs').textContent = 'Show ' + fmt(n) + t;
    let a = 0;
    for (const k in S.sel) a += S.sel[k].size;
    for (const k in S.rng) if (S.rng[k].lo != null || S.rng[k].hi != null) a++;
    $('#fb b').textContent = a || '';
  }
  function valCounts(k) {
    const f = X.f[k], c = cc[k], v = new Int32Array(f.v.length);
    for (let code = 1; code < f.k.length; code++) if (c[code]) for (const j of f.k[code]) v[j] += c[code];
    return v;
  }
  function paint() {
    for (const d of $$('#fp .fac')) {
      const k = d.dataset.f, f = X.f[k];
      if (!f) continue;
      const sel = [];
      if (f.t === 'c') {
        const v = valCounts(k);
        for (const inp of $$('input[type=checkbox]', d)) {
          const n = inp.value === '?' ? cc[k][0] : v[X.vi[k].get(inp.value)] || 0;
          setCount(inp, n);
          if (inp.checked) sel.push(lab(k, inp.value));
        }
      } else {
        const pre = FI[k].pre || [], r = S.rng[k] || {};
        $$('button[data-r]', d).forEach((b, p) => {
          const on = r.lo === pre[p][0] && r.hi === pre[p][1];
          b.querySelector('i').textContent = fmt(cc[k][p]);
          b.setAttribute('aria-pressed', on);
          b.disabled = !cc[k][p] && !on;
        });
        const u = $('input[value="?"]', d); if (u) setCount(u, cc[k][pre.length]);
        if (r.lo != null || r.hi != null) sel.push((r.lo ?? '') + '–' + (r.hi ?? ''));
      }
      d.querySelector('summary small').textContent = sel.join(', ');
    }
    for (const b of $$('.qf button')) {
      const s = S.sel[b.dataset.f];
      b.setAttribute('aria-pressed', !!s && b.dataset.v.split(' ').every(v => s.has(v)));
    }
  }
  function setCount(inp, n) {
    const i = inp.closest('label').querySelector('i');
    if (i) i.textContent = fmt(n);
    inp.disabled = !n && !inp.checked;
    inp.closest('label').classList.toggle('off', !n && !inp.checked);
  }
  function applied() {
    const b = [];
    if (S.q) b.push('<button type=button data-q>“' + esc(S.q) + '” ✕</button>');
    for (const k in S.sel) for (const v of S.sel[k])
      b.push('<button type=button data-k="' + k + '" data-v="' + esc(v) + '">' + esc(C.FL[k] + ': ' + lab(k, v)) + ' ✕</button>');
    for (const k in S.rng) {
      const r = S.rng[k];
      if (r.lo != null || r.hi != null) b.push('<button type=button data-k="' + k + '" data-r>' + esc(C.FL[k] + ': ' + (r.lo ?? '') + '–' + (r.hi ?? '')) + ' ✕</button>');
    }
    if (b.length > 1) b.push('<button type=button class=cl data-all>Clear all</button>');
    $('#ap').innerHTML = b.join('');
  }
  // Lange Wertelisten (Hersteller, Lizenzen …): erst die häufigsten, auf Wunsch alle, mit Suchfeld
  function renderAll(k, text) {
    const d = $('#fp .fac[data-f="' + k + '"]'), f = X.f[k], v = valCounts(k), s = S.sel[k] || new Set();
    const t = text ? norm(text) : '';
    const idx = [...f.v.keys()].filter(j => !t || norm(lab(k, f.v[j])).includes(t) || s.has(f.v[j]))
      .sort((a, b) => v[b] - v[a] || lab(k, f.v[a]).localeCompare(lab(k, f.v[b])));
    const li = (val, n, cls) => '<li><label' + (cls ? ' class=' + cls : '') + '><input type=checkbox name="' + k + '" value="' + esc(val) + '"' +
      (s.has(val) ? ' checked' : '') + (!n && !s.has(val) ? ' disabled' : '') + '><span>' + esc(lab(k, val)) + '</span><i>' + fmt(n) + '</i></label></li>';
    $('.vl', d).innerHTML = idx.slice(0, 300).map(j => li(f.v[j], v[j])).join('') + (t ? '' : li('?', cc[k][0], 'unk'));
    const b = $('.sa', d); if (b) b.hidden = true;
  }

  // ---------------------------------------------------------------- Zustand <-> URL und Eingabefelder
  function url(extra) {
    const p = [], st = Object.assign({ kb: new URLSearchParams(location.search).get('kb') }, extra || {});
    if (S.q) p.push('q=' + encodeURIComponent(S.q));
    for (const k in S.sel) if (S.sel[k].size) p.push(k + '=' + [...S.sel[k]].map(encodeURIComponent).join(','));
    for (const k in S.rng) {
      const r = S.rng[k];
      if (r.lo != null || r.hi != null) p.push(k + '=' + (r.lo ?? '') + '-' + (r.hi ?? ''));
      if (r.u) p.push(k + '_u=1');
    }
    if (S.sort !== 'rel') p.push('sort=' + S.sort);
    if (st.kb) p.push('kb=' + encodeURIComponent(st.kb));
    const u = location.pathname + (p.length ? '?' + p.join('&') : '');
    if (extra) return u;
    if (u !== location.pathname + location.search) history.replaceState(history.state, '', u);
  }
  function readURL() {
    S.sel = {}; S.rng = {}; S.q = ''; S.sort = 'rel';
    let kb = null;
    for (const part of location.search.slice(1).split('&')) {
      if (!part) continue;
      const [p, raw = ''] = part.split('='), v = decodeURIComponent(raw.replace(/\+/g, ' '));
      if (p === 'q') S.q = v;
      else if (p === 'sort') S.sort = v;
      else if (p === 'kb') kb = v;
      else if (p.endsWith('_u') && FI[p.slice(0, -2)]) (S.rng[p.slice(0, -2)] ||= {}).u = true;
      else if (FI[p] && FI[p].t === 'r') {
        const m = /^(\d*)-(\d*)$/.exec(v);
        if (m) Object.assign(S.rng[p] ||= {}, { lo: m[1] ? +m[1] : null, hi: m[2] ? +m[2] : null });
      } else if (FI[p]) S.sel[p] = new Set(raw.split(',').map(decodeURIComponent));
    }
    return kb;
  }
  const hasState = () => S.q || S.sort !== 'rel' || Object.keys(S.sel).length || Object.keys(S.rng).length;
  function sync() {
    $('#q').value = S.q;
    $('#so').value = S.sort;
    for (const inp of $$('#fp input[type=checkbox]')) {
      const k = inp.name;
      inp.checked = FI[k].t === 'r' ? !!(S.rng[k] && S.rng[k].u) : !!(S.sel[k] && S.sel[k].has(inp.value));
    }
    for (const inp of $$('#fp input[type=number]')) {
      const r = S.rng[inp.name] || {};
      inp.value = r[inp.dataset.b] ?? '';
    }
    // gewählte Werte, die nicht vorgerendert sind (z. B. seltene Hersteller): ganze Liste zeigen
    if (X) for (const k in S.sel) for (const v of S.sel[k])
      if (!$('#fp input[name="' + k + '"][value="' + CSS.escape(v) + '"]') && X.f[k]) { renderAll(k); break; }
  }

  // ---------------------------------------------------------------- Ereignisse
  let tmr;
  const later = (fn, ms) => { clearTimeout(tmr); tmr = setTimeout(fn, ms); };
  const fp = $('#fp');
  fp.addEventListener('change', e => {
    const t = e.target;
    if (t.type !== 'checkbox') return;
    const k = t.name;
    if (FI[k].t === 'r') (S.rng[k] ||= {}).u = t.checked;
    else {
      const s = S.sel[k] ||= new Set();
      t.checked ? s.add(t.value) : s.delete(t.value);
      if (!s.size) delete S.sel[k];
    }
    S.lim = 50; run();
  });
  fp.addEventListener('input', e => {
    const t = e.target;
    if (t.type === 'number') later(() => {
      const r = S.rng[t.name] ||= {}, v = t.value.trim();
      r[t.dataset.b] = v === '' ? null : +v;
      S.lim = 50; run();
    }, 400);
    else if (t.classList.contains('fq')) { if (X) renderAll(t.dataset.f, t.value); }
  });
  fp.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    if (b.dataset.r !== undefined && b.dataset.f) {
      const k = b.dataset.f, [lo, hi] = FI[k].pre[+b.dataset.r], r = S.rng[k] ||= {};
      const on = r.lo === lo && r.hi === hi;
      r.lo = on ? null : lo; r.hi = on ? null : hi;
      sync(); S.lim = 50; run();
    } else if (b.classList.contains('sa')) { if (X) renderAll(b.dataset.f); else { pend = true; run(); } }
  });
  $('.qf').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    const k = b.dataset.f, vs = b.dataset.v.split(' '), s = S.sel[k] ||= new Set();
    const on = vs.every(v => s.has(v));
    vs.forEach(v => on ? s.delete(v) : s.add(v));
    if (!s.size) delete S.sel[k];
    sync(); S.lim = 50; run();
  });
  $('#ap').addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    const k = b.dataset.k;
    if (b.dataset.all !== undefined) { S.sel = {}; S.rng = {}; S.q = ''; }
    else if (b.dataset.q !== undefined) S.q = '';
    else if (b.dataset.r !== undefined) delete S.rng[k];
    else { S.sel[k].delete(b.dataset.v); if (!S.sel[k].size) delete S.sel[k]; }
    sync(); S.lim = 50; run();
  });
  $('#fc').addEventListener('click', () => { S.sel = {}; S.rng = {}; sync(); S.lim = 50; run(); });
  $('#q').addEventListener('input', e => later(() => { S.q = e.target.value; S.lim = 50; run(); }, 200));
  $('#so').addEventListener('change', e => { S.sort = e.target.value; run(); });
  $('#mo').addEventListener('click', () => { S.lim += 50; if (X) list(); else run(); });

  const root = D.documentElement;
  const panel = open => {
    root.classList.toggle('fp-open', open);
    $('#fb').setAttribute('aria-expanded', open);
    (open ? $('#fx') : $('#fb')).focus();
  };
  $('#fb').addEventListener('click', () => panel(true));
  $('#fx').addEventListener('click', () => panel(false));
  $('#fs').addEventListener('click', () => panel(false));
  D.addEventListener('keydown', e => {
    if (e.key === 'Escape' && root.classList.contains('fp-open')) panel(false);
    if (e.key === '/' && !/INPUT|SELECT|TEXTAREA/.test(D.activeElement.tagName)) { e.preventDefault(); $('#q').focus(); }
  });

  // Detailansicht: lädt die statische Seite k/<slug>.html und zeigt deren <article> im Dialog
  const dv = $('#dv'), dvb = $('#dvb');
  function detail(s, push) {
    if (push) history.pushState({ kb: s }, '', url({ kb: s }));
    $('#dl').href = 'k/' + s + '.html';
    dvb.innerHTML = '<p class=note>Loading…</p>';
    if (!dv.open) dv.showModal();
    fetch('k/' + s + '.html').then(r => { if (!r.ok) throw 0; return r.text(); }).then(t => {
      const a = new DOMParser().parseFromString(t, 'text/html').querySelector('article');
      dvb.replaceChildren(a);
      dv.scrollTop = 0;
    }).catch(() => { location.href = 'k/' + s + '.html'; });
  }
  function closeDetail() {
    if (history.state && history.state.kb) history.back();
    else { dv.close(); history.replaceState(null, '', url({ kb: null })); }
  }
  $('#ls').addEventListener('click', e => {
    const a = e.target.closest('a[data-s]');
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey || e.button) return;
    e.preventDefault();
    detail(a.dataset.s, true);
  });
  $('#dx').addEventListener('click', closeDetail);
  dv.addEventListener('cancel', e => { e.preventDefault(); closeDetail(); });
  addEventListener('popstate', () => {
    const before = url({ kb: null }), kb = readURL();
    if (kb) detail(kb, false); else if (dv.open) dv.close();
    if (url({ kb: null }) !== before) { sync(); run(); }
  });

  // Farbschema: Auto (System) -> Hell -> Dunkel
  const th = $('#th'), modes = ['auto', 'light', 'dark'];
  const showTheme = () => { const m = root.dataset.theme || 'auto'; th.textContent = '◐ ' + m[0].toUpperCase() + m.slice(1); th.setAttribute('aria-label', 'Color theme: ' + m); };
  th.addEventListener('click', () => {
    const m = modes[(modes.indexOf(root.dataset.theme || 'auto') + 1) % 3];
    root.dataset.theme = m;
    try { m === 'auto' ? localStorage.removeItem('theme') : localStorage.setItem('theme', m); } catch (e) { /* privat */ }
    showTheme();
  });
  showTheme();

  // Start
  const kb = readURL();
  if (hasState()) { sync(); run(); }
  if (kb) detail(kb, false);
  load();
  // frühe Klicks (siehe FRUEH_JS in seite_bauen.py) jetzt ausführen
  window.KB = 1;
  (window.Q || []).forEach(t => { t.style.opacity = ''; t.click(); });
})();
