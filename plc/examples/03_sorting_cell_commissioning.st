(*
  03_sorting_cell_commissioning — OpenPLC Structured Text (IEC 61131-3)

  A *virtual-commissioning* variant of 02_sorting_cell_mvp.st: identical control
  logic, but every PLC INPUT is mapped to a master-WRITABLE Modbus location so an
  external simulator (the OpenLogiTwin gateway) can drive the PLC over Modbus.

  Why: OpenPLC exposes %IX/%IW as Modbus discrete-inputs/input-registers, which a
  master can only READ. Standard Modbus has no way to drive them. So here the inputs
  live on coils (%QX) and a holding register (%QW) — both master-writable (FC05/06):

    Master WRITES (drives the PLC):           Master READS (observes the PLC):
      pe_001   %QX1.0  coil  8                  motor    %QX0.0  coil 0
      pe_002   %QX1.1  coil  9                  diverter %QX0.1  coil 1
      start_pb %QX1.2  coil 10                  jam      %QX0.2  coil 2
      stop_pb  %QX1.3  coil 11                  count_a  %QW0    hold reg 0
      reset_pb %QX1.4  coil 12                  count_b  %QW2    hold reg 2
      estop_in %QX1.5  coil 13
      barcode  %QW1    hold reg 1

  Reading an output coil (%QX) inside the program is legal IEC 61131-3; using it as a
  master-writable input is the standard trick for driving a PLC in virtual commissioning.

  STATUS: compiles and runs on OpenPLC Runtime v3 (verified 2026-06-20); behavioural
  equivalence to control_logic_mvp.py is checked by tests/test_openplc_behavioral.py.
*)
PROGRAM sorting_cell_comm
VAR
    (* Outputs the master READS *)
    motor     AT %QX0.0 : BOOL;
    diverter  AT %QX0.1 : BOOL;
    jam       AT %QX0.2 : BOOL;
    count_a   AT %QW0   : UINT;
    count_b   AT %QW2   : UINT;
END_VAR
VAR
    (* Inputs the master WRITES (coils / holding reg — master-writable) *)
    pe_001    AT %QX1.0 : BOOL;
    pe_002    AT %QX1.1 : BOOL;
    start_pb  AT %QX1.2 : BOOL;
    stop_pb   AT %QX1.3 : BOOL;
    reset_pb  AT %QX1.4 : BOOL;
    estop_in  AT %QX1.5 : BOOL;   (* NC fail-safe wire: TRUE = healthy *)
    barcode   AT %QW1   : UINT;   (* 1 = CHUTE_A, 2 = CHUTE_B *)
END_VAR
VAR
    (* Internal state — separate block (MatIEC rejects mixing with located vars) *)
    running       : BOOL;
    pending       : UINT;
    estop_engaged : BOOL;
    start_edge    : R_TRIG;
    reset_edge    : R_TRIG;
    pe2_rise      : R_TRIG;
    pe2_fall      : F_TRIG;
    jam_timer     : TON;
END_VAR

    estop_engaged := NOT estop_in;
    start_edge(CLK := start_pb);
    reset_edge(CLK := reset_pb);
    pe2_rise(CLK := pe_002);
    pe2_fall(CLK := pe_002);

    IF reset_edge.Q THEN
        jam := FALSE;
        pending := 0;
        diverter := FALSE;
    END_IF;

    IF estop_engaged OR stop_pb THEN
        running := FALSE;
        diverter := FALSE;
        pending := 0;
    END_IF;

    IF start_edge.Q AND NOT estop_engaged AND NOT jam THEN
        running := TRUE;
    END_IF;

    jam_timer(IN := running AND NOT estop_engaged AND NOT jam AND pe_002, PT := T#1s);
    IF jam_timer.Q THEN
        jam := TRUE;
        running := FALSE;
    END_IF;

    IF pe2_rise.Q AND running AND NOT estop_engaged AND NOT jam THEN
        IF barcode = 1 THEN
            pending := 1;
            diverter := TRUE;
        ELSE
            pending := 2;
            diverter := FALSE;
        END_IF;
    END_IF;

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

(* Stand-alone configuration so iec2c/OpenPLC can compile this file directly. *)
CONFIGURATION Config0
  RESOURCE Res0 ON PLC
    TASK Main(INTERVAL := T#20ms, PRIORITY := 0);
    PROGRAM Inst0 WITH Main : sorting_cell_comm;
  END_RESOURCE
END_CONFIGURATION
