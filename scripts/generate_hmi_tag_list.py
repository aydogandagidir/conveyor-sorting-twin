"""Generate the FUXA/SCADA device tag list from the tag registry (single source of truth).

Prevents drift between protocol-gateway/config/tags.sorting_cell_mvp.json and
hmi/fuxa/tag_list_sorting_cell_mvp.csv. Run with no args to (re)write the CSV;
run with --check to fail if the committed CSV is stale.

Usage:
  python scripts/generate_hmi_tag_list.py            # write the CSV
  python scripts/generate_hmi_tag_list.py --check    # exit 1 if CSV is out of date
"""
import csv
import io
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "protocol-gateway"))

from tag_registry import TagRegistry  # noqa: E402

REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
CSV_PATH = os.path.join(_ROOT, "hmi", "fuxa", "tag_list_sorting_cell_mvp.csv")

HEADER = ["tag", "direction", "modbus_table", "read_fc", "write_fc",
          "address_0based", "modicon_ref", "data_type", "description"]

_READ_FC = {"coil": 1, "discrete_input": 2, "holding_register": 3, "input_register": 4}
_WRITE_FC = {"coil": 5, "holding_register": 6}                      # others are read-only
_MODICON_BASE = {"coil": 1, "discrete_input": 100001, "holding_register": 400001, "input_register": 300001}


def rows(registry):
    out = []
    for t in registry:
        out.append([
            t.name, t.direction, t.table,
            _READ_FC[t.table], _WRITE_FC.get(t.table, ""),
            t.address, f"{_MODICON_BASE[t.table] + t.address:06d}",
            t.type, t.description,
        ])
    return out


def as_string():
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(HEADER)
    w.writerows(rows(TagRegistry.from_file(REGISTRY)))
    return buf.getvalue()


def main(argv):
    generated = as_string()
    if "--check" in argv:
        current = open(CSV_PATH, encoding="utf-8").read() if os.path.exists(CSV_PATH) else ""
        if current != generated:
            print("DRIFT: hmi/fuxa/tag_list_sorting_cell_mvp.csv is out of date; run "
                  "`python scripts/generate_hmi_tag_list.py`")
            return 1
        print("OK: FUXA tag list matches the registry")
        return 0
    with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
        f.write(generated)
    print(f"wrote {os.path.relpath(CSV_PATH, _ROOT)} ({len(rows(TagRegistry.from_file(REGISTRY)))} tags)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
