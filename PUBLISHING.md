# Publishing OpenLogiTwin to PyPI

The package builds a **self-contained wheel**: `setup.py` vendors the runtime source dirs into
`openlogitwin/_bundled/` at build time, so a `pip install`ed `openlogitwin` runs without the repo
(verified end to end — a clean-venv install runs `openlogitwin export` from the bundled runtime).

Everything below is the **maintainer's** job and needs a **PyPI account + API token** — these steps
are not run by CI.

## 1 · Build the distributions
```bash
python -m pip install --upgrade build twine     # one-time
python -m build                                  # -> dist/openlogitwin-X.Y.Z.tar.gz + .whl
```
(`pip wheel . --no-deps -w dist` also builds just the wheel.)

## 2 · Smoke-test the wheel in a throwaway venv
```bash
python -m venv /tmp/oltw && /tmp/oltw/bin/pip install dist/openlogitwin-*.whl
cd /tmp && /tmp/oltw/bin/openlogitwin --help          # from a neutral dir (no repo)
/tmp/oltw/bin/openlogitwin export barcode_sorting_basic   # exercises the bundled runtime
```
On Windows the scripts live under `…\Scripts\` (`openlogitwin.exe`).

## 3 · Check the name + metadata
- Confirm the project name **`openlogitwin`** is available (or owned by you) on
  <https://pypi.org/project/openlogitwin/>. If taken, change `name` in `pyproject.toml`.
- Bump `version` in **both** `pyproject.toml` and `openlogitwin/__init__.py`, and add a
  `docs/CHANGELOG.md` entry.

## 4 · Upload
```bash
twine upload --repository testpypi dist/*      # optional dry run on TestPyPI first
twine upload dist/*                            # the real PyPI (uses your ~/.pypirc or a token)
```
Use a scoped **API token** (`__token__` as the username) rather than your password.

## 5 · Verify
```bash
pip install openlogitwin
openlogitwin --help
```

## Notes
- The wheel bundles `scripts/ protocol-gateway/ plc/ simulation/ telemetry/ scenarios/ web/ tests/`
  (minus caches, generated traces, and exports). Traces are regenerated on first run.
- Editable installs (`pip install -e .`) and clones don't use `_bundled/` — they run from the repo
  dirs directly (`openlogitwin.cli._bootstrap()` picks whichever is present).
- A self-contained wheel is heavier than a typical library wheel because OpenLogiTwin is a runnable
  demo/twin, not just a library — that trade-off is intentional.
