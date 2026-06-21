/* OpenLogiTwin HMI engine — replays a deterministic scene_model.py trace.
   High-Performance HMI rules (ISA-101 / Hollifield / Rockwell): equipment reads by
   outline (fill = canvas), status by brightness + word (no red/green lamps), colour
   only for live data (--data) and alarms (--p1/2/3), and alarms are redundantly coded
   (shape + colour + text) in a docked banner + summary (ISA-18.2). */
(function () {
  "use strict";
  var NS = "http://www.w3.org/2000/svg", svg = document.getElementById("cell"), $ = function (id) { return document.getElementById(id); };
  var cssv = function (n) { return getComputedStyle(document.documentElement).getPropertyValue(n).trim(); };
  var OX = 168, SCALE = 5.27, BELT_Y = 250, BELT_H = 32, BOX_H = 26, BOX_W = 30;
  var cx = function (cm) { return OX + cm * SCALE; };
  var A_BIN = { x: 690, y: 118 }, B_BIN = { x: 798, y: 338 };
  var frames = [], dt = 0.05, dur = 0, layout = null;
  var simT = 0, playing = true, speed = 1, lastIdx = -1, lastTick = null, lastSt = null;
  var vis = new Map(), spark = [], alarms = [], alarmSeq = 0, jamActive = false, estopLatched = false;

  function el(t, a) { var e = document.createElementNS(NS, t); for (var k in a) e.setAttribute(k, a[k]); return e; }
  function txt(x, y, s, fill, sz, anchor) { var t = el("text", { x: x, y: y, "font-size": sz || 11, fill: fill, "font-family": "system-ui,Segoe UI,Arial" }); if (anchor) t.setAttribute("text-anchor", anchor); t.textContent = s; return t; }

  /* ---- static mimic: outlined gray equipment, flow left→right ---- */
  function drawStatic() {
    svg.innerHTML = "";
    var L = cssv("--line"), L2 = cssv("--line-2"), INK = cssv("--ink"), INK2 = cssv("--ink-2"), BG = cssv("--bg");
    var bx0 = cx(0), bx1 = cx(layout.end), cyc = BELT_Y + BELT_H / 2;
    svg.appendChild(txt(bx0 - 26, 30, "CONV-001 · SORTING CELL", INK2, 12));
    svg.appendChild(el("path", { d: "M" + (bx0 + 100) + " 26 h34 m-7 -4 l7 4 l-7 4", fill: "none", stroke: L2, "stroke-width": 1.2 }));
    // infeed funnel feeding the belt start
    svg.appendChild(el("path", { d: "M" + (bx0 + 6) + " " + (BELT_Y - 80) + " h46 l-13 62 h-20 z", fill: BG, stroke: L, "stroke-width": 1.2 }));
    svg.appendChild(txt(bx0 + 28, BELT_Y - 86, "INFEED", INK2, 9.5, "middle"));
    // drive motor M-001 (ISA circle)
    svg.appendChild(el("circle", { id: "sv-motor", cx: bx0 - 26, cy: cyc, r: 20, fill: BG, stroke: L, "stroke-width": 1.4 }));
    svg.appendChild(txt(bx0 - 26, cyc + 5, "M", INK, 14, "middle"));
    svg.appendChild(txt(bx0 - 26, BELT_Y + BELT_H + 22, "M-001", INK2, 9.5, "middle"));
    // conveyor (outline; fill = canvas) + side rails
    svg.appendChild(el("rect", { x: bx0, y: BELT_Y, width: bx1 - bx0, height: BELT_H, fill: BG, stroke: L, "stroke-width": 1.4 }));
    svg.appendChild(el("line", { x1: bx0, y1: BELT_Y + 5, x2: bx1, y2: BELT_Y + 5, stroke: L, "stroke-width": .6, opacity: .55 }));
    svg.appendChild(el("line", { x1: bx0, y1: BELT_Y + BELT_H - 5, x2: bx1, y2: BELT_Y + BELT_H - 5, stroke: L, "stroke-width": .6, opacity: .55 }));
    // photo-eyes (ISA instrument bubbles)
    [["pe1", layout.pe1, "PE-001"], ["pe2", layout.pe2, "PE-002"]].forEach(function (p) {
      var X = cx(p[1]);
      svg.appendChild(el("line", { x1: X, y1: BELT_Y - 18, x2: X, y2: BELT_Y, stroke: L2, "stroke-width": 1 }));
      svg.appendChild(el("circle", { id: "sv-" + p[0], cx: X, cy: BELT_Y - 27, r: 9, fill: BG, stroke: L, "stroke-width": 1.3 }));
      svg.appendChild(txt(X, BELT_Y - 42, p[2], INK2, 9.5, "middle"));
    });
    // diverter DV-001 (pivoting gate)
    var dvX = cx(layout.divert);
    svg.appendChild(el("circle", { cx: dvX, cy: BELT_Y + BELT_H, r: 3, fill: L }));
    var arm = el("g", { id: "sv-divarm" });
    arm.appendChild(el("line", { x1: dvX, y1: BELT_Y + BELT_H, x2: dvX, y2: BELT_Y - 16, stroke: INK, "stroke-width": 3.4 }));
    svg.appendChild(arm);
    svg.appendChild(txt(dvX, BELT_Y + BELT_H + 22, "DV-001", INK2, 9.5, "middle"));
    // chute A spur (up from diverter) + chute B spur (down from belt end)
    svg.appendChild(el("path", { d: "M" + dvX + " " + BELT_Y + " L" + (A_BIN.x + 16) + " " + (A_BIN.y + 52), fill: "none", stroke: L, "stroke-width": 1.3, "stroke-dasharray": "5 4" }));
    svg.appendChild(el("path", { d: "M" + bx1 + " " + (BELT_Y + BELT_H) + " L" + (B_BIN.x + 16) + " " + B_BIN.y, fill: "none", stroke: L, "stroke-width": 1.3, "stroke-dasharray": "5 4" }));
    bin("A", A_BIN); bin("B", B_BIN);
    svg.appendChild(el("g", { id: "sv-alarm" }));     // jam alarm indicator (drawn on demand)
    svg.appendChild(el("g", { id: "sv-parcels" }));
    $("sv-motor").setAttribute("data-fp", ""); $("sv-motor").onclick = motorFp;
    $("sv-divarm").setAttribute("data-fp", ""); $("sv-divarm").onclick = diverterFp;
  }
  function bin(id, p) {
    var L = cssv("--line"), L2 = cssv("--line-2"), INK2 = cssv("--ink-2"), DATA = cssv("--data"), BG = cssv("--bg");
    var W = 120, H = 54;
    var box = el("path", { d: "M" + p.x + " " + p.y + " v" + H + " h" + W + " v" + (-H), fill: BG, stroke: L, "stroke-width": 1.3 });
    box.setAttribute("data-fp", ""); box.onclick = function () { chuteFp(id); };
    svg.appendChild(box);
    svg.appendChild(txt(p.x + 4, p.y - 8, "CHUTE " + id, INK2, 11));
    var c = txt(p.x + W - 4, p.y - 8, "0", DATA, 15, "end"); c.setAttribute("id", "binc" + id); c.setAttribute("font-weight", "600"); svg.appendChild(c);
    svg.appendChild(txt(p.x + 8, p.y + H - 24, "LEVEL", INK2, 8.5));
    svg.appendChild(el("rect", { x: p.x + 8, y: p.y + H - 18, width: W - 16, height: 9, fill: BG, stroke: L2, "stroke-width": .8 }));
    svg.appendChild(el("rect", { id: "binf" + id, x: p.x + 9, y: p.y + H - 17, width: 0, height: 7, fill: L2 }));
  }
  function parcelEl(dest) {
    var L2 = cssv("--line-2"), RAISED = cssv("--raised"), DATA = cssv("--data");
    var g = el("g", {});
    g.appendChild(el("rect", { width: BOX_W, height: BOX_H, fill: RAISED, stroke: L2, "stroke-width": 1.2 }));
    g.appendChild(el("line", { x1: 0, y1: 7, x2: BOX_W, y2: 7, stroke: L2, "stroke-width": .7, opacity: .6 }));
    g.appendChild(txt(BOX_W / 2, BOX_H - 8.5, dest === 1 ? "A" : "B", DATA, 12, "middle"));
    return g;
  }

  function frameAt(t) {
    var i = Math.min(Math.floor(t / dt), frames.length - 1); if (i < 0) i = 0;
    var f = frames[i], g = frames[Math.min(i + 1, frames.length - 1)], fr = Math.min(Math.max((t - i * dt) / dt, 0), 1);
    var gm = new Map(g.parcels.map(function (p) { return [p.id, p]; }));
    var parcels = f.parcels.map(function (p) { var q = gm.get(p.id); return { id: p.id, x: q ? p.x + (q.x - p.x) * fr : p.x, dest: p.dest, stuck: p.stuck }; });
    return { i: i, parcels: parcels, motor: f.motor, diverter: f.diverter, jam: f.jam, a: f.a, b: f.b, pe1: f.pe1, pe2: f.pe2 };
  }
  var set = function (id, k, v) { var e = $(id); if (e) e.setAttribute(k, v); };

  function render(st, rd) {
    lastSt = st;
    var ON = cssv("--on"), OFF = cssv("--off"), BG = cssv("--bg"), INK = cssv("--ink"), P1 = cssv("--p1");
    // parcels (outlined, A/B label; brightness shows on belt). Stuck → alarm outline.
    var g = $("sv-parcels"), seen = new Set();
    st.parcels.forEach(function (p) {
      var v = vis.get(p.id); if (!v) { var e = parcelEl(p.dest); g.appendChild(e); v = { el: e }; vis.set(p.id, v); }
      v.dest = p.dest; v.el.setAttribute("transform", "translate(" + (cx(p.x) - BOX_W / 2) + " " + (BELT_Y - BOX_H) + ")");
      v.el.firstChild.setAttribute("stroke", p.stuck ? P1 : cssv("--line-2"));
      v.el.firstChild.setAttribute("stroke-width", p.stuck ? 2 : 1.2);
      seen.add(p.id);
    });
    vis.forEach(function (v, id) {
      if (seen.has(id)) return;
      if (!v.exiting) { v.exiting = true; v.et = 0; var m = v.el.getAttribute("transform").match(/translate\(([-\d.]+) ([-\d.]+)/); v.sx = +m[1]; v.sy = +m[2]; var t = v.dest === 1 ? A_BIN : B_BIN; v.tx = t.x; v.ty = t.y; }
      v.et += rd; var k = Math.min(v.et / 0.5, 1);
      v.el.setAttribute("transform", "translate(" + (v.sx + (v.tx - v.sx) * k) + " " + (v.sy + (v.ty - v.sy) * k) + ")");
      v.el.setAttribute("opacity", 1 - k); if (k >= 1) { v.el.remove(); vis.delete(id); }
    });
    // motor: brightness + status WORD (not colour)
    set("sv-motor", "fill", st.motor ? ON : OFF);
    $("st-motor").textContent = st.motor ? "RUN" : "STOP";
    // diverter gate position + word
    set("sv-divarm", "transform", "rotate(" + (st.diverter ? -38 : 0) + " " + cx(layout.divert) + " " + (BELT_Y + BELT_H) + ")");
    $("st-div").textContent = st.diverter ? "DIVERT → A" : "PASS → B";
    // photo-eyes: blocked shown by brightness (ON fill), not colour
    set("sv-pe1", "fill", st.pe1 ? ON : BG); set("sv-pe2", "fill", st.pe2 ? ON : BG);
    // jam alarm indicator near the diverter (redundant shape+colour+text), not by recolouring the belt
    drawJamIndicator(st.jam);
    // bins + KPIs (live data colour)
    if ($("bincA")) $("bincA").textContent = st.a; if ($("bincB")) $("bincB").textContent = st.b;
    binFill("binfA", st.a); binFill("binfB", st.b);
    $("ca").textContent = st.a; $("cb").textContent = st.b; $("st-wip").textContent = st.parcels.length;
    var mins = Math.max(simT / 60, 1e-6), tput = Math.round((st.a + st.b) / mins);
    $("tp").textContent = tput; ptr("tp-ptr", tput, 50); band("tp-band", 8, 36, 50);
    var tot = Math.max(1, (frames.length ? frames[frames.length - 1].a + frames[frames.length - 1].b : 1));
    ptr("a-ptr", st.a, tot); ptr("b-ptr", st.b, tot);
    $("rt").textContent = fmt(simT);
    $("seek").value = Math.round(simT / dur * 1000) || 0;
    $("time").textContent = simT.toFixed(1) + " / " + dur.toFixed(1) + " s";
    drawTrend(); drawSpark();
    logTransitions(st.i);
  }
  function drawJamIndicator(on) {
    var g = $("sv-alarm"); if (!g) return;
    if (!on) { g.innerHTML = ""; return; }
    if (g.childElementCount) return;
    var P1 = cssv("--p1"), dvX = cx(layout.divert);
    g.appendChild(el("path", { d: "M" + dvX + " " + (BELT_Y - 44) + " l13 22 l-26 0 z", fill: P1, stroke: P1 }));
    g.appendChild(txt(dvX, BELT_Y - 25, "!", "#fff", 13, "middle"));
    g.appendChild(el("line", { x1: dvX, y1: BELT_Y - 20, x2: dvX, y2: BELT_Y, stroke: P1, "stroke-width": 1, "stroke-dasharray": "2 2" }));
  }
  function ptr(id, v, max) { var e = $(id); if (e) e.style.left = Math.min(Math.max(v / max, 0), 1) * 100 + "%"; }
  function band(id, lo, hi, max) { var e = $(id); if (e) { e.style.left = (lo / max * 100) + "%"; e.style.width = ((hi - lo) / max * 100) + "%"; } }
  function binFill(id, n) { var e = $(id); if (e) e.setAttribute("width", Math.min(n / 12, 1) * (120 - 18)); }
  function fmt(s) { var m = Math.floor(s / 60), x = Math.floor(s % 60); return (m < 10 ? "0" : "") + m + ":" + (x < 10 ? "0" : "") + x; }

  /* ---- trend (thin lines on gray, HP-HMI restraint) ---- */
  function drawTrend() {
    var c = $("trend"), x = c.getContext("2d"), W = c.width, H = c.height, n = frames.length; if (!n) return;
    x.clearRect(0, 0, W, H);
    var maxN = Math.max(1, frames[n - 1].a + frames[n - 1].b);
    var xs = function (i) { return i / (n - 1) * (W - 6) + 3; }, ys = function (v) { return H - 6 - v / maxN * (H - 14); };
    x.strokeStyle = rgba(cssv("--line"), .5); x.lineWidth = 1;
    for (var gy = 0; gy <= 2; gy++) { var yy = 6 + gy * (H - 12) / 2; x.beginPath(); x.moveTo(3, yy); x.lineTo(W - 3, yy); x.stroke(); }
    [[function (f) { return f.b; }, cssv("--ink-2")], [function (f) { return f.a; }, cssv("--data")]].forEach(function (s) {
      x.beginPath(); for (var i = 0; i < n; i++) { var px = xs(i), py = ys(s[0](frames[i])); i ? x.lineTo(px, py) : x.moveTo(px, py); } x.strokeStyle = s[1]; x.lineWidth = 1.6; x.stroke();
    });
    var ph = xs(Math.min(Math.floor(simT / dt), n - 1)); x.strokeStyle = rgba(cssv("--data"), .5); x.lineWidth = 1; x.beginPath(); x.moveTo(ph, 2); x.lineTo(ph, H - 2); x.stroke();
  }
  function drawSpark() {
    var c = $("spark"), x = c.getContext("2d"), W = c.width, H = c.height; x.clearRect(0, 0, W, H); if (spark.length < 2) return;
    var mx = Math.max.apply(null, spark.concat([1]));
    x.beginPath(); spark.forEach(function (s, i) { var px = i / (spark.length - 1) * W, py = H - 2 - s / mx * (H - 5); i ? x.lineTo(px, py) : x.moveTo(px, py); });
    x.strokeStyle = cssv("--data"); x.lineWidth = 1.3; x.stroke();
  }
  function rgba(hex, a) { hex = hex.replace("#", ""); if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join(""); var n = parseInt(hex, 16); return "rgba(" + (n >> 16 & 255) + "," + (n >> 8 & 255) + "," + (n & 255) + "," + a + ")"; }

  /* ---- alarms & events (ISA-18.2 summary + docked banner) ---- */
  var PRI = { 1: { lab: "P1", clip: "polygon(50% 0,100% 50%,50% 100%,0 50%)", c: "--p1" }, 2: { lab: "P2", clip: "polygon(50% 0,100% 100%,0 100%)", c: "--p2" }, 3: { lab: "P3", clip: "none", c: "--p3" }, 4: { lab: "·", clip: "circle(45%)", c: "--ink-3" } };
  function addAlarm(pri, tag, desc, info, time) { alarms.unshift({ id: ++alarmSeq, t: (time == null ? simT : time), pri: pri, tag: tag, desc: desc, state: info ? "RTN" : "UNACK" }); if (alarms.length > 80) alarms.pop(); renderAlarms(); }
  function returnAlarm(tag) { for (var i = 0; i < alarms.length; i++) if (alarms[i].tag === tag && alarms[i].state !== "RTN") { alarms[i].state = "RTN"; break; } renderAlarms(); }
  function renderAlarms() {
    var tb = $("alm-rows"); tb.innerHTML = "";
    if (!alarms.length) { var tr = document.createElement("tr"); tr.innerHTML = '<td colspan="5" style="color:var(--ink-3)">No active alarms</td>'; tb.appendChild(tr); }
    alarms.slice(0, 30).forEach(function (a) {
      var p = PRI[a.pri], tr = document.createElement("tr");
      tr.className = (a.state === "UNACK" ? "unack blink " : "") + (a.state === "RTN" ? "rtn" : "");
      tr.innerHTML = '<td class="pri" style="color:var(--' + (a.pri <= 3 ? (a.pri === 1 ? "p1" : a.pri === 2 ? "p2" : "p3") : "ink-2") + ')">' +
        '<span class="ic" style="background:var(' + p.c + ');clip-path:' + p.clip + '"></span>' + p.lab + '</td>' +
        '<td class="ts num">' + fmt(a.t) + '</td><td class="tag">' + a.tag + '</td><td>' + a.desc + '</td>' +
        '<td><span class="state ' + a.state + '">' + a.state + '</span></td>';
      tr.onclick = function () { alarmFp(a); };
      tb.appendChild(tr);
    });
    // docked banner: highest-priority UNACK, else latest
    var bn = $("banner"), act = alarms.filter(function (a) { return a.state === "UNACK"; }).sort(function (a, b) { return a.pri - b.pri; })[0];
    if (act) { bn.className = "banner has blink"; $("bn-pri").style.background = "var(--" + (act.pri === 1 ? "p1" : act.pri === 2 ? "p2" : "p3") + ")"; $("bn-pri").textContent = act.pri; $("bn-msg").textContent = act.tag + " — " + act.desc; $("bn-ts").textContent = fmt(act.t) + " s"; }
    else { bn.className = "banner quiet"; $("bn-msg").textContent = "No active alarms"; $("bn-ts").textContent = ""; }
  }
  function logTransitions(idx) {
    if (idx <= lastIdx) { lastIdx = idx; return; }
    for (var j = Math.max(lastIdx, 0) + 1; j <= idx; j++) {
      var a = frames[j - 1], b = frames[j]; if (!a || !b) continue; var tt = j * dt;
      if (b.a > a.a) addAlarm(4, "CHUTE-A", "Parcel sorted to Chute A", true, tt);
      if (b.b > a.b) addAlarm(4, "CHUTE-B", "Parcel sorted to Chute B", true, tt);
      if (b.jam && !a.jam) addAlarm(1, "DV-001", "Conveyor jam — sorter blocked", false, tt);
      if (!b.jam && a.jam) returnAlarm("DV-001");
    }
    lastIdx = idx;
  }

  /* ---- faceplates (equipment detail + ISA-18.2 alarm rationalisation) ---- */
  var RAT = {
    "DV-001": { cause: "Parcel stuck at the diverter — PE-002 blocked beyond the 1 s jam timer.", consequence: "Sorter halted and the conveyor stopped; parcels accumulate upstream.", action: "Clear the obstruction at DV-001, then press Reset to restart the cell." },
    "CELL-01": { cause: "Operator actuated the cell E-stop.", consequence: "Cell de-energised; all motion stopped (fail-safe).", action: "Resolve the hazard, release the E-stop, then press Reset." }
  };
  function openFp(title, tag, rows, actions) {
    $("fp-title").textContent = title; $("fp-tag").textContent = tag || "";
    var bd = $("fp-body"); bd.innerHTML = "";
    rows.forEach(function (r) {
      var d = document.createElement("div"); d.className = "fp-row" + (r.col ? " col" : "");
      d.innerHTML = '<span class="k">' + r.k + '</span><span class="vv"' + (r.color ? ' style="color:' + r.color + '"' : "") + ">" + r.v + "</span>";
      bd.appendChild(d);
    });
    var ac = $("fp-ac"); ac.innerHTML = "";
    (actions || []).forEach(function (a) { var b = document.createElement("button"); b.className = "btn"; b.textContent = a.label; b.onclick = a.onclick; ac.appendChild(b); });
    $("fp-ov").classList.add("show");
  }
  function closeFp() { $("fp-ov").classList.remove("show"); }
  function alarmFp(a) {
    var r = RAT[a.tag] || {};
    openFp(a.pri <= 3 ? "Alarm — priority " + a.pri : "Event", a.tag, [
      { k: "State", v: a.state, color: a.state === "UNACK" ? "var(--p1)" : "" },
      { k: "Time", v: fmt(a.t) + " s" },
      { k: "Description", v: a.desc, col: true },
      { k: "Probable cause", v: r.cause || "—", col: true },
      { k: "Consequence", v: r.consequence || "—", col: true },
      { k: "Corrective action", v: r.action || "—", col: true }
    ], a.state === "UNACK"
      ? [{ label: "Acknowledge", onclick: function () { a.state = "ACK"; renderAlarms(); closeFp(); } }, { label: "Close", onclick: closeFp }]
      : [{ label: "Close", onclick: closeFp }]);
  }
  function motorFp() { var s = lastSt || {}; openFp("Drive motor", "M-001", [
    { k: "State", v: s.motor ? "RUN" : "STOP" }, { k: "Mode", v: "Auto" },
    { k: "Run time", v: fmt(simT) }, { k: "Interlock", v: s.jam ? "JAM — stopped" : "OK", color: s.jam ? "var(--p1)" : "" }
  ], [{ label: "Close", onclick: closeFp }]); }
  function diverterFp() { var s = lastSt || {}; openFp("Diverter gate", "DV-001", [
    { k: "Position", v: s.diverter ? "DIVERT → Chute A" : "PASS → Chute B" },
    { k: "Mode", v: "Auto (barcode-routed)" }, { k: "Status", v: s.jam ? "JAM" : "OK", color: s.jam ? "var(--p1)" : "" }
  ], [{ label: "Close", onclick: closeFp }]); }
  function chuteFp(id) { var s = lastSt || {}, n = (id === "A" ? s.a : s.b) || 0; openFp("Sort chute " + id, "CHUTE-" + id, [
    { k: "Sorted count", v: n, color: "var(--data)" }, { k: "Capacity", v: "12 (demo)" },
    { k: "Level", v: Math.round(Math.min(n / 12, 1) * 100) + " %" }
  ], [{ label: "Close", onclick: closeFp }]); }

  function clearVis() { vis.forEach(function (v) { v.el.remove(); }); vis.clear(); }
  function reset() { simT = 0; lastIdx = -1; spark = []; alarms = []; playing = true; $("play").textContent = "⏸ Pause"; clearVis(); renderAlarms(); }
  function tick() {
    var now = performance.now(); if (lastTick == null) lastTick = now; var rd = Math.min((now - lastTick) / 1000, 0.5); lastTick = now;
    if (playing && frames.length) {
      simT += rd * speed; var st = frameAt(simT), mins = Math.max(simT / 60, 1e-6);
      if (spark.length < 400) spark.push((st.a + st.b) / mins);
      if (simT >= dur) { simT = 0; lastIdx = -1; spark = []; alarms = []; clearVis(); }
    }
    if (frames.length) render(frameAt(simT), rd);
  }
  setInterval(tick, 33);
  setInterval(function () { var d = new Date(); $("clock").textContent = d.toTimeString().slice(0, 8); }, 1000);

  function loadTrace(name) {
    return fetch("traces/" + name + ".json").then(function (r) { return r.json(); }).then(function (t) {
      frames = t.frames; dt = t.dt; layout = t.layout; dur = (frames.length - 1) * dt;
      $("scan").textContent = Math.round(dt * 1000) + " ms"; drawStatic(); reset();
    });
  }
  function init() {
    fetch("traces/index.json").then(function (r) { return r.json(); }).then(function (idx) {
      var sel = $("scenario");
      idx.traces.forEach(function (n) { var o = document.createElement("option"); o.value = n; o.textContent = n.replace(/_/g, " "); sel.appendChild(o); });
      sel.onchange = function () { loadTrace(sel.value); };
      return loadTrace(idx.traces[0]);
    }).catch(function () { $("hint").style.display = "block"; });
  }
  $("play").onclick = function () { playing = !playing; $("play").textContent = playing ? "⏸ Pause" : "▶ Play"; };
  $("speed").onchange = function (e) { speed = +e.target.value; };
  $("seek").oninput = function (e) { simT = (+e.target.value) / 1000 * dur; lastIdx = -1; spark = []; alarms = []; clearVis(); renderAlarms(); };
  $("b-start").onclick = function () { playing = true; $("play").textContent = "⏸ Pause"; };
  $("b-stop").onclick = function () { playing = false; $("play").textContent = "▶ Play"; };
  $("b-reset").onclick = function () { reset(); };
  $("b-est").onclick = function () { playing = false; $("play").textContent = "▶ Play"; addAlarm(2, "CELL-01", "E-stop actuated (operator)"); };
  $("b-ack").onclick = function () { alarms.forEach(function (a) { if (a.state === "UNACK") a.state = "ACK"; }); renderAlarms(); };
  $("fp-x").onclick = closeFp;
  $("fp-ov").onclick = function (e) { if (e.target === $("fp-ov")) closeFp(); };
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeFp(); });
  init();
})();
