// Launcher netsys-academy : onglets, topologie éditable, quiz, terminaux, outils
let sid = SID;
let topo = { nodes: [], links: [] };
const $ = (id) => document.getElementById(id);

async function api(path, body) {
  const r = await fetch(path, {
    method: "POST", headers: { "content-type": "application/json" },
    body: JSON.stringify(body || {}), credentials: "same-origin",
  });
  if (!r.ok) throw new Error((await r.json()).detail || r.status);
  return r.json();
}

function setButtons() {
  if (MODE === "drills") return;
  if ($("launch")) $("launch").disabled = !!sid;
  if ($("destroy")) $("destroy").disabled = !sid;
  if ($("session-state")) $("session-state").textContent = sid
    ? `session ${sid} active — clique un nœud de la topologie pour ouvrir son terminal`
    : "labo non lancé — clique « ▶ Lancer le labo »";
  const tb = $("topo-edit-btn");
  if (tb) tb.disabled = !sid;
  document.querySelectorAll(".needs-session").forEach((e) => (e.hidden = !sid));
}

// --- onglets Cours / Quiz / Labo / Scénario
function showTab(name) {
  document.querySelectorAll(".tabs button").forEach((b) =>
    b.classList.toggle("on", b.dataset.tab === name));
  document.querySelectorAll(".tab").forEach((s) =>
    s.hidden = s.id !== "tab-" + name);
  if (name === "quiz" && !quizLoaded && MODE !== "drills") loadQuiz();
}

// --- topologie interactive : déplacement, icônes, câblage à la souris
let tpos = {};
let wiring = false, wireFrom = null, drag = null, svgBound = false;

const devType = (nd) => nd.kind === "frr" ? "router"
  : /^sw/.test(nd.name) ? "switch"
  : /^(h|pc|cli|work)/.test(nd.name) ? "pc" : "server";

const ICONS = {
  pc: `<rect x="-17" y="-15" width="34" height="23" rx="2"></rect>
       <line x1="0" y1="8" x2="0" y2="13"></line><line x1="-9" y1="13" x2="9" y2="13"></line>`,
  server: `<rect x="-13" y="-20" width="26" height="38" rx="3"></rect>
       <line x1="-8" y1="-12" x2="8" y2="-12"></line><line x1="-8" y1="-4" x2="8" y2="-4"></line>
       <circle cx="0" cy="9" r="3"></circle>`,
  switch: `<rect x="-24" y="-9" width="48" height="18" rx="3"></rect>` +
       [-18, -12, -6, 0, 6, 12].map((x) => `<line x1="${x}" y1="-3" x2="${x}" y2="3"></line>`).join(""),
  router: `<rect x="-20" y="-12" width="40" height="24" rx="8"></rect>
       <path d="M-11 0 H9 M4 -5 L9 0 L4 5" fill="none"></path>`,
};

function layoutPos(nodes) {
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem("netsys-pos-" + LAB)) || {}; } catch { /* neuf */ }
  const n = nodes.length, p = {};
  nodes.forEach((nd, i) => {
    if (saved[nd.name]) { p[nd.name] = saved[nd.name]; return; }
    const a = (2 * Math.PI * i) / Math.max(n, 1) - Math.PI / 2;
    p[nd.name] = n === 1 ? { x: 380, y: 160 }
      : { x: 380 + (n > 6 ? 320 : 280) * Math.cos(a), y: 160 + (n > 6 ? 130 : 115) * Math.sin(a) };
  });
  return p;
}

function svgPoint(e) {
  const svg = $("topo"), p = svg.createSVGPoint();
  p.x = e.clientX; p.y = e.clientY;
  const q = p.matrixTransform(svg.getScreenCTM().inverse());
  return { x: Math.round(q.x), y: Math.round(q.y) };
}

