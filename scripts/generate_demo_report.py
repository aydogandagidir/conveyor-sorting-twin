"""Render a self-contained HTML + Markdown report from demo results JSON.

Reads telemetry/exports/demo_results.json (produced by scripts/run_full_demo.py) and
writes demo_report.html and demo_report.md. The HTML is fully self-contained (inline
CSS, CSS bar chart — no external assets), so it opens offline in any browser.

Usage:
  python scripts/generate_demo_report.py [results.json] [--out-dir=DIR]
"""
import html as _html
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPORTS = os.path.join(_ROOT, "telemetry", "exports")
DEFAULT_RESULTS = os.path.join(EXPORTS, "demo_results.json")


def _bar(value, maxv, cls):
    width = 0 if maxv <= 0 else round(value / maxv * 280)
    return f'<span class="seg {cls}" style="width:{width}px" title="{value}"></span>'


def as_html(data) -> str:
    totals = data["totals"]
    scenarios = data["scenarios"]
    maxv = max([1] + [s["sorted_a"] + s["sorted_b"] for s in scenarios])

    cards = "".join(
        f'<div class="card"><div class="num">{v}</div><div class="lbl">{k}</div></div>'
        for k, v in [
            ("scenarios", totals["scenarios"]),
            ("expect passed", f'{totals["expect_passed"]}/{totals["scenarios"]}'),
            ("parcels sorted", totals["parcels_sorted"]),
            ("parcels/min", totals["parcels_per_min"]),
            ("jams", totals["jams"]),
            ("sim seconds", totals["sim_seconds"]),
        ]
    )

    chart_rows = ""
    table_rows = ""
    for s in scenarios:
        name = _html.escape(s["name"])
        chart_rows += (
            f'<div class="crow"><span class="clbl">{name}</span>'
            f'<span class="track">{_bar(s["sorted_a"], maxv, "a")}{_bar(s["sorted_b"], maxv, "b")}</span>'
            f'<span class="cval">A {s["sorted_a"]} / B {s["sorted_b"]}</span></div>'
        )
        badge = '<span class="ok">PASS</span>' if s["expect_pass"] else '<span class="bad">FAIL</span>'
        jam = "yes" if s["jam_triggered"] else "—"
        table_rows += (
            f"<tr><td>{name}</td><td>{s['sorted_a']}</td><td>{s['sorted_b']}</td>"
            f"<td>{s['parcels']}</td><td>{jam}</td><td>{s['sim_seconds']}</td><td>{badge}</td></tr>"
        )

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>OpenLogiTwin Demo Report</title>
<style>
  body{{font:14px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;background:#0f172a;color:#e2e8f0}}
  .wrap{{max-width:880px;margin:0 auto;padding:32px}}
  h1{{font-size:22px;margin:0 0 4px}} .sub{{color:#94a3b8;margin:0 0 24px}}
  .cards{{display:flex;flex-wrap:wrap;gap:12px;margin-bottom:28px}}
  .card{{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:14px 18px;min-width:120px}}
  .num{{font-size:22px;font-weight:700}} .lbl{{color:#94a3b8;font-size:12px;text-transform:uppercase;letter-spacing:.04em}}
  h2{{font-size:16px;margin:24px 0 10px;border-bottom:1px solid #334155;padding-bottom:6px}}
  .crow{{display:flex;align-items:center;gap:10px;margin:6px 0}}
  .clbl{{width:180px;color:#cbd5e1;font-size:13px}}
  .track{{flex:1;display:flex;height:18px;background:#0b1220;border-radius:4px;overflow:hidden}}
  .seg.a{{background:#22c55e}} .seg.b{{background:#3b82f6}}
  .cval{{width:110px;text-align:right;color:#94a3b8;font-size:12px}}
  table{{width:100%;border-collapse:collapse;margin-top:8px}}
  th,td{{padding:8px 10px;text-align:left;border-bottom:1px solid #334155}}
  th{{color:#94a3b8;font-size:12px;text-transform:uppercase}}
  .ok{{color:#22c55e;font-weight:700}} .bad{{color:#ef4444;font-weight:700}}
  .legend{{color:#94a3b8;font-size:12px;margin:8px 0 0}}
  .legend b.a{{color:#22c55e}} .legend b.b{{color:#3b82f6}}
  footer{{color:#64748b;font-size:12px;margin-top:28px}}
</style></head><body><div class="wrap">
  <h1>OpenLogiTwin — Conveyor Sorting Cell Demo</h1>
  <p class="sub">Generated {_html.escape(str(data.get("generated_at", "")))} · deterministic scenario suite</p>
  <div class="cards">{cards}</div>
  <h2>Sorting throughput by scenario</h2>
  <div class="chart">{chart_rows}</div>
  <p class="legend"><b class="a">■</b> CHUTE_A &nbsp; <b class="b">■</b> CHUTE_B</p>
  <h2>Scenario results</h2>
  <table><thead><tr><th>scenario</th><th>A</th><th>B</th><th>parcels</th><th>jam</th><th>sim s</th><th>expect</th></tr></thead>
  <tbody>{table_rows}</tbody></table>
  <footer>OpenLogiTwin · Modbus TCP soft-PLC · self-contained report (no external assets)</footer>
</div></body></html>
"""


def as_markdown(data) -> str:
    t = data["totals"]
    lines = [
        "# OpenLogiTwin — Demo Report",
        "",
        f"Generated: {data.get('generated_at', '')}",
        "",
        f"- Scenarios: **{t['scenarios']}** (expect passed {t['expect_passed']}/{t['scenarios']})",
        f"- Parcels sorted: **{t['parcels_sorted']}** (A {t['sorted_a']} / B {t['sorted_b']})",
        f"- Throughput: **{t['parcels_per_min']}** parcels/min · jams: {t['jams']} · sim {t['sim_seconds']}s",
        "",
        "| scenario | A | B | parcels | jam | sim s | expect |",
        "|---|---|---|---|---|---|---|",
    ]
    for s in data["scenarios"]:
        jam = "yes" if s["jam_triggered"] else "—"
        verdict = "PASS" if s["expect_pass"] else "FAIL"
        lines.append(f"| {s['name']} | {s['sorted_a']} | {s['sorted_b']} | {s['parcels']} | {jam} | {s['sim_seconds']} | {verdict} |")
    return "\n".join(lines) + "\n"


def generate(results_path=DEFAULT_RESULTS, out_dir=EXPORTS):
    with open(results_path, encoding="utf-8") as f:
        data = json.load(f)
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "demo_report.html")
    md_path = os.path.join(out_dir, "demo_report.md")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(as_html(data))
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(as_markdown(data))
    return html_path, md_path


def main(argv):
    results = DEFAULT_RESULTS
    out_dir = EXPORTS
    for a in argv:
        if a.startswith("--out-dir="):
            out_dir = a.split("=", 1)[1]
        elif not a.startswith("--"):
            results = a if os.path.isabs(a) else os.path.join(_ROOT, a)
    html_path, md_path = generate(results, out_dir)
    print(f"wrote {os.path.relpath(html_path, _ROOT)} and {os.path.relpath(md_path, _ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
