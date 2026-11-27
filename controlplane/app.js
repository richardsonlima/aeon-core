// Æon Control Plane. Vanilla ES module, no build step, no third-party requests.
// All server data reaches the DOM through textContent or setAttribute, never as markup.

import { t, initLang, setLang, getLang, applyStatic } from "./i18n.js";

const TOKEN_KEY = "aeon.token";
const MAX_ROWS = 500;
const $ = (sel, root = document) => root.querySelector(sel);

// -- tiny DOM helpers ---------------------------------------------------------------------

function h(tag, attrs, ...kids) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
    else node.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) {
    if (kid === null || kid === undefined || kid === false) continue;
    node.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
  }
  return node;
}

function clear(node) { node.replaceChildren(); }

let uid = 0;
function field(labelText, input, hint) {
  const id = `f${++uid}`;
  input.id = id;
  const wrap = h("div", {}, h("label", { for: id, text: labelText }), input);
  if (hint) {
    const hid = `${id}-h`;
    input.setAttribute("aria-describedby", hid);
    wrap.append(h("p", { class: "hint", id: hid, text: hint }));
  }
  return wrap;
}

const fmt = {
  pct: (x) => (x === null || x === undefined ? t("cp_na") : `${(x * 100).toFixed(1)}%`),
  ci: (c) => (Array.isArray(c) ? `${t("cp_ci")} [${(c[0] * 100).toFixed(1)}%, ${(c[1] * 100).toFixed(1)}%]` : ""),
  num: (x, d = 2) => (x === null || x === undefined ? t("cp_na") : Number(x).toFixed(d).replace(/\.?0+$/, "")),
  time: (s) => {
    if (!s) return "";
    const d = new Date(s);
    return Number.isNaN(d.getTime()) ? String(s) : d.toLocaleString(getLang() === "pt" ? "pt-BR" : "en-GB");
  },
  uptime: (s) => {
    const n = Math.round(Number(s) || 0);
    return `${Math.floor(n / 3600)}h ${Math.floor((n % 3600) / 60)}m ${n % 60}s`;
  },
};

// -- token and API ------------------------------------------------------------------------

let token = "";

