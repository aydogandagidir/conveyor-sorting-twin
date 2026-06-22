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
  var vis = new Map(), spark = [], alarms = [], alarmSeq = 0, level = 2;
  var liveMode = false, ws = null, prevLive = null, liveTrend = [];

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
    var parcels = f.parcels.map(function (p) { var q = gm.get(p.id); return { id: p.id, x: q ? p.x + (q.x - p.x) * fr : p.x, dest: p.dest, stuck: q ? q.stuck : p.stuck }; });
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
    var clk = liveMode ? (st.t || 0) : simT;
    var mins = Math.max(clk / 60, 1e-6), tput = Math.round((st.a + st.b) / mins);
    $("tp").textContent = tput; ptr("tp-ptr", tput, 50); band("tp-band", 8, 36, 50);
    var tot = Math.max(1, st.a + st.b, frames.length ? frames[frames.length - 1].a + frames[frames.length - 1].b : 1);
    ptr("a-ptr", st.a, tot); ptr("b-ptr", st.b, tot);
    $("rt").textContent = fmt(clk);
    if (liveMode) {
      $("time").textContent = "LIVE · " + clk.toFixed(1) + " s";
      drawLiveTrend(); drawSpark();
    } else {
      $("seek").value = Math.round(simT / dur * 1000) || 0;
      $("time").textContent = simT.toFixed(1) + " / " + dur.toFixed(1) + " s";
      drawTrend(); drawSpark();
      logTransitions(st.i);
    }
    if (level === 1) updateLine(st); else if (level === 3) updateIO(st);
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
    if (liveMode) return;   // live frames drive render via the WebSocket
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

  function applyTheme(t) {
    if (t === "dark") document.documentElement.setAttribute("data-theme", "dark");
    else document.documentElement.removeAttribute("data-theme");
    try { localStorage.setItem("oltwin-theme", t); } catch (e) {}
    if (layout) { clearVis(); drawStatic(); }   // SVG colours read CSS vars at draw time
    if ($("view-line")) { $("view-line").innerHTML = ""; if (level === 1) { drawLine(); if (lastSt) updateLine(lastSt); } }
  }

  /* ---- display hierarchy: L1 line overview / L2 cell mimic / L3 I/O detail ---- */
  function setLevel(n) {
    level = n;
    $("cell").style.display = n === 2 ? "" : "none";
    $("view-line").style.display = n === 1 ? "" : "none";
    $("view-io").style.display = n === 3 ? "" : "none";
    ["lv1", "lv2", "lv3"].forEach(function (id, i) { $(id).className = (i + 1 === n) ? "cur" : ""; });
    $("crumb-leaf").textContent = n === 1 ? "Line overview" : n === 3 ? "I/O detail" : "Sorting Cell";
    if (n === 1 && !$("view-line").childElementCount) drawLine();
    if (lastSt) { if (n === 1) updateLine(lastSt); else if (n === 3) updateIO(lastSt); }
  }
  function drawLine() {
    var s = $("view-line"); s.innerHTML = "";
    var L = cssv("--line"), L2 = cssv("--line-2"), INK = cssv("--ink"), INK2 = cssv("--ink-2"), BG = cssv("--bg"), D = cssv("--data");
    function block(x, y, w, h, fp) { var r = el("rect", { x: x, y: y, width: w, height: h, fill: BG, stroke: L, "stroke-width": 1.4 }); if (fp) { r.setAttribute("data-fp", ""); r.onclick = function () { setLevel(2); }; } s.appendChild(r); }
    function arrow(x1, y1, x2, y2) { s.appendChild(el("line", { x1: x1, y1: y1, x2: x2, y2: y2, stroke: L2, "stroke-width": 1.4 })); s.appendChild(el("path", { d: "M" + x2 + " " + y2 + " l-9 -4 m9 4 l-9 4", fill: "none", stroke: L2, "stroke-width": 1.4 })); }
    s.appendChild(txt(60, 34, "LINE 01 — OVERVIEW", INK2, 12));
    block(60, 196, 150, 88); s.appendChild(txt(135, 246, "INFEED", INK, 13, "middle"));
    arrow(210, 240, 298, 240);
    block(300, 168, 230, 150, true);
    s.appendChild(txt(415, 196, "SORTING CELL", INK, 13, "middle")); s.appendChild(txt(415, 214, "CONV-001 · DV-001", INK2, 10, "middle"));
    s.appendChild(txt(318, 252, "Status", INK2, 11)); var ls = txt(512, 252, "—", INK, 12, "end"); ls.setAttribute("id", "line-status"); ls.setAttribute("font-weight", "600"); s.appendChild(ls);
    s.appendChild(txt(318, 276, "Throughput", INK2, 11)); var lt = txt(512, 276, "0 /min", D, 12, "end"); lt.setAttribute("id", "line-tput"); lt.setAttribute("font-weight", "600"); s.appendChild(lt);
    s.appendChild(el("g", { id: "line-alarm" }));
    arrow(530, 220, 658, 166); arrow(530, 252, 658, 296);
    block(660, 130, 200, 76); s.appendChild(txt(674, 158, "CHUTE A", INK2, 12)); var ca = txt(844, 178, "0", D, 20, "end"); ca.setAttribute("id", "line-ca"); ca.setAttribute("font-weight", "600"); s.appendChild(ca);
    block(660, 258, 200, 76); s.appendChild(txt(674, 286, "CHUTE B", INK2, 12)); var cb = txt(844, 306, "0", D, 20, "end"); cb.setAttribute("id", "line-cb"); cb.setAttribute("font-weight", "600"); s.appendChild(cb);
    s.appendChild(txt(415, 344, "click the cell to drill down  ▸ L2", INK2, 10, "middle"));
  }
  function updateLine(st) {
    var ls = $("line-status"); if (ls) { ls.textContent = st.jam ? "JAM" : st.motor ? "RUN" : "STOP"; ls.setAttribute("fill", st.jam ? cssv("--p1") : cssv("--ink")); }
    var mins = Math.max(simT / 60, 1e-6);
    if ($("line-tput")) $("line-tput").textContent = Math.round((st.a + st.b) / mins) + " /min";
    if ($("line-ca")) $("line-ca").textContent = st.a; if ($("line-cb")) $("line-cb").textContent = st.b;
    var g = $("line-alarm"); if (g) { g.innerHTML = ""; if (st.jam) { g.appendChild(el("path", { d: "M324 250 l11 19 l-22 0 z", fill: cssv("--p1") })); g.appendChild(txt(324, 266, "!", "#fff", 12, "middle")); } }
  }
  function updateIO(st) {
    var rows = [
      ["sensor.pe_001", "Discrete In", "coil 0", st.pe1, st.pe1 ? "BLOCKED" : "clear", 0],
      ["sensor.pe_002", "Discrete In", "coil 1", st.pe2, st.pe2 ? "BLOCKED" : "clear", 0],
      ["output.motor_conv_001_run", "Discrete Out", "DI 0", st.motor, st.motor ? "RUN" : "STOP", 0],
      ["output.diverter_dv_001_extend", "Discrete Out", "DI 1", st.diverter, st.diverter ? "EXTEND" : "retract", 0],
      ["alarm.jam_001", "Discrete Out", "DI 2", st.jam, st.jam ? "ALARM" : "ok", st.jam ? 1 : 0],
      ["counter.sorted_chute_a", "Int16", "IR 0", st.a, "—", 0],
      ["counter.sorted_chute_b", "Int16", "IR 1", st.b, "—", 0]
    ];
    var h = '<div class="h2">Sorting cell — live I/O image · sorting_cell_mvp registry</div>' +
      '<table class="io-t"><thead><tr><th>Tag</th><th>Type</th><th>Address</th><th>Value</th><th>State</th></tr></thead><tbody>';
    rows.forEach(function (r) {
      var v = typeof r[3] === "boolean" ? (r[3] ? "1" : "0") : r[3];
      h += "<tr><td class='tag'>" + r[0] + "</td><td>" + r[1] + "</td><td class='addr'>" + r[2] + "</td><td class='val'>" + v + "</td><td" + (r[5] ? " style='color:var(--p1);font-weight:600'" : " class='st0'") + ">" + r[4] + "</td></tr>";
    });
    $("view-io").innerHTML = h + "</tbody></table>";
  }

  /* ---- live mode: stream the real twin over WebSocket (scripts/hmi_server.py) ---- */
  function drawLiveTrend() {
    var c = $("trend"), x = c.getContext("2d"), W = c.width, H = c.height, n = liveTrend.length;
    x.clearRect(0, 0, W, H); if (n < 2) return;
    var maxN = Math.max(1, liveTrend[n - 1].a + liveTrend[n - 1].b);
    var xs = function (i) { return i / (n - 1) * (W - 6) + 3; }, ys = function (v) { return H - 6 - v / maxN * (H - 14); };
    x.strokeStyle = rgba(cssv("--line"), .5); x.lineWidth = 1;
    for (var gy = 0; gy <= 2; gy++) { var yy = 6 + gy * (H - 12) / 2; x.beginPath(); x.moveTo(3, yy); x.lineTo(W - 3, yy); x.stroke(); }
    [["b", cssv("--ink-2")], ["a", cssv("--data")]].forEach(function (s) {
      x.beginPath(); for (var i = 0; i < n; i++) { var px = xs(i), py = ys(liveTrend[i][s[0]]); i ? x.lineTo(px, py) : x.moveTo(px, py); } x.strokeStyle = s[1]; x.lineWidth = 1.6; x.stroke();
    });
  }
  function liveFrame(f) {
    if (prevLive) {
      if (f.a > prevLive.a) addAlarm(4, "CHUTE-A", "Parcel sorted to Chute A", true, f.t);
      if (f.b > prevLive.b) addAlarm(4, "CHUTE-B", "Parcel sorted to Chute B", true, f.t);
      if (f.jam && !prevLive.jam) addAlarm(1, "DV-001", "Conveyor jam — sorter blocked", false, f.t);
      if (!f.jam && prevLive.jam) returnAlarm("DV-001");
      if (f.estop && !prevLive.estop) addAlarm(1, "CELL-01", "E-stop actuated (operator)", false, f.t);
      if (!f.estop && prevLive.estop) returnAlarm("CELL-01");
    }
    prevLive = f;
    liveTrend.push({ a: f.a, b: f.b }); if (liveTrend.length > 300) liveTrend.shift();
    var mins = Math.max(f.t / 60, 1e-6); if (spark.length < 400) spark.push((f.a + f.b) / mins);
    render(f, 0.1);
  }
  function setMode(label, on) {
    $("mode").textContent = label;
    $("go-live").textContent = on ? "■ Stop live" : "● Go live";
    ["scenario", "play", "speed", "seek"].forEach(function (id) { $(id).disabled = on; });
    $("b-jam").style.display = on ? "" : "none";
    var d = $("comms-dot"); if (d) d.style.background = on ? "var(--on)" : "var(--off)";   // live link bright, replay dim
  }
  function sendCmd(cmd) { if (ws && liveMode) try { ws.send(JSON.stringify({ cmd: cmd })); } catch (e) {} }
  function liveErr(url) { var h = $("hint"); h.textContent = "No live server at " + url + " — run  python scripts/hmi_server.py  on that host."; h.style.display = "block"; if (ws) { try { ws.close(); } catch (e) {} } ws = null; liveMode = false; setMode("REPLAY", false); }
  function stopLive() { liveMode = false; if (ws) { try { ws.close(); } catch (e) {} ws = null; } setMode("REPLAY", false); spark = []; clearVis(); if (layout) reset(); }
  function goLive() {
    if (liveMode || ws) { stopLive(); return; }
    var url = "ws://" + (location.hostname || "localhost") + ":8765";
    $("hint").style.display = "none";
    try { ws = new WebSocket(url); } catch (e) { liveErr(url); return; }
    ws.onopen = function () { liveMode = true; prevLive = null; liveTrend = []; spark = []; alarms = []; renderAlarms(); clearVis(); setMode("LIVE", true); };
    ws.onmessage = function (ev) { try { liveFrame(JSON.parse(ev.data)); } catch (e) {} };
    ws.onclose = function () { ws = null; if (liveMode) { liveMode = false; setMode("REPLAY", false); } };
    ws.onerror = function () { liveErr(url); };
  }

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
      sel.onchange = function () { loadTrace(sel.value).catch(function () { $("hint").style.display = "block"; }); };
      return loadTrace(idx.traces[0]);
    }).catch(function () { $("hint").style.display = "block"; });
  }
  $("play").onclick = function () { playing = !playing; $("play").textContent = playing ? "⏸ Pause" : "▶ Play"; };
  $("speed").onchange = function (e) { speed = +e.target.value; };
  $("seek").oninput = function (e) { simT = (+e.target.value) / 1000 * dur; lastIdx = Math.min(Math.floor(simT / dt), frames.length - 1); spark = []; alarms = []; clearVis(); renderAlarms(); };
  $("b-start").onclick = function () { if (liveMode) return sendCmd("start"); playing = true; $("play").textContent = "⏸ Pause"; };
  $("b-stop").onclick = function () { if (liveMode) return sendCmd("stop"); playing = false; $("play").textContent = "▶ Play"; };
  $("b-reset").onclick = function () { if (liveMode) return sendCmd("reset"); reset(); };
  $("b-est").onclick = function () { if (liveMode) return sendCmd("estop"); playing = false; $("play").textContent = "▶ Play"; addAlarm(1, "CELL-01", "E-stop actuated (operator)"); };
  $("b-jam").onclick = function () { sendCmd("jam"); };
  $("go-live").onclick = goLive;
  $("b-ack").onclick = function () { alarms.forEach(function (a) { if (a.state === "UNACK") a.state = "ACK"; }); renderAlarms(); };
  $("fp-x").onclick = closeFp;
  $("fp-ov").onclick = function (e) { if (e.target === $("fp-ov")) closeFp(); };
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeFp(); });
  $("theme").onclick = function () { applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark"); };
  $("lv1").onclick = function () { setLevel(1); }; $("lv2").onclick = function () { setLevel(2); }; $("lv3").onclick = function () { setLevel(3); };
  try { if (localStorage.getItem("oltwin-theme") === "dark") document.documentElement.setAttribute("data-theme", "dark"); } catch (e) {}
  init();
})();