function drawTopo() {
  const svg = $("topo");
  tpos = layoutPos(topo.nodes);
  svg.innerHTML =
    topo.links.map((l) => `<line data-a="${l.a}" data-b="${l.b}" x1="${tpos[l.a].x}" y1="${tpos[l.a].y}" x2="${tpos[l.b].x}" y2="${tpos[l.b].y}" class="link"></line>`).join("") +
    topo.nodes.map((nd) => `<g class="tnode ${nd.kind} ${devType(nd)}" data-node="${nd.name}" transform="translate(${tpos[nd.name].x},${tpos[nd.name].y})">
      ${ICONS[devType(nd)]}<text y="30">${nd.name}</text><title>${devType(nd)} · ${nd.kind} · ${nd.image} — glisser pour déplacer</title></g>`).join("");
  if (!svgBound) {
    svgBound = true;
    svg.addEventListener("pointerdown", (e) => {
      const g = e.target.closest(".tnode");
      if (!g) return;
      e.preventDefault();
      g.setPointerCapture(e.pointerId);
      drag = { g, name: g.dataset.node, moved: false, start: svgPoint(e), pid: e.pointerId };
    });
    svg.addEventListener("pointermove", (e) => {
      if (!drag || e.pointerId !== drag.pid) return;
      const p = svgPoint(e);
      if (!drag.moved && Math.hypot(p.x - drag.start.x, p.y - drag.start.y) < 6) return;
      drag.moved = true;
      p.x = Math.min(740, Math.max(20, p.x));
      p.y = Math.min(300, Math.max(20, p.y));
      tpos[drag.name] = p;
      drag.g.setAttribute("transform", `translate(${p.x},${p.y})`);
      svg.querySelectorAll(`line[data-a="${drag.name}"], line[data-b="${drag.name}"]`).forEach((ln) => {
        const side = ln.dataset.a === drag.name ? "a" : "b";
        ln.setAttribute("x" + (side === "a" ? "1" : "2"), p.x);
        ln.setAttribute("y" + (side === "a" ? "1" : "2"), p.y);
      });
    });
    const finish = (e) => {
      if (!drag || e.pointerId !== drag.pid) return;
      if (drag.moved) localStorage.setItem("netsys-pos-" + LAB, JSON.stringify(tpos));
      else nodeClick(drag.name);
      drag = null;
    };
    svg.addEventListener("pointerup", finish);
    svg.addEventListener("pointercancel", () => (drag = null));
  }
}

function nodeClick(name) {
  if (!wiring) { openTerm(name); return; }
  if (!wireFrom) {
    wireFrom = name;
    $("topo-msg").textContent = `câble depuis ${name} — clique le nœud d'arrivée`;
    return;
  }
  if (name !== wireFrom) {
    const used = (n) => topo.links.filter((l) => (l.a === n ? l.a_if : l.b === n ? l.b_if : "")).filter(Boolean);
    const next = (n) => { const u = used(n); let i = 1; while (u.includes("eth" + i)) i++; return "eth" + i; };
    const fa = next(wireFrom), fb = next(name);
    topo.links.push({ a: wireFrom, b: name, a_if: fa, b_if: fb });
    $("topo-msg").textContent = `câblé : ${wireFrom}:${fa} ↔ ${name}:${fb} — puis « Appliquer »`;
    renderTopoEditor();
  }
  wiring = wireFrom = null;
  $("topo-wire").classList.remove("on");
}

// --- topologie SVG : fetch + rendu
async function renderTopo() {
  const svg = $("topo");
  if (!svg) return;
  topo = await (await fetch(`/api/topo/${LAB}${sid ? "?sid=" + sid : ""}`,
    { credentials: "same-origin" })).json();
  if (!topo.nodes.length) return;
  drawTopo();
  renderTopoEditor();
}