function loadToken() {
  const m = /(?:^|[#&])token=([^&]+)/.exec(location.hash);
  if (m) {
    token = decodeURIComponent(m[1]);
    try { sessionStorage.setItem(TOKEN_KEY, token); } catch (_e) { /* ignore */ }
    const rest = location.hash.replace(/(^#|&)token=[^&]*/, "").replace(/^&/, "");
    history.replaceState(null, "", `${location.pathname}${location.search}${rest ? `#${rest}` : ""}`);
    return;
  }
  try { token = sessionStorage.getItem(TOKEN_KEY) || ""; } catch (_e) { token = ""; }
}

function clearToken() {
  token = "";
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (_e) { /* ignore */ }
}

let tokenWaiters = [];
function askToken(rejected) {
  const dlg = $("#token-dialog");
  $("#token-error").textContent = rejected ? t("token_rejected") : "";
  return new Promise((resolve) => {
    tokenWaiters.push(resolve);
    if (dlg.open) return;
    $("#token-input").value = "";
    dlg.showModal();
    $("#token-input").focus();
  });
}

class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status; }
}

async function api(path, { method = "GET", body, raw = false } = {}) {
  if (!token) await askToken(false);
  const headers = { Authorization: `Bearer ${token}` };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  let res;
  try {
    res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  } catch (_e) {
    throw new ApiError(0, t("net_error"));
  }
  if (res.status === 401) {
    clearToken();
    await askToken(true);
    return api(path, { method, body, raw });
  }
  if (raw) return res;
  let data = null;
  try { data = await res.json(); } catch (_e) { data = null; }
  if (!res.ok) {
    const detail = data && data.detail ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : res.statusText;
    throw new ApiError(res.status, detail);
  }
  return { status: res.status, data };
}

function showError(err) {
  const msg = err instanceof Error ? err.message : String(err);
  $("#alerts").textContent = `${t("error_prefix")}: ${msg}`;
}
function clearError() { $("#alerts").textContent = ""; }
async function guard(fn) {
  try { clearError(); return await fn(); } catch (e) { showError(e); return undefined; }
}

// -- confirm dialog -----------------------------------------------------------------------

function confirmDialog(title, body) {
  const dlg = $("#confirm-dialog");
  $("#confirm-title").textContent = title;
  $("#confirm-body").textContent = body;
  return new Promise((resolve) => {
    const done = (ok) => {
      dlg.removeEventListener("close", onClose);
      resolve(ok);
    };
    const onClose = () => done(dlg.returnValue === "yes");
    dlg.returnValue = "no";
    dlg.addEventListener("close", onClose);
    dlg.showModal();
    $("#confirm-no").focus();
  });
}

// -- router -------------------------------------------------------------------------------

let cleanup = null;
const pages = {};

function routeName() {
  const m = /^#\/([a-z]+)/.exec(location.hash);
  return m && pages[m[1]] ? m[1] : "overview";
}

async function render() {
  if (cleanup) { cleanup(); cleanup = null; }
  const name = routeName();
  for (const a of document.querySelectorAll("nav a")) {
    if (a.dataset.route === name) a.setAttribute("aria-current", "page");
    else a.removeAttribute("aria-current");
  }
  const main = $("#main");
  clear(main);
  main.append(h("p", { class: "muted", text: `${t("loading")}...` }));
  clearError();
  const root = h("div");
  try {
    cleanup = (await pages[name](root)) || null;
  } catch (e) {
    showError(e);
  }
  clear(main);
  main.append(root);
  const h1 = $("h1", root);
  if (h1) { h1.setAttribute("tabindex", "-1"); h1.focus({ preventScroll: true }); }
}

function rerender() { applyChrome(); render(); }

function applyChrome() {
  applyStatic();
  document.title = `${t("brand_sub")} | Æon`;
  $("#lang-btn").setAttribute("lang", getLang() === "pt" ? "en" : "pt-BR");
}

// -- shared widgets -----------------------------------------------------------------------

function verdictBadge(level) {
  return h("span", { class: `badge v-${level}`, text: level });
}

function kvList(pairs) {
  const dl = h("dl", { class: "kv" });
  for (const [k, v] of pairs) dl.append(h("dt", { text: k }), h("dd", { text: v }));
  return dl;
}

function table(caption, headCells, numericCols = []) {
  const thead = h("tr", {}, headCells.map((c, i) => h("th", { scope: "col", class: numericCols.includes(i) ? "num" : null, text: c })));
  const tbody = h("tbody");
  const tbl = h("table", {}, h("caption", { text: caption }), h("thead", {}, thead), tbody);
  return { wrap: h("div", { class: "tablewrap" }, tbl), tbody };
}

// -- Overview -----------------------------------------------------------------------------

pages.overview = async (root) => {
  root.append(h("h1", { text: t("ov_title") }));
  const live = h("div", { "aria-live": "polite", class: "sr", id: "ov-live" });
  const top = h("div", { class: "grid" });
  const agentsBox = h("section", { "aria-labelledby": "ov-agents-h" }, h("h2", { id: "ov-agents-h", text: t("ov_agents") }));
  const agentsList = h("div", { class: "grid" });
  agentsBox.append(agentsList);
  const bottom = h("div", { class: "grid" });
  root.append(live, top, agentsBox, bottom);

  // mode card
  const modeVal = h("p", { class: "big" });
  const modeDesc = h("p", { class: "muted" });
  const modeBtn = h("button", { type: "button", class: "btn" });
  const modeCard = h("section", { class: "card", "aria-labelledby": "ov-mode-h" }, h("h2", { id: "ov-mode-h", text: t("ov_mode") }), modeVal, modeDesc, modeBtn);
  // kill switch card
  const killState = h("p", { class: "banner" });
  const killReason = h("input", { type: "text", maxlength: "500", autocomplete: "off" });
  const killBtn = h("button", { type: "button", class: "btn" });
  const killWrap = h("div", {}, field(t("ov_kill_reason"), killReason));
  const killCard = h("section", { class: "card", "aria-labelledby": "ov-kill-h" }, h("h2", { id: "ov-kill-h", text: t("ov_kill") }), killState, killWrap, h("div", { class: "row" }, killBtn));
  // audit and runtime cards
  const auditBody = h("div");
  const auditCard = h("section", { class: "card", "aria-labelledby": "ov-audit-h" }, h("h2", { id: "ov-audit-h", text: t("ov_audit") }), auditBody);
  const countersBody = h("div");
  const countersCard = h("section", { class: "card", "aria-labelledby": "ov-count-h" }, h("h2", { id: "ov-count-h", text: t("ov_counters") }), countersBody);
  const runtimeBody = h("div");
  const runtimeCard = h("section", { class: "card", "aria-labelledby": "ov-rt-h" }, h("h2", { id: "ov-rt-h", text: t("ov_runtime") }), runtimeBody);
  top.append(modeCard, killCard);
  bottom.append(auditCard, countersCard, runtimeCard);

  let current = null;
  modeBtn.addEventListener("click", () => guard(async () => {
    const toEnforce = current.mode !== "enforce";
    const ok = toEnforce
      ? await confirmDialog(t("ov_confirm_enforce_title"), t("ov_confirm_enforce_body"))
      : await confirmDialog(t("ov_confirm_shadow_title"), t("ov_confirm_shadow_body"));
    if (!ok) return;
    const { data } = await api("/v1/mode", { method: "POST", body: { mode: toEnforce ? "enforce" : "shadow" } });
    live.textContent = `${t("ov_mode_changed")} ${data.mode}`;
    await refresh();
  }));
  killBtn.addEventListener("click", () => guard(async () => {
    const engage = !current.kill_switch.engaged;
    const ok = engage
      ? await confirmDialog(t("ov_confirm_kill_title"), t("ov_confirm_kill_body"))
      : await confirmDialog(t("ov_confirm_release_title"), t("ov_confirm_release_body"));
    if (!ok) return;
    const reason = killReason.value.trim();
    await api("/v1/kill-switch", { method: "POST", body: engage ? { engaged: true, reason: reason || null } : { engaged: false } });
    killReason.value = "";
    await refresh();
  }));

  const cards = new Map();

  function agentCard(name) {
    const title = h("h3", { class: "mono", text: name });
    const state = h("span", { class: "badge" });
    const level = h("span", { class: "badge" });
    const meter = h("div", { class: "meter", role: "meter", "aria-valuemin": "0", "aria-label": `${t("meter_label")} ${name}` });
    const fill = h("div", { class: "meter-fill" });
    const ticks = h("span");
    meter.append(fill, ticks);
    const meterText = h("p", { class: "mono" });
    const calibLabel = h("span", {});
    const calibId = `cal-${++uid}`;
    const calib = h("progress", { id: calibId, "aria-labelledby": `${calibId}-t` });
    const calibText = h("p", { class: "muted", id: `${calibId}-t` });
    const detail = h("p", { class: "muted" });
    const reset = h("button", { type: "button", class: "btn", text: t("ov_reset") });
    reset.addEventListener("click", () => guard(async () => {
      const { data } = await api(`/v1/safe-state/${encodeURIComponent(name)}/reset`, { method: "POST" });
      live.textContent = `${data.released ? t("ov_reset_done") : t("ov_reset_none")} ${name}`;
      await refresh();
    }));
    const el = h("article", { class: "card" }, h("div", { class: "row" }, title, state, level), meter, meterText, calibLabel, calib, calibText, detail, h("div", { class: "row" }, reset));
    return { el, state, level, fill, meter, ticks, meterText, calib, calibText, detail, reset, name };
  }

  function updateAgent(c, safe, b, budget) {
    const inSafe = Boolean(safe);
    c.state.textContent = inSafe ? t("ov_in_safe_state") : t("ov_not_safe_state");
    c.state.className = `badge ${inSafe ? "bad" : "ok"}`;
    c.reset.disabled = !inSafe;
    const lvl = b ? b.level : "GO";
    c.level.textContent = `${t("ov_level")} ${lvl}`;
    c.level.className = `badge v-${lvl}`;
    if (b && budget) {
      const max = budget.block_at || 1;
      const acc = b.accumulated || 0;
      c.fill.style.width = `${Math.min(100, (acc / max) * 100)}%`;
      c.fill.className = `meter-fill lv-${lvl}`;
      c.meter.setAttribute("aria-valuemax", String(max));
      c.meter.setAttribute("aria-valuenow", String(Math.min(acc, max)));
      c.meter.setAttribute("aria-valuetext", `${t("ov_accumulated")} ${fmt.num(acc)}, ${t("ov_alert")} ${budget.alert_at}, ${t("ov_limit")} ${budget.limit_at}, ${t("ov_block")} ${budget.block_at}`);
      c.ticks.replaceChildren();
      for (const at of [budget.alert_at, budget.limit_at]) {
        const tick = h("span", { class: "tick", "aria-hidden": "true" });
        tick.style.left = `${(at / max) * 100}%`;
        c.ticks.append(tick);
      }
      c.meterText.textContent = `${t("ov_accumulated")} ${fmt.num(acc)} | ${t("ov_alert")} ${budget.alert_at} | ${t("ov_limit")} ${budget.limit_at} | ${t("ov_block")} ${budget.block_at}`;
      c.calib.max = budget.baseline_n;
      c.calib.value = Math.min(b.calibration_progress, budget.baseline_n);
      c.calibText.textContent = `${t("ov_calibration")}: ${b.calibration_progress}/${budget.baseline_n} (${b.calibrated ? t("ov_calibrated") : t("ov_calibrating")})`;
      c.detail.textContent = `${t("ov_steps")}: ${b.steps} | ${fmt.num(b.deviation, 3)} | ${b.reason || ""}`;
    } else {
      c.meterText.textContent = "";
      c.calibText.textContent = "";
      c.detail.textContent = safe ? safe.reason : "";
      c.meter.hidden = true;
      c.calib.hidden = true;
    }
    if (safe && !(b && budget)) c.detail.textContent = safe.reason;
    else if (safe) c.detail.textContent += ` | ${safe.reason}`;
  }

  async function refresh() {
    const { data } = await api("/v1/status");
    current = data;
    modeVal.textContent = data.mode.toUpperCase();
    modeDesc.textContent = data.mode === "enforce" ? t("ov_mode_enforce") : t("ov_mode_shadow");
    modeBtn.textContent = data.mode === "enforce" ? t("ov_switch_shadow") : t("ov_switch_enforce");
    const ks = data.kill_switch;
    killState.className = `banner ${ks.engaged ? "bad" : "ok"}`;
    killState.textContent = ks.engaged
      ? `${t("ov_kill_engaged")} (${ks.reason || ""}; ${t("ov_kill_since")} ${fmt.time(ks.since)})`
      : t("ov_kill_released");
    killBtn.textContent = ks.engaged ? t("ov_kill_release") : t("ov_kill_engage");
    killBtn.className = ks.engaged ? "btn" : "btn btn-danger";
    killWrap.hidden = ks.engaged;

    const safe = data.safe_states || {};
    const budget = data.budget || null;
    const names = [...new Set([...Object.keys(safe), ...Object.keys((budget && budget.agents) || {})])].sort();
    for (const n of names) {
      if (!cards.has(n)) { const c = agentCard(n); cards.set(n, c); agentsList.append(c.el); }
      updateAgent(cards.get(n), safe[n], budget && budget.agents ? budget.agents[n] : null, budget ? budget.budget : null);
    }
    for (const [n, c] of cards) if (!names.includes(n)) { c.el.remove(); cards.delete(n); }
    if (!names.length && !agentsBox.querySelector(".none")) agentsList.before(h("p", { class: "muted none", text: t("ov_no_agents") }));
    if (names.length) for (const p of agentsBox.querySelectorAll(".none")) p.remove();

    // audit
    const a = data.audit;
    clear(auditBody);
    if (!a) {
      auditBody.append(h("p", { class: "banner", text: t("ov_audit_off") }));
    } else {
      const stats = a.stats || {};
      const bad = !a.healthy || Boolean(stats.backend_errors) || Boolean(stats.dropped);
      auditBody.append(h("p", { class: `banner ${bad ? "bad" : "ok"}`, text: bad ? t("ov_audit_bad") : t("ov_audit_ok") }));
      const rows = [];
      for (const [k, v] of Object.entries(stats)) rows.push([k, String(v)]);
      if (typeof a.pending === "number") rows.push([t("ov_audit_pending"), String(a.pending)]);
      if (rows.length) auditBody.append(kvList(rows));
    }
    // counters
    clear(countersBody);
    const cr = Object.entries(data.counters || {}).map(([k, v]) => [k, String(v)]);
    countersBody.append(cr.length ? kvList(cr) : h("p", { class: "muted", text: t("none") }));
    // runtime
    clear(runtimeBody);
    runtimeBody.append(kvList([
      [t("ov_version"), data.version],
      [t("ov_uptime"), fmt.uptime(data.uptime_s)],
      [t("ov_buffered"), String(data.decisions_buffered)],
      [t("ov_stream_clients"), String(data.stream_clients)],
      [t("ov_axioms"), (data.axioms || []).join(", ") || t("none")],
    ]));
  }

  await refresh();
  const timer = setInterval(() => { if (!document.hidden) refresh().catch(showError); }, 3000);
  return () => clearInterval(timer);
};

// -- Decisions ----------------------------------------------------------------------------

pages.decisions = async (root) => {
  root.append(h("h1", { text: t("dc_title") }));
  const agent = h("input", { type: "text", autocomplete: "off" });
  const axiom = h("input", { type: "text", autocomplete: "off" });
  const level = h("select", {}, h("option", { value: "", text: t("dc_any") }), ["GO", "ALERT", "LIMIT", "BLOCK"].map((l) => h("option", { value: l, text: l })));
  const apply = h("button", { type: "submit", class: "btn btn-primary", text: t("dc_apply") });
  const pause = h("button", { type: "button", class: "btn", "aria-pressed": "false", text: t("dc_pause") });
  const wipe = h("button", { type: "button", class: "btn", text: t("dc_clear") });
  const form = h("form", { class: "card", role: "search" }, h("div", { class: "fields" }, field(t("dc_filter_agent"), agent), field(t("dc_filter_axiom"), axiom), field(t("dc_filter_level"), level)), h("div", { class: "row" }, apply, pause, wipe));
  const dot = h("span", { class: "dot", "aria-hidden": "true" });
  const connText = h("span", { text: t("dc_reconnecting") });
  const counter = h("p", { class: "muted", "aria-live": "polite", "aria-atomic": "true" });
  const status = h("p", { class: "pill-live" }, dot, connText);
  const { wrap, tbody } = table(t("dc_caption"), [t("dc_col_time"), t("dc_col_agent"), t("dc_col_tool"), t("dc_col_verdict"), t("dc_col_allowed"), t("dc_col_mode"), t("dc_col_reasons")]);
  const empty = h("p", { class: "muted", text: t("dc_empty") });
  root.append(form, status, counter, wrap, empty);

  const seen = new Set();
  let received = 0;
  let paused = false;
  let held = [];
  let es = null;
  let closed = false;

  const match = (r) => {
    if (agent.value && r.agent !== agent.value.trim()) return false;
    if (level.value && r.verdict !== level.value) return false;
    if (axiom.value && !(r.findings || []).some((f) => f.axiom === axiom.value.trim())) return false;
    return true;
  };

  function rowFor(r) {
    const reasons = (r.findings || []).map((f) => h("li", {}, h("span", { class: "mono", text: f.axiom }), `: ${f.reason}`));
    const flags = [];
    if (r.safe_state) flags.push(h("div", { class: "badge bad", text: t("dc_safe_state") }));
    if (r.enforced === false && r.verdict !== "GO") flags.push(h("div", { class: "muted", text: t("dc_not_enforced") }));
    return h("tr", {},
      h("td", { text: fmt.time(r.decided_at) }),
      h("td", { class: "mono", text: r.agent }),
      h("td", { class: "mono", text: r.tool }),
      h("td", {}, verdictBadge(r.verdict)),
      h("td", { text: r.allowed ? t("dc_allowed") : t("dc_denied") }),
      h("td", { text: r.mode }),
      h("td", {}, reasons.length ? h("ul", { class: "reasons" }, reasons) : "", flags),
    );
  }

  function addRow(r, atTop) {
    const id = r.decision_id;
    if (id && seen.has(id)) return;
    if (id) seen.add(id);
    if (!match(r)) return;
    const tr = rowFor(r);
    if (atTop) tbody.prepend(tr); else tbody.append(tr);
    while (tbody.rows.length > MAX_ROWS) tbody.deleteRow(-1);
    empty.hidden = tbody.rows.length > 0;
  }

  let dirty = false;
  const counterTimer = setInterval(() => { if (dirty) { dirty = false; paintCounter(); } }, 2000);
  function paintCounter() {
    const parts = [`${received} ${t("dc_received")}`, `${tbody.rows.length} ${t("dc_showing")}`];
    if (paused) parts.push(`${held.length} ${t("dc_buffered_paused")}`);
    counter.textContent = parts.join(" | ");
  }

  async function loadHistory() {
    const q = new URLSearchParams({ limit: "200" });
    if (agent.value.trim()) q.set("agent", agent.value.trim());
    if (axiom.value.trim()) q.set("axiom", axiom.value.trim());
    if (level.value) q.set("level", level.value);
    const { data } = await api(`/v1/decisions?${q}`);
    clear(tbody);
    seen.clear();
    for (const r of data.decisions) addRow(r, false); // newest first already
    paintCounter();
  }

  function onDecision(ev) {
    let r;
    try { r = JSON.parse(ev.data); } catch (_e) { return; }
    received += 1;
    if (paused) { held.push(r); if (held.length > MAX_ROWS) held.shift(); } else addRow(r, true);
    dirty = true;
  }

  function connect() {
    if (closed || !token) return;
    es = new EventSource(`/v1/decisions/stream?token=${encodeURIComponent(token)}`);
    es.onopen = () => { dot.classList.add("on"); connText.textContent = paused ? t("dc_paused") : t("dc_connected"); };
    es.onmessage = onDecision;
    es.onerror = async () => {
      dot.classList.remove("on");
      connText.textContent = t("dc_reconnecting");
      // EventSource hides the status code: probe once so a rejected token prompts again.
      es.close();
      try { await api("/v1/status"); } catch (_e) { /* shown by the next retry */ }
      if (!closed) setTimeout(connect, 2000);
    };
  }

  form.addEventListener("submit", (e) => { e.preventDefault(); guard(loadHistory); });
  wipe.addEventListener("click", () => { clear(tbody); seen.clear(); empty.hidden = false; paintCounter(); });
  pause.addEventListener("click", () => {
    paused = !paused;
    pause.setAttribute("aria-pressed", String(paused));
    pause.textContent = paused ? t("dc_resume") : t("dc_pause");
    connText.textContent = paused ? t("dc_paused") : (dot.classList.contains("on") ? t("dc_connected") : t("dc_reconnecting"));
    if (!paused) {
      for (const r of held) addRow(r, true);
      held = [];
    }
    paintCounter();
  });

  await loadHistory();
  connect();
  return () => { closed = true; clearInterval(counterTimer); if (es) es.close(); };
};

// -- Campaigns ----------------------------------------------------------------------------

const METRIC_ROWS = [
  ["cp_to_detect_steps", "time_to_detect_steps"],
  ["cp_to_detect_ms", "time_to_detect_ms"],
  ["cp_to_safe_steps", "time_to_safe_state_steps"],
  ["cp_to_safe_ms", "time_to_safe_state_ms"],
];

function metric(label, value, sub, bad) {
  return h("div", { class: `metric${bad ? " is-bad" : ""}` }, h("span", { class: "label", text: label }), h("span", { class: "big", text: value }), h("span", { class: "muted", text: sub || "" }));
}

function renderResult(doc) {
  const s = doc.summary;
  const c = doc.campaign;
  const box = h("div");
  const supported = doc.hypothesis_supported;
  box.append(h("p", { class: `banner ${supported ? "ok" : "bad"}`, text: `${t("cp_hypothesis")}: ${supported ? t("cp_supported") : t("cp_not_supported")}` }));
  box.append(h("p", { class: "muted", text: c.hypothesis || "" }));
  box.append(h("h3", { text: t("cp_metrics") }));
  box.append(h("div", { class: "metrics" },
    metric(t("cp_detection"), fmt.pct(s.detection_rate), `${s.detected} ${t("cp_detected")}, ${s.missed} ${t("cp_missed")}. ${fmt.ci(s.detection_ci95)}`, s.missed > 0),
    metric(t("cp_false_pos"), fmt.pct(s.false_positive_rate), `${s.false_positives}. ${fmt.ci(s.false_positive_ci95)}`, s.false_positives > 0),
    metric(t("cp_safe_rate"), fmt.pct(s.safe_state_rate), fmt.ci(s.safe_state_ci95), false),
    metric(t("cp_harm"), String(s.harmful_actions_executed), `${s.runs_with_harm} ${t("cp_runs_with_harm")}`, s.harmful_actions_executed > 0),
  ));
  // unfavourable results: same weight as the numbers, never collapsed
  const unfav = h("section", { class: "unfav", "aria-labelledby": `uf-${++uid}` });
  unfav.append(h("h3", { id: `uf-${uid}`, text: `${t("cp_unfav")} (${(doc.unfavourable || []).length})` }), h("p", { class: "muted", text: t("cp_unfav_note") }), h("ul", {}, (doc.unfavourable || []).map((u) => h("li", { text: u }))));
  box.append(unfav);

  box.append(h("h3", { text: t("cp_dist") }));
  const dist = table(t("cp_dist"), [t("cp_col_metric"), "n", "p50", "p90", "max", "mean"], [1, 2, 3, 4, 5]);
  for (const [lab, key] of METRIC_ROWS) {
    const d = s[key] || {};
    dist.tbody.append(h("tr", {}, h("th", { scope: "row", text: t(lab) }), ...["n", "p50", "p90", "max", "mean"].map((k) => h("td", { class: "num", text: fmt.num(d[k]) }))));
  }
  box.append(dist.wrap);

  box.append(h("h3", { text: t("cp_checks") }));
  box.append(h("ul", { class: "checks" }, Object.entries(doc.checks || {}).map(([k, ok]) => h("li", { class: `badge ${ok ? "ok" : "bad"}`, text: `${ok ? t("cp_pass") : t("cp_fail")} ${k}` }))));

  box.append(h("h3", { text: t("cp_meta") }));
  box.append(kvList([
    ["id", c.id], ["fault", c.fault], ["mode", c.mode], [t("cp_radius"), c.blast_radius],
    [t("cp_runs"), String(c.runs)], [t("cp_controls"), String(c.controls)], [t("cp_seed"), String(c.seed)],
    [t("cp_duration"), `${doc.duration_s}s`], ["aeon", doc.aeon_version], [t("cp_col_started"), fmt.time(doc.started_at)],
  ]));
  return box;
}

function renderCompare(a, b) {
  const rows = [
    [t("cp_hypothesis"), (d) => (d.hypothesis_supported ? t("cp_supported") : t("cp_not_supported"))],
    [t("cp_detection"), (d) => `${fmt.pct(d.summary.detection_rate)} (${fmt.ci(d.summary.detection_ci95)})`],
    [t("cp_false_pos"), (d) => `${fmt.pct(d.summary.false_positive_rate)} (${d.summary.false_positives})`],
    [t("cp_safe_rate"), (d) => fmt.pct(d.summary.safe_state_rate)],
    [t("cp_harm"), (d) => String(d.summary.harmful_actions_executed)],
    ...METRIC_ROWS.map(([lab, key]) => [t(lab), (d) => `p50 ${fmt.num((d.summary[key] || {}).p50)} / p90 ${fmt.num((d.summary[key] || {}).p90)} / max ${fmt.num((d.summary[key] || {}).max)}`]),
    [t("cp_checks"), (d) => Object.entries(d.checks).map(([k, ok]) => `${ok ? t("cp_pass") : t("cp_fail")} ${k}`).join(", ")],
  ];
  const tb = table(t("cp_compare_title"), [t("cp_col_metric"), a.campaign.id, b.campaign.id]);
  for (const [lab, fn] of rows) tb.tbody.append(h("tr", {}, h("th", { scope: "row", text: lab }), h("td", { text: fn(a) }), h("td", { text: fn(b) })));
  const unfav = (d) => h("div", { class: "unfav" }, h("h3", { text: `${t("cp_unfav")}: ${d.campaign.id} (${(d.unfavourable || []).length})` }), h("ul", {}, (d.unfavourable || []).map((u) => h("li", { text: u }))));
  return h("div", {}, tb.wrap, h("div", { class: "compare" }, unfav(a), unfav(b)));
}

pages.campaigns = async (root) => {
  root.append(h("h1", { text: t("cp_title") }));
  let stopped = false;

  const target = h("input", { type: "text", required: true, autocomplete: "off", maxlength: "80" });
  const runs = h("input", { type: "number", min: "1", max: "1000" });
  const controls = h("input", { type: "number", min: "0", max: "1000" });
  const seed = h("input", { type: "number" });
  const radius = h("select", {}, h("option", { value: "", text: t("cp_default") }), ["dev", "staging", "prod-shadow"].map((r) => h("option", { value: r, text: r })));
  const launch = h("button", { type: "submit", class: "btn btn-primary", text: t("cp_launch") });
  const progress = h("p", { class: "banner", role: "status", "aria-live": "polite", hidden: true });
  const form = h("form", { class: "card", "aria-labelledby": "cp-start-h" },
    h("h2", { id: "cp-start-h", text: t("cp_start") }),
    h("div", { class: "fields" }, field(t("cp_target"), target, t("cp_target_hint")), field(t("cp_runs"), runs), field(t("cp_controls"), controls), field(t("cp_seed"), seed), field(t("cp_radius"), radius)),
    h("div", { class: "row" }, launch), progress);

  const listBox = h("section", { "aria-labelledby": "cp-list-h" }, h("h2", { id: "cp-list-h", text: t("cp_list") }));
  const resultBox = h("section", { "aria-label": t("cp_result"), tabindex: "-1" });
  root.append(form, listBox, resultBox);

  const picked = new Set();

  async function fetchResult(id) {
    const { data } = await api(`/v1/campaigns/${encodeURIComponent(id)}`);
    return data;
  }

  async function show(id) {
    const doc = await fetchResult(id);
    clear(resultBox);
    if (doc.status === "error") { resultBox.append(h("p", { class: "banner bad", text: `${t("cp_failed")}: ${doc.error}` })); return; }
    const close = h("button", { type: "button", class: "btn", text: t("cp_close") });
    close.addEventListener("click", () => clear(resultBox));
    resultBox.append(h("div", { class: "card" }, h("h2", { text: `${t("cp_result")}: ${doc.campaign.id}` }), renderResult(doc), h("div", { class: "row" }, close)));
    resultBox.focus();
  }

  async function compare() {
    const ids = [...picked];
    if (ids.length !== 2) { showError(new Error(t("cp_compare_need_two"))); return; }
    const [a, b] = await Promise.all(ids.map(fetchResult));
    clear(resultBox);
    resultBox.append(h("div", { class: "card" }, h("h2", { text: t("cp_compare_title") }), renderCompare(a, b)));
    resultBox.focus();
  }

  async function loadList() {
    const { data } = await api("/v1/campaigns");
    for (const n of [...listBox.children].slice(1)) n.remove();
    const rows = data.campaigns || [];
    if (!rows.length) { listBox.append(h("p", { class: "muted", text: t("cp_none") })); return; }
    const tb = table(t("cp_list"), [t("cp_compare_pick"), t("cp_col_id"), t("cp_col_started"), t("cp_col_supported"), t("cp_col_detection"), t("cp_col_fp"), t("cp_col_actions")]);
    for (const r of rows) {
      const cb = h("input", { type: "checkbox", "aria-label": `${t("cp_compare_pick")} ${r.id}` });
      cb.checked = picked.has(r.id);
      cb.addEventListener("change", () => { if (cb.checked) picked.add(r.id); else picked.delete(r.id); });
      const view = h("button", { type: "button", class: "btn", text: t("cp_view"), "aria-label": `${t("cp_view")} ${r.id}` });
      view.addEventListener("click", () => guard(() => show(r.id)));
      tb.tbody.append(h("tr", {},
        h("td", {}, cb), h("th", { scope: "row", class: "mono", text: r.id }), h("td", { text: fmt.time(r.started_at) }),
        h("td", {}, h("span", { class: `badge ${r.hypothesis_supported ? "ok" : "bad"}`, text: r.hypothesis_supported ? t("cp_supported") : t("cp_not_supported") })),
        h("td", { text: fmt.pct(r.detection_rate) }), h("td", { text: fmt.pct(r.false_positive_rate) }), h("td", {}, view)));
    }
    const cmp = h("button", { type: "button", class: "btn", text: t("cp_compare_go") });
    cmp.addEventListener("click", () => guard(compare));
    listBox.append(tb.wrap, h("div", { class: "row" }, cmp), h("p", { class: "hint", text: t("cp_compare_hint") }));
  }

  async function poll(id) {
    progress.hidden = false;
    progress.className = "banner";
    progress.textContent = `${t("cp_running")}: ${id}`;
    while (!stopped) {
      await new Promise((r) => setTimeout(r, 1500));
      if (stopped) return;
      const res = await api(`/v1/campaigns/${encodeURIComponent(id)}`);
      if (res.status === 202) continue;
      const doc = res.data;
      if (doc.status === "error") {
        progress.className = "banner bad";
        progress.textContent = `${t("cp_failed")}: ${doc.error}`;
      } else {
        progress.className = "banner ok";
        progress.textContent = `${t("cp_done")}: ${id}`;
        clear(resultBox);
        resultBox.append(h("div", { class: "card" }, h("h2", { text: `${t("cp_result")}: ${doc.campaign.id}` }), renderResult(doc)));
        await loadList();
      }
      return;
    }
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    guard(async () => {
      const body = { target: target.value.trim() };
      if (runs.value) body.runs = Number(runs.value);
      if (controls.value) body.controls = Number(controls.value);
      if (seed.value) body.seed = Number(seed.value);
      if (radius.value) body.blast_radius = radius.value;
      launch.disabled = true;
      try {
        const { data } = await api("/v1/campaigns", { method: "POST", body });
        await poll(data.id);
      } catch (err) {
        if (err instanceof ApiError && err.status === 409) throw new Error(t("cp_running_elsewhere"));
        throw err;
      } finally { launch.disabled = false; }
    });
  });

  await loadList();
  // resume the poll when a campaign was already running
  try {
    const { data } = await api("/v1/campaigns");
    const running = (data.running || [])[0];
    if (running) guard(() => poll(running.id));
  } catch (_e) { /* the list call already reported */ }
  return () => { stopped = true; };
};

// -- Audit --------------------------------------------------------------------------------

function downloadName(res, fallback) {
  const cd = res.headers.get("content-disposition") || "";
  const m = /filename="?([^";]+)"?/.exec(cd);
  return m ? m[1] : fallback;
}

