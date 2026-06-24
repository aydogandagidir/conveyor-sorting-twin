# Contributing to OpenLogiTwin

OpenLogiTwin is a narrow, demo-ready intralogistics simulator (conveyor sorting cell) for
PLC training and virtual commissioning. Please keep changes small, verifiable, and honest.

## Dev setup
- Python 3.9+ (developed on 3.13). The Phase 0/1 core needs **no third-party packages**.
- Optional dev extras (for the pytest path and the pymodbus adapter):
  ```bash
  python -m venv .venv
  .venv/Scripts/python -m pip install -e ".[dev]"   # pytest, jsonschema, pymodbus
  ```

## Running the tests
```bash
python scripts/run_tests.py        # canonical, stdlib-only (what CI runs)
python -m pytest tests/ -q         # equivalent, when pytest is installed
```
Every test file is **dual-mode**: runnable directly (`python tests/test_*.py`, exit 0/1) and
collectable by pytest. The pymodbus interop tests skip cleanly when pymodbus is absent.

## Conventions
- **No fake integrations.** A stand-in must be named `*stub*` and carry TODO replacement
  criteria (see `plc/soft_plc.py`).
- **Don't break the gates.** `tests/verify_phase0.py` (19/19) and `tests/verify_phase1.py`
  (14/14) must stay green; `verify_phase1` also re-runs Phase 0.
- **Tag registry is the source of truth.** Don't hand-edit `hmi/fuxa/tag_list_*.csv`; run
  `python scripts/generate_hmi_tag_list.py` (a drift test guards it).
- **Deterministic scenarios.** New scenarios go in `scenarios/*.json`, validate against
  `scenarios/schema.json`, and carry an `expect` block (`scenario_manager.py run-all` checks them).
- **Document decisions** in `adr/NNNN-title.md` (Context / Decision / Rationale / Consequences
  / Alternatives) and add a row to [`adr/README.md`](adr/README.md). Keep `docs/CHANGELOG.md` and
  `docs/ROADMAP.md` current (and `docs/ACCEPTANCE_CRITERIA.md` when acceptance changes).

## Adding a test
Mirror the existing pattern: `test_*` functions with plain `assert`s, plus a `main()` that runs
them and a `__main__` guard. Add the file to the `SUITE` list in `scripts/run_tests.py`.

## Commit messages
Imperative mood, scoped, one logical change per commit, e.g.
`plc: clear diverter latch on E-stop (ADR-0004)`.

## Pull requests
- Keep PRs focused; include the verification you ran (`run_tests.py` output).
- Note any new limitation honestly in the relevant doc.