// --- éditeur de topologie (modifier = recréer le lab à zéro)
function renderTopoEditor() {
  const box = $("node-list");
  if (!box) return;
  box.innerHTML = topo.nodes.map((nd, i) =>
    `<div class="row">${nd.name} <small>${nd.kind} · ${nd.image}</small>
     <button class="mini" data-i="${i}" title="supprimer">✕</button></div>`).join("");
  box.querySelectorAll("button").forEach((b) => (b.onclick = () => {
    const i = +b.dataset.i, rm = topo.nodes[i];
    topo.links = topo.links.filter((l) => l.a !== rm.name && l.b !== rm.name);
    topo.nodes.splice(i, 1);
    renderTopoEditor();
    drawTopo();
  }));
  $("link-list").innerHTML = topo.links.map((l, i) =>
    `<div class="row">${l.a}:${l.a_if} ↔ ${l.b}:${l.b_if}
     <button class="mini" data-k="${i}" title="supprimer">✕</button></div>`).join("");
  $("link-list").querySelectorAll("button").forEach((b) =>
    (b.onclick = () => { topo.links.splice(+b.dataset.k, 1); renderTopoEditor(); drawTopo(); }));
  const opts = topo.nodes.map((nd) => `<option>${nd.name}</option>`).join("");
  ["ln-a", "ln-b"].forEach((id) => { $(id).innerHTML = opts; });
  if (sid) {
    ["ed-node", "tool-node"].forEach((id) => {
      const e = $(id); if (!e) return;
      const v = e.value; e.innerHTML = opts; if (topo.nodes.some((nd) => nd.name === v)) e.value = v;
    });
  }
}

async function applyTopo() {
  if (!confirm("Recréer le labo avec cette topologie ?\nLes machines seront remises à ZÉRO (config perdue).")) return;
  $("topo-msg").textContent = "redéploiement (30-60 s)…";
  try {
    const r = await api("/api/session/topo", { sid, nodes: topo.nodes, links: topo.links });
    terminals.forEach((t) => t.dispose());
    terminals.clear();
    document.querySelectorAll(".term-wrap").forEach((w) => w.remove());
    await renderTopo();
    $("topo-msg").textContent = "topologie appliquée ✓" +
      (r.warnings.length ? " — " + r.warnings.join("; ") : "");
  } catch (e) {
    $("topo-msg").textContent = "erreur: " + e.message;
  }
}

async function launch() {
  $("session-state").textContent = "déploiement en cours (30-60 s)…";
  const r = await api("/api/session/launch", { lab: LAB });
  sid = r.session.id;
  setButtons();
  await renderTopo();
  $("session-state").textContent = `session ${sid} active — clique un nœud de la topologie pour ouvrir son terminal`;
}

async function destroy() {
  await api("/api/session/destroy", { sid });
  sid = null;
  terminals.forEach((t) => t.dispose());
  terminals.clear();
  document.querySelectorAll(".term-wrap").forEach((w) => w.remove());
  setButtons();
  await renderTopo();
}

// --- vérification avec cartes de résultats + hints
function esc(s) {
  return String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
}

async function verify() {
  const out = $("results");
  out.hidden = false;
  out.innerHTML = "<p>vérification…</p>";
  try {
    if (MODE === "drills" && !sid) sid = (await api("/api/session/launch", { lab: LAB })).session.id;
    const body = { sid };
    if (MODE === "drills") body.answers = Object.fromEntries(new FormData($("drill-form")));
    const s = await api("/api/session/verify", body);
    const pct = Math.round((100 * s.score) / (s.max || 1));
    out.innerHTML =
      `<h3>score ${s.score}/${s.max} (${pct} %)</h3>
       <div class="bar"><div class="fill" style="width:${pct}%"></div></div>` +
      (pct === 100 ? "<p class='congrats'>🎉 Parfait, tout est validé !</p>" : "") +
      s.checks.map((c) => `<div class="chk ${c.ok ? "pass" : "fail"}">
        <span class="badge">${c.ok ? "PASS" : "FAIL"}</span>
        <strong>${esc(c.id)}</strong> <small>+${c.points} pt(s)</small>
        <details><summary>détail</summary><pre>${esc(c.detail)}</pre></details>
        ${c.hint ? `<p class="hint">💡 ${esc(c.hint)}</p>` : ""}
      </div>`).join("") +
      `<p class="push">note enregistrée${s.push.pushed ? " et poussée dans Moodle ✓" : ""}${s.push.moodle_error ? " (Moodle: " + esc(s.push.moodle_error) + ")" : ""}</p>`;
  } catch (e) {
    out.innerHTML = "<p class='hint'>erreur: " + esc(e.message) + "</p>";
  }
}

