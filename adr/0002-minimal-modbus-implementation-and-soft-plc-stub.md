# ADR-0002 — Minimal Modbus implementation and soft-PLC stub

- Status: Accepted
- Date: 2026-06-17
- Phase: 0 (PoC Connectivity)

## Context
Phase 0 needs a Modbus TCP proof path and a PLC that responds to it. Two upstream
options exist: depend on `pymodbus` for the transport, and depend on a running
OpenPLC Runtime v3 for control. Both add setup/version risk to a PoC whose
Definition of Done is "runs locally, verification script passes."

Development rules also require: never hallucinate upstream APIs, no fake
integrations, and any stub must be clearly named `stub` with TODO replacement
criteria.

## Decision
1. **Implement a minimal, standards-compliant Modbus TCP subset in-repo**
   (`protocol-gateway/modbus_tcp.py`): MBAP framing + function codes
   01/02/03/04/05/06/0F/10, a shared `ModbusDataStore`, threaded server, and a
   synchronous client. Pure stdlib.
2. **Provide a soft-PLC stub** (`plc/soft_plc.py`), explicitly named a stub for
   OpenPLC Runtime v3, that serves the store as a Modbus slave and runs the
   control scan.

## Rationale
- **Zero dependencies** → `python tests/verify_phase0.py` runs anywhere with no
  pip install, no version pinning, no Docker. Directly serves the DoD.
- **pymodbus API churn** across 2.x/3.x would make a committed verification
  script fragile; avoiding it removes that risk for Phase 0.
- The implementation is **real Modbus** (interoperable MBAP frames + standard
  function codes), not a fake transport — it satisfies "no fake integrations."
- The stub is **clearly labelled** and carries TODO criteria, satisfying the
  stub-naming rule.

## This is NOT a permanent choice
The transport and the PLC are deliberately swappable:
- **pymodbus**: the gateway only needs a client exposing
  `read_coils/read_discrete_inputs/read_holding_registers/read_input_registers/
  write_coil/write_register`. A `pymodbus`-backed adapter can drop in unchanged.
- **OpenPLC Runtime v3**: point `ModbusTCPClient` at the OpenPLC endpoint and
  delete the soft-PLC scan loop; the tag registry already uses OpenPLC-compatible
  master/slave semantics (ADR-0001).

### TODO — replacement criteria (Phase 1)
- [ ] Stand up OpenPLC Runtime v3 with an ST/LD program implementing
      `control_logic.scan()`.
- [ ] Map tags to OpenPLC `%IX/%QX` addresses; reconcile with the registry.
- [ ] Run `tests/verify_phase0.py` against OpenPLC (not the stub) and pass.
- [ ] Optionally add a `pymodbus` client adapter and run the same suite through it.

## Consequences
- We own ~300 lines of transport code (covered by the Gate-1 verification).
- The subset is intentionally limited; unsupported function codes return a proper
  Modbus exception response rather than silently misbehaving.

## Alternatives considered
- **Depend on pymodbus now:** rejected for Phase 0 (dependency + version risk);
  reconsidered in Phase 1 as an adapter.
- **Require OpenPLC for Phase 0:** rejected; raises the barrier to "runs locally"
  and couples the first proof to external setup. Deferred to Phase 1.
