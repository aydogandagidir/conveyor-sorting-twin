"""Soft-PLC STUB for OpenLogiTwin Phase 0.

STUB: a stand-in for OpenPLC Runtime v4. It runs the conveyor sorting control
scan (plc/control_logic.py) against a Modbus data store, and optionally exposes
that store as a Modbus TCP slave so the protocol gateway can connect as a master
— exactly the way it will later connect to OpenPLC.

TODO (replace this stub with real OpenPLC):
  - Map these tags to OpenPLC %IX/%QX addresses and load an ST/LD program that
    implements control_logic.scan().
  - Point the gateway at the OpenPLC Modbus endpoint instead of this server.
  - Delete the scan loop below; OpenPLC performs the scan.
See adr/0002-minimal-modbus-implementation-and-soft-plc-stub.md.
"""
from __future__ import annotations

import os
import sys
import threading
import time

# --- path bootstrap so cross-dir imports work when run standalone ------------
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "telemetry", "simulation"):
    _p = os.path.join(_ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

import control_logic  # noqa: E402
from modbus_tcp import ModbusDataStore, ModbusTCPServer  # noqa: E402

_TABLE_ATTR = {
    "coil": "coils",
    "discrete_input": "discrete_inputs",
    "holding_register": "holding_registers",
    "input_register": "input_registers",
}


def _read_tag(store: ModbusDataStore, tag):
    # PLC-side input conditioning: an inverted bool tag presents the logical
    # value to the control program (e.g. a NC fail-safe E-stop whose raw wire is
    # true=healthy is read as logical engaged=false). See ADR-0004.
    arr = getattr(store, _TABLE_ATTR[tag.table])
    with store.lock:
        raw = arr[tag.address]
    if tag.type == "bool":
        val = bool(raw)
        return (not val) if getattr(tag, "invert", False) else val
    return int(raw)


def _write_tag(store: ModbusDataStore, tag, value):
    arr = getattr(store, _TABLE_ATTR[tag.table])
    if tag.type == "bool":
        v = bool(value)
        if getattr(tag, "invert", False):
            v = not v
        with store.lock:
            arr[tag.address] = v
    else:
        with store.lock:
            arr[tag.address] = int(value) & 0xFFFF


class SoftPlc:
    def __init__(self, registry, store=None, scan_interval: float = 0.01, control=None):
        # `control` is any module/object exposing initial_state() and
        # scan(inputs, state) -> (outputs, state). Defaults to the Phase 0
        # control_logic so existing callers are unaffected; Phase 1 passes
        # control_logic_mvp.
        self.registry = registry
        self.store = store or ModbusDataStore()
        self.scan_interval = scan_interval
        self.control = control or control_logic
        self.state = self.control.initial_state()
        self._input_tags = registry.sim_to_plc()
        self._output_tags = {t.name: t for t in registry.plc_to_sim()}
        self._server = None
        self._thread = None
        self._stop = threading.Event()
        self.last_inputs = {}
        self.last_outputs = {}
        self.scan_count = 0

    def scan_once(self):
        inputs = {t.name: _read_tag(self.store, t) for t in self._input_tags}
        outputs, self.state = self.control.scan(inputs, self.state)
        for name, value in outputs.items():
            tag = self._output_tags.get(name)
            if tag is not None:
                _write_tag(self.store, tag, value)
        self.last_inputs, self.last_outputs = inputs, outputs
        self.scan_count += 1
        return inputs, outputs

    def serve(self, host: str = "127.0.0.1", port: int = 15502) -> int:
        """Expose the store over Modbus TCP. Returns the bound port."""
        self._server = ModbusTCPServer(self.store, host, port).start()
        return self._server.port

    def start(self) -> "SoftPlc":
        """Start the background scan loop."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return self

    def _run(self):
        while not self._stop.is_set():
            self.scan_once()
            time.sleep(self.scan_interval)

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        if self._server is not None:
            self._server.stop()