// --- quiz
let quizLoaded = false;
async function loadQuiz() {
  quizLoaded = true;
  const box = $("quiz-box");
  const q = await (await fetch(`/api/quiz/${LAB}`, { credentials: "same-origin" })).json();
  box.innerHTML = q.questions.map((qq, i) =>
    `<fieldset class="qq"><legend>${i + 1}. ${esc(qq.q)}</legend>` +
    qq.choices.map((c, j) =>
      `<label><input type="radio" name="q${i}" value="${j}"> ${esc(c)}</label>`).join("") +
    `</fieldset>`).join("") + "<button id='quiz-submit'>Corriger</button><div id='quiz-score'></div>";
  $("quiz-submit").onclick = submitQuiz;
}

async function submitQuiz() {
  const n = document.querySelectorAll(".qq").length;
  const answers = Array.from({ length: n },
    (_, i) => document.querySelector(`input[name=q${i}]:checked`)?.value ?? -1).map(Number);
  if (answers.includes(-1) &&
      !confirm("Des questions sont sans réponse. Corriger quand même ?")) return;
  const s = await api(`/api/quiz/${LAB}`, { answers });
  document.querySelectorAll(".qq").forEach((fs, i) => {
    const q = s.questions[i];
    fs.classList.add(q.ok ? "ok" : "bad");
    fs.querySelectorAll("label").forEach((lb, j) => { if (j === q.correct) lb.classList.add("good"); });
    const d = document.createElement("p");
    d.className = "expl";
    d.textContent = (q.ok ? "✓ " : "✗ ") + q.expl;
    fs.append(d);
  });
  const pct = Math.round((100 * s.score) / (s.max || 1));
  $("quiz-score").innerHTML = `<h3>${pct}/100 ${pct >= 80 ? "🎉" : pct >= 50 ? "👍" : "📖 relis le cours"}</h3>`;
}

// --- outil « commande rapide » dans un nœud
async function runTool() {
  const cmd = $("tool-cmd").value.trim();
  if (!cmd || !sid) return;
  $("tool-out").textContent = "$ " + cmd + "\n…";
  const r = await api("/api/run", { sid, node: $("tool-node").value, cmd });
  $("tool-out").textContent = `$ ${cmd}\n[rc=${r.rc}]\n${r.out}`;
}

// --- éditeur de configuration (fichiers dans les nœuds via docker exec)
async function edLoad() {
  const st = $("ed-state");
  st.textContent = "lecture…";
  const r = await fetch(`/api/file?sid=${sid}&node=${$("ed-node").value}&path=${encodeURIComponent($("ed-path").value)}`);
  if (!r.ok) { st.textContent = "erreur: " + (await r.json()).detail; return; }
  $("ed-body").value = (await r.json()).content;
  st.textContent = `${$("ed-node").value}:${$("ed-path").value}`;
}
async function edSave() {
  const st = $("ed-state");
  const r = await fetch("/api/file", {
    method: "POST", headers: { "content-type": "application/json" }, credentials: "same-origin",
    body: JSON.stringify({ sid, node: $("ed-node").value, path: $("ed-path").value, content: $("ed-body").value }),
  });
  st.textContent = r.ok ? "enregistré ✓" : "erreur: " + (await r.json()).detail;
}

// --- terminaux dynamiques
const terminals = new Map();