pages.audit = async (root) => {
  root.append(h("h1", { text: t("au_title") }));
  const expect = h("input", { type: "text", autocomplete: "off", spellcheck: "false", class: "mono" });
  const go = h("button", { type: "submit", class: "btn btn-primary", text: t("au_verify_go") });
  const out = h("div", { role: "status", "aria-live": "polite" });
  const vform = h("form", { class: "card", "aria-labelledby": "au-v-h" }, h("h2", { id: "au-v-h", text: t("au_verify") }), field(t("au_expect"), expect, t("au_expect_hint")), h("div", { class: "row" }, go), out);

  const limit = h("input", { type: "number", min: "1", max: "5000", value: "100" });
  const type = h("input", { type: "text", autocomplete: "off" });
  const load = h("button", { type: "submit", class: "btn", text: t("au_load") });
  const tform = h("form", { class: "card", "aria-labelledby": "au-t-h" }, h("h2", { id: "au-t-h", text: t("au_tail") }), h("div", { class: "fields" }, field(t("au_limit"), limit), field(t("au_type"), type)), h("div", { class: "row" }, load));
  const tableBox = h("div");

  const exportNote = h("p", { class: "muted", role: "status", "aria-live": "polite" });
  const expBox = h("div", { class: "card" }, h("h2", { text: t("au_export") }), h("div", { class: "row" }, ...["jsonl", "csv"].map((fmtName) => {
    const b = h("button", { type: "button", class: "btn", text: t(fmtName === "jsonl" ? "au_export_jsonl" : "au_export_csv") });
    b.addEventListener("click", () => guard(async () => {
      const res = await api(`/v1/audit/export?format=${fmtName}`, { raw: true });
      if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail || d; } catch (_e) { /* ignore */ } throw new ApiError(res.status, d); }
      const blob = await res.blob();
      const name = downloadName(res, `aeon-audit.${fmtName}`);
      const url = URL.createObjectURL(blob);
      const a = h("a", { href: url, download: name });
      document.body.append(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 10000);
      exportNote.textContent = `${t("au_exported")} ${name}`;
    }));
    return b;
  })), exportNote);
  root.append(vform, tform, tableBox, expBox);

  vform.addEventListener("submit", (e) => {
    e.preventDefault();
    guard(async () => {
      const body = expect.value.trim() ? { expect_head: expect.value.trim() } : {};
      const { data: r } = await api("/v1/audit/verify", { method: "POST", body });
      clear(out);
      out.append(h("p", { class: `banner ${r.ok ? "ok" : "bad"}`, text: r.ok ? t("au_intact") : t("au_broken") }));
      const pairs = [[t("au_records"), String(r.records)], [t("au_head"), r.head]];
      if (r.ts_regressions) pairs.push([t("au_ts_regressions"), String(r.ts_regressions)]);
      out.append(kvList(pairs));
      if (!r.ok) {
        const fb = h("div", { class: "unfav" }, h("h3", { text: t("au_first_bad") }), kvList([
          [t("au_first_bad_seq"), r.first_bad_seq === null ? t("cp_na") : String(r.first_bad_seq)],
          [t("au_first_bad_line"), r.first_bad_line === null ? t("cp_na") : String(r.first_bad_line)],
          [t("au_reason"), r.reason || ""],
        ]));
        out.append(fb);
      }
      if ((r.warnings || []).length) out.append(h("h3", { text: t("au_warnings") }), h("ul", {}, r.warnings.map((w) => h("li", { text: w }))));
    });
  });

  async function loadTail() {
    const q = new URLSearchParams({ limit: String(Math.max(1, Math.min(5000, Number(limit.value) || 100))) });
    if (type.value.trim()) q.set("type", type.value.trim());
    const { data } = await api(`/v1/audit?${q}`);
    clear(tableBox);
    if (!data.records.length) { tableBox.append(h("p", { class: "muted", text: t("au_empty") })); return; }
    const tb = table(t("au_caption"), [t("au_col_seq"), t("au_col_time"), t("au_col_type"), t("au_col_agent"), t("au_col_tool"), t("au_col_verdict"), t("au_col_hash")], [0]);
    for (const r of data.records) {
      const d = r.data || {};
      tb.tbody.append(h("tr", {},
        h("td", { class: "num", text: String(r.seq) }), h("td", { text: fmt.time(r.ts) }), h("td", { text: r.type || "" }),
        h("td", { class: "mono", text: d.agent || "" }), h("td", { class: "mono", text: d.tool || "" }),
        h("td", {}, d.verdict ? verdictBadge(d.verdict) : ""),
        h("td", {}, h("span", { class: "mono cut", title: r.hash || "", text: r.hash || "" }))));
    }
    tableBox.append(tb.wrap);
  }
  tform.addEventListener("submit", (e) => { e.preventDefault(); guard(loadTail); });
  await loadTail().catch(showError);
};

