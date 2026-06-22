# deployment/

Docker Compose stack for OpenLogiTwin. Full guide: `docs/DEPLOYMENT.md`.

- `Dockerfile` — soft-PLC image (zero-dep Python 3.13; runs `scripts/run_soft_plc.py`).
- `docker-compose.yml` — profiles `demo` / `minimal` / `standard` / `full` / `integration`.
- `.env.example` — copy to `.env`, set ports and which cell/control to run.

Turnkey browser demo (one container — the web HMI + live twin):
```bash
docker compose -f deployment/docker-compose.yml --profile demo up --build
# open http://localhost:8099/hmi/   (click "Go live" to drive the real twin over WebSocket)
```

Full stack (soft-PLC + FUXA + web HMI):
```bash
cp deployment/.env.example deployment/.env
docker compose -f deployment/docker-compose.yml --profile full up --build
# soft-PLC -> tcp://localhost:15502 ; FUXA -> http://localhost:1881 ; web HMI -> http://localhost:8099/hmi/
```

Validate config (no build/run):
```bash
docker compose -f deployment/docker-compose.yml --profile full config
```

The build context is the repository root; `.dockerignore` keeps `.venv/`, caches and
exports out of the image.
