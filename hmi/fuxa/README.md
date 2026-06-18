# hmi/fuxa

The **FUXA HMI project** (screens/widgets) is a **Phase 2** deliverable. Phase 1
delivers the **FUXA tag list** so the HMI can be wired when Phase 2 starts.

## Phase 1 deliverable: device tag list
`tag_list_sorting_cell_mvp.csv` — every MVP cell tag with its Modbus table,
function codes, 0-based address and conventional Modicon reference
(coils `0xxxx`, discrete inputs `1xxxx`, input registers `3xxxx`, holding
registers `4xxxx`). Source of truth: `protocol-gateway/config/tags.sorting_cell_mvp.json`.

Suggested HMI bindings:
- Buttons → `input.start_pb`, `input.stop_pb`, `input.reset_pb`, `input.estop` (coils)
- Lamps → `output.motor_conv_001_run`, `alarm.jam_001` (discrete inputs)
- Counters → `counter.sorted_chute_a`, `counter.sorted_chute_b` (input registers)

## Wiring it up (Phase 2)
1. Start the soft-PLC Modbus slave:
   ```bash
   python scripts/run_soft_plc.py        # 127.0.0.1:15502
   ```
   (Note: Phase 0/1 use the conveyor cell registries; load the MVP registry for
   this tag list.)
2. Bring up FUXA:
   ```bash
   docker compose --profile hmi up
   ```
3. In FUXA add a Modbus TCP device → `127.0.0.1:15502`, import the addresses from
   `tag_list_sorting_cell_mvp.csv`, then bind widgets.

No FUXA project JSON is committed yet by design (Phase 2).
