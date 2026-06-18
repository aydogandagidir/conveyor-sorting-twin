(*
  02_sorting_cell_mvp — OpenPLC Structured Text (IEC 61131-3)

  Full conveyor sorting cell, the ST port of plc/control_logic_mvp.py:
    - start/stop/reset/E-stop control (E-stop NC fail-safe, ADR-0004)
    - routing latched on the RISING edge of pe_002 from the barcode word
    - counting on the FALLING edge of pe_002 (parcel cleared the diverter)
    - jam detection via a 1 s on-delay timer; latch + motor stop
    - diverter latch cleared on E-stop / Stop (never energized while stopped)

  Line references below point at the equivalent control_logic_mvp.py logic.
  STATUS: provided as-is; validate in the OpenPLC editor before deploying.
*)
PROGRAM sorting_cell_mvp
VAR
    (* Inputs (master-writable coils / holding register) *)
    pe_001    AT %IX0.0 : BOOL;   (* infeed / barcode scan photo-eye *)
    pe_002    AT %IX0.1 : BOOL;   (* pre-diverter photo-eye *)
    start_pb  AT %IX0.2 : BOOL;
    stop_pb   AT %IX0.3 : BOOL;
    reset_pb  AT %IX0.4 : BOOL;
    estop_in  AT %IX0.5 : BOOL;   (* NC fail-safe wire: TRUE = healthy *)
    barcode   AT %IW0   : UINT;   (* 1 = CHUTE_A, 2 = CHUTE_B *)
    (* Outputs (master-readable discrete inputs / input registers) *)
    motor     AT %QX0.0 : BOOL;
    diverter  AT %QX0.1 : BOOL;   (* extended => route to CHUTE_A *)
    jam       AT %QX0.2 : BOOL;
    count_a   AT %QW0   : UINT;
    count_b   AT %QW1   : UINT;
    (* Internal state *)
    running       : BOOL;
    pending       : UINT;         (* 0 = none, 1 = A, 2 = B *)
    estop_engaged : BOOL;
    start_edge    : R_TRIG;
    reset_edge    : R_TRIG;
    pe2_rise      : R_TRIG;
    pe2_fall      : F_TRIG;
    jam_timer     : TON;
END_VAR

    estop_engaged := NOT estop_in;            (* ADR-0004 fail-safe inversion *)
    start_edge(CLK := start_pb);
    reset_edge(CLK := reset_pb);
    pe2_rise(CLK := pe_002);
    pe2_fall(CLK := pe_002);

    (* Reset acknowledges + clears the jam latch and pending decision (mvp:72-76) *)
    IF reset_edge.Q THEN
        jam := FALSE;
        pending := 0;
        diverter := FALSE;
    END_IF;

    (* E-stop / Stop drop running and de-energize the diverter latch (mvp:80-82) *)
    IF estop_engaged OR stop_pb THEN
        running := FALSE;
        diverter := FALSE;
    END_IF;

    (* Start latches only when safe (mvp:85-86) *)
    IF start_edge.Q AND NOT estop_engaged AND NOT jam THEN
        running := TRUE;
    END_IF;

    (* Jam detection: pe_002 blocked > 1 s while the motor should run (mvp:91-98) *)
    jam_timer(IN := running AND NOT estop_engaged AND NOT jam AND pe_002, PT := T#1s);
    IF jam_timer.Q THEN
        jam := TRUE;
        running := FALSE;
    END_IF;

    (* Routing decision on the rising edge of pe_002 (mvp:101-103) *)
    IF pe2_rise.Q AND running AND NOT estop_engaged AND NOT jam THEN
        IF barcode = 1 THEN
            pending := 1;
            diverter := TRUE;
        ELSE
            pending := 2;
            diverter := FALSE;
        END_IF;
    END_IF;

    (* Count on the falling edge of pe_002 (mvp:106-111) *)
    IF pe2_fall.Q AND running AND NOT estop_engaged AND NOT jam AND pending <> 0 THEN
        IF pending = 1 THEN
            count_a := count_a + 1;
        ELSE
            count_b := count_b + 1;
        END_IF;
        pending := 0;
    END_IF;

    motor := running AND NOT estop_engaged AND NOT jam;
    IF NOT motor THEN
        diverter := FALSE;
    END_IF;
END_PROGRAM
