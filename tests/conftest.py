"""pytest fixtures + import-path setup for OpenLogiTwin tests.

Adds the hyphenated source dirs to sys.path so `pytest tests/` can import the
modules, and provides shared fixtures. The standalone test scripts still run
without pytest (each sets up its own path); this just centralises it for pytest.
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TESTS = os.path.join(_ROOT, "tests")
for _p in (_TESTS, *(os.path.join(_ROOT, s) for s in ("protocol-gateway", "plc", "telemetry", "simulation"))):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import pytest  # noqa: E402

REGISTRY_MVP = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")


@pytest.fixture
def repo_root():
    return _ROOT


@pytest.fixture
def mvp_registry_path():
    return REGISTRY_MVP


@pytest.fixture
def modbus_pair():
    """A connected (store, client) Modbus TCP pair, torn down after the test."""
    from modbus_tcp import ModbusDataStore, ModbusTCPServer, ModbusTCPClient
    store = ModbusDataStore(size=64)
    srv = ModbusTCPServer(store, "127.0.0.1", 0).start()
    cli = ModbusTCPClient("127.0.0.1", srv.port).connect()
    yield store, cli
    cli.close()
    srv.stop()


@pytest.fixture
def sorting_cell_runner():
    """Factory for a ScenarioRunner on the MVP cell; auto-closes created runners."""
    from scenario_runner import ScenarioRunner
    created = []

    def _make(use_modbus=True):
        runner = ScenarioRunner(REGISTRY_MVP, use_modbus=use_modbus)
        created.append(runner)
        return runner

    yield _make
    for runner in created:
        try:
            runner.close()
        except Exception:
            pass
