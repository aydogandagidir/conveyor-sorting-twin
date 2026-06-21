"""Export deterministic per-tick traces of scenarios for the web HMI (V0).

Runs scenarios through the same cell-aware ScenarioRunner the test suite uses and writes
`web/hmi/traces/<scenario>.json` — the exact data the browser HMI replays. Because the plant
(`scene_model.py`) is deterministic, the trace is reproducible: same scenario, same frames.

Stdlib only. Usage:
  python scripts/export_trace.py                  # the curated demo set
  python scripts/export_trace.py barcode_routing  # a single scenario
"""
import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.join(_ROOT, "simulation"))

import scenario_manager as sm        # noqa: E402
from scenario_runner import ScenarioRunner  # noqa: E402

OUT = os.path.join(_ROOT, "web", "hmi", "traces")

# Curated for the web demo: a clean sort, a fault/recovery, barcode routing, a dense advanced run.
DEMO = ["barcode_sorting_basic", "jam_recovery_basic", "barcode_routing", "dense_sort_advanced"]


def export(name):
    with open(sm.resolve(name), encoding="utf-8") as f:
        scenario = json.load(f)
    prof = sm._profile(scenario)
    runner = ScenarioRunner(prof["registry"], use_modbus=False,
                            control=prof["control"], dest_strategy=prof["dest_strategy"])
    try:
        result = runner.run(scenario, record_trace=True)
    finally:
        runner.close()
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f"{name}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result["trace"], f, separators=(",", ":"))
    print(f"  {name:24} -> {os.path.relpath(out, _ROOT)}  "
          f"({len(result['trace']['frames'])} frames, A/B={result['sorted_a']}/{result['sorted_b']})")
    return name


def main(argv):
    names = [a for a in argv if not a.startswith("-")] or DEMO
    index = []
    for n in names:
        index.append(export(n))
    # a small manifest so the web HMI can list available traces without a directory scan
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "index.json"), "w", encoding="utf-8") as f:
        json.dump({"traces": index}, f, indent=2)
    print(f"  manifest -> {os.path.relpath(os.path.join(OUT, 'index.json'), _ROOT)} ({len(index)} traces)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