function openTerm(node) {
  if (terminals.has(node)) return;
  if (!sid) {
    $("session-state").textContent = "⚠️ Lance d'abord le labo avec « ▶ Lancer le labo », puis clique à nouveau le nœud.";
    showTab("labo");
    return;
  }
  const wrap = document.createElement("div");
  wrap.className = "term-wrap";
  wrap.innerHTML = `<div class="row"><strong>${node}</strong>
    <button class="mini term-close">fermer</button></div><div class="term"></div>`;
  $("terms").append(wrap);
  wrap.scrollIntoView({ block: "nearest" });
  wrap.querySelector(".term-close").onclick = () => {
    terminals.get(node)?.dispose();
    terminals.delete(node);
    wrap.remove();
  };
  const term = new Terminal({ fontSize: 13, theme: { background: "#0b1220" } });
  term.open(wrap.querySelector(".term"));
  term.writeln("\x1b[36mTerminal " + node + " — tape tes commandes ici (ex: ip -br a)\x1b[0m");
  term.focus();
  const ws = new WebSocket(
    `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws/term/${sid}/${node}`);
  ws.binaryType = "arraybuffer"; // sans ça ev.data arrive en Blob et xterm n'affiche rien
  ws.onmessage = (ev) =>
    ev.data instanceof ArrayBuffer ? term.write(new Uint8Array(ev.data)) : term.write(ev.data);
  ws.onclose = () => term.write("\r\n\x1b[31m[terminal fermé — relance le labo si la session a expiré]\x1b[0m\r\n");
  term.onData((d) => ws.readyState === 1 && ws.send(JSON.stringify({ type: "input", data: d })));
  const sendSize = () =>
    ws.readyState === 1 && ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
  term.onResize(sendSize);
  sendSize();
  terminals.set(node, { dispose: () => { ws.close(); term.dispose(); } });
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".tabs button").forEach((b) =>
    (b.onclick = () => showTab(b.dataset.tab)));
  showTab(MODE === "drills" ? "quiz" : "cours");
  setButtons();
  renderTopo();
  $("verify").onclick = verify;
  $("go-pratique").onclick = () => showTab(MODE === "drills" ? "quiz" : "labo");
  $("go-scenario").onclick = () => showTab("scenario");
  if ($("launch")) {
    $("launch").onclick = () => launch().catch((e) => { setButtons(); alert(e.message); });
    $("destroy").onclick = () => destroy().catch((e) => alert(e.message));
    $("topo-edit-btn").onclick = () => {
      const e = $("topo-edit");
      e.hidden = !e.hidden;
      $("topo-edit-btn").textContent = e.hidden ? "Modifier la topologie" : "Masquer l'éditeur";
    };
    $("topo-add-node").onclick = () => {
      const name = $("nn-name").value.trim();
      if (!/^[a-z][a-z0-9_-]{0,20}$/.test(name)) { $("topo-msg").textContent = "nom de nœud invalide (ex: sw3, h10)"; return; }
      if (topo.nodes.some((n) => n.name === name)) { $("topo-msg").textContent = "nom déjà pris"; return; }
      topo.nodes.push({ name, kind: $("nn-kind").value, image: $("nn-image").value });
      $("topo-msg").textContent = "";
      renderTopoEditor();
      drawTopo();
    };
    $("topo-add-link").onclick = () => {      const a = $("ln-a").value, b = $("ln-b").value;
      const ai = $("ln-a-if").value.trim(), bi = $("ln-b-if").value.trim();
      if (a === b || !ai || !bi) { $("topo-msg").textContent = "lien invalide (2 nœuds différents + interfaces)"; return; }
      topo.links.push({ a, b, a_if: ai, b_if: bi });
      $("topo-msg").textContent = "";
      renderTopoEditor();
      drawTopo();
    };
    $("topo-wire").onclick = () => {
      wiring = !wiring; wireFrom = null;
      $("topo-wire").classList.toggle("on", wiring);
      $("topo-msg").textContent = wiring ? "🔌 clique le nœud de départ, puis le nœud d'arrivée" : "";
    };
    $("topo-apply").onclick = () => applyTopo().catch((e) => $("topo-msg").textContent = "erreur: " + e.message);
    $("tool-run").onclick = runTool;
    $("tool-cmd").addEventListener("keydown", (e) => { if (e.key === "Enter") runTool(); });
    $("ed-load").onclick = edLoad;
    $("ed-save").onclick = edSave;
  }
});
