# Tag Map — MVP Sorting Cell (Phase 1)

Canonical registry: `protocol-gateway/config/tags.sorting_cell_mvp.json`.
FUXA/SCADA device list: `hmi/fuxa/tag_list_sorting_cell_mvp.csv`.

Destinations: `CHUTE_A = 1`, `CHUTE_B = 2`.

## Inputs to PLC (`sim_to_plc`, gateway writes)
| Tag | Type | Modbus | Addr | Notes |
|-----|------|--------|------|-------|
| `sensor.pe_001` | bool | coil | 0 | Infeed / barcode scan photo-eye |
| `sensor.pe_002` | bool | coil | 1 | Pre-diverter photo-eye |
| `input.start_pb` | bool | coil | 2 | Momentary start |
| `input.stop_pb` | bool | coil | 3 | Momentary stop |
| `input.reset_pb` | bool | coil | 4 | Momentary reset (clears jam) |
| `input.estop` | bool | coil | 5 | Emergency stop (true = engaged) |
| `data.parcel_destination` | uint16 | holding_register | 0 | 1=CHUTE_A, 2=CHUTE_B |

## Outputs from PLC (`plc_to_sim`, gateway reads)
| Tag | Type | Modbus | Addr | Notes |
|-----|------|--------|------|-------|
| `output.motor_conv_001_run` | bool | discrete_input | 0 | Conveyor motor run |
| `output.diverter_dv_001_extend` | bool | discrete_input | 1 | Extended ⇒ route CHUTE_A |
| `alarm.jam_001` | bool | discrete_input | 2 | Latched jam |
| `counter.sorted_chute_a` | uint16 | input_register | 0 | Sorted to A |
| `counter.sorted_chute_b` | uint16 | input_register | 1 | Sorted to B |

## Control behaviour (`plc/control_logic_mvp.py`)
- **Start/Stop/Reset/E-stop**: start latches running; stop or E-stop drops it;
  reset clears the jam latch (operator also clears the stuck parcel).
- **Routing**: latched on pe_002 rising edge from `data.parcel_destination`
  (A ⇒ diverter extend; B ⇒ straight).
- **Counting**: on pe_002 falling edge (parcel cleared the diverter). A jammed
  parcel never produces a falling edge, so it is not counted.
- **Jam**: pe_002 blocked > `JAM_SCAN_LIMIT` scans (~1.0 s at dt=0.05) while
  running ⇒ `alarm.jam_001` latched, motor stopped. Cleared by `input.reset_pb`.

## Phase 0 ↔ Phase 1 tag naming
Phase 0 used the `tags.conveyor_sorting_cell.json` registry (`sensor.preDivert`,
`motor.conveyor`, …). Phase 1 introduces the ISA-style MVP names above in a new
registry; both load through the same `tag_registry.py` model and Modbus
master/slave semantics. Phase 0 remains intact and verifiable.
