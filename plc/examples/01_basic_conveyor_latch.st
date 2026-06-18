(*
  01_basic_conveyor_latch — OpenPLC Structured Text (IEC 61131-3)

  Minimal conveyor start/stop latch with a fail-safe E-stop. The teaching baseline
  before the full sorting cell (02_sorting_cell_mvp.st).

  Maps to plc/control_logic_mvp.py (start/stop/E-stop portion).
  STATUS: provided as-is; validate in the OpenPLC editor before deploying.
*)
PROGRAM basic_conveyor_latch
VAR
    (* Inputs *)
    start_pb   AT %IX0.2 : BOOL;   (* momentary start *)
    stop_pb    AT %IX0.3 : BOOL;   (* momentary stop  *)
    estop_in   AT %IX0.5 : BOOL;   (* NC fail-safe wire: TRUE = healthy (ADR-0004) *)
    (* Outputs *)
    motor      AT %QX0.0 : BOOL;
    (* Internal *)
    running       : BOOL;
    estop_engaged : BOOL;
    start_edge    : R_TRIG;
END_VAR

    (* De-energize-to-trip: a broken/opened E-stop circuit reads FALSE -> engaged. *)
    estop_engaged := NOT estop_in;
    start_edge(CLK := start_pb);

    IF estop_engaged OR stop_pb THEN
        running := FALSE;
    ELSIF start_edge.Q THEN
        running := TRUE;
    END_IF;

    motor := running AND NOT estop_engaged;
END_PROGRAM
