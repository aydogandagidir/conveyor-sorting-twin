"""Run the soft-PLC Modbus TCP slave standalone (Ctrl+C to stop).

This is the STUB stand-in for OpenPLC Runtime v4. Point any Modbus master
(the gateway, a SCADA, or a Modbus poll tool) at the printed host:port.

Env overrides:
  OLTWIN_HOST      (default 127.0.0.1; use 0.0.0.0 in a container)
  OLTWIN_PORT      (default 15502)
  OLTWIN_REGISTRY  (default conveyor_sorting_cell) — a cell name under
                   protocol-gateway/config/tags.<name>.json, or a path
  OLTWIN_CONTROL   (default control_logic) — control module: control_logic,
                   control_logic_mvp, or control_logic_advanced
"""
import importlib
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry   # noqa: E402
from soft_plc import SoftPlc           # noqa: E402

_CONFIG = os.path.join(_ROOT, "protocol-gateway", "config")


def resolve_registry(spec):
    candidates = [spec, os.path.join(_CONFIG, f"tags.{spec}.json"), os.path.join(_ROOT, spec)]
    for c in candidates:
        if os.path.exists(c):
            return c
    raise FileNotFoundError(f"registry not found: {spec!r}")


def build_plc():
    reg_spec = os.environ.get("OLTWIN_REGISTRY", "conveyor_sorting_cell")
    control_name = os.environ.get("OLTWIN_CONTROL", "control_logic")
    registry = TagRegistry.from_file(resolve_registry(reg_spec))
    control = importlib.import_module(control_name)
    return SoftPlc(registry, control=control), reg_spec, control_name


def main():
    host = os.environ.get("OLTWIN_HOST", "127.0.0.1")
    port = int(os.environ.get("OLTWIN_PORT", "15502"))
    plc, reg_spec, control_name = build_plc()
    bound = plc.serve(host, port)
    plc.start()
    print(f"Soft-PLC (STUB for OpenPLC) Modbus TCP slave on {host}:{bound} "
          f"[cell={reg_spec} control={control_name}]")
    print("Scan loop running. Ctrl+C to stop.")
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nstopping soft-PLC...")
        plc.stop()


if __name__ == "__main__":
    main()
