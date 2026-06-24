# Architecture Decision Records

Each ADR captures one significant decision — its context, the choice made, and the trade-offs —
in the lightweight [Michael Nygard format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions).
They explain *why* the project is built the way it is; the code shows *what*.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-phase0-architecture-and-modbus-topology.md) | Phase 0 architecture & Modbus topology | Accepted |
| [0002](0002-minimal-modbus-implementation-and-soft-plc-stub.md) | Minimal in-repo Modbus + soft-PLC stub (zero deps) | Accepted |
| [0003](0003-phase1-scene-adapter-and-mvp-cell.md) | Phase 1 scene adapter & MVP sorting cell | Accepted |
| [0004](0004-estop-failsafe-and-tag-inversion.md) | E-stop NC fail-safe via tag inversion at the I/O boundary | Accepted |
| [0005](0005-multi-parcel-destination-tracking.md) | Multi-parcel destination tracking (FIFO ring) | Accepted |
| [0006](0006-opcua-adapter.md) | OPC UA adapter (second protocol) | Accepted |
| [0007](0007-mqtt-telemetry.md) | MQTT telemetry (third protocol) | Accepted |
| [0008](0008-modbus-robustness.md) | Modbus client robustness: auto-reconnect + multi-word types | Accepted |
| [0009](0009-live-hmi-websocket.md) | Live HMI transport: hand-rolled WebSocket, stdlib only | Accepted |

**Status legend:** *Accepted* — in effect. A decision that changes a previous one gets a **new** ADR
that references (supersedes) the old one; ADRs are an append-only log, not edited after acceptance.