// -- Claims -------------------------------------------------------------------------------

pages.claims = async (root) => {
  root.append(h("h1", { text: t("cl_title") }), h("p", { class: "muted", text: t("cl_intro") }));
  const legend = h("section", { class: "card", "aria-labelledby": "cl-legend-h" }, h("h2", { id: "cl-legend-h", text: t("cl_legend") }), h("ol", { class: "legend" },
    ...["specified", "implemented", "measured"].map((s) => h("li", {}, h("span", { class: `badge s-${s}`, text: t(`cl_${s}`) }), h("span", { text: t(`cl_${s}_desc`) })))));
  root.append(legend);
  let data;
  try {
    ({ data } = await api("/v1/claims"));
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      root.append(h("div", { class: "card" }, h("p", { class: "banner warn", text: t("cl_missing") }), h("p", { text: t("cl_missing_hint") }), h("p", { class: "muted mono", text: e.message })));
      return;
    }
    throw e;
  }
  const claims = Array.isArray(data) ? data : data.claims || [];
  if (!claims.length) { root.append(h("p", { class: "muted", text: t("cl_empty") })); return; }
  const tb = table(t("cl_caption"), [t("cl_col_claim"), t("cl_col_status"), t("cl_col_value"), t("cl_col_note"), t("cl_col_evidence"), t("cl_col_checked")]);
  for (const c of claims) {
    const status = ["specified", "implemented", "measured"].includes(c.status) ? c.status : "specified";
    const note = c.note ? h("span", { class: `note ${/not met/i.test(c.note) ? "unmet" : "plain"}`, text: c.note }) : "";
    tb.tbody.append(h("tr", {},
      h("th", { scope: "row" }, h("div", { text: c.text || c.id }), h("div", { class: "muted mono", text: c.id })),
      h("td", {}, h("span", { class: `badge s-${status}`, text: t(`cl_${status}`) })),
      h("td", { text: c.value || "" }),
      h("td", {}, note),
      h("td", {}, h("ul", { class: "evidence" }, (c.evidence || []).map((ev) => h("li", { text: ev })))),
      h("td", { text: c.last_checked || "" })));
  }
  root.append(tb.wrap);
};

// -- boot ---------------------------------------------------------------------------------

function boot() {
  initLang();
  loadToken();
  applyChrome();

  $("#lang-btn").addEventListener("click", () => { setLang(getLang() === "pt" ? "en" : "pt"); rerender(); });
  $("#forget-btn").addEventListener("click", () => { clearToken(); clear($("#main")); askToken(false).then(render); });
  $("#token-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const v = $("#token-input").value.trim();
    if (!v) return;
    token = v;
    try { sessionStorage.setItem(TOKEN_KEY, token); } catch (_e) { /* ignore */ }
    $("#token-dialog").close();
    const waiters = tokenWaiters;
    tokenWaiters = [];
    for (const w of waiters) w();
  });
  $("#token-dialog").addEventListener("cancel", (e) => e.preventDefault()); // a token is required
  $("#confirm-no").addEventListener("click", () => $("#confirm-dialog").close("no"));
  $("#confirm-form").addEventListener("submit", (e) => { e.preventDefault(); $("#confirm-dialog").close("yes"); });

  window.addEventListener("hashchange", render);
  render();
}

boot();
