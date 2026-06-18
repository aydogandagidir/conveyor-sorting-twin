# Soft-PLC (STUB for OpenPLC) — zero-dependency Python image.
# Build context is the repo root (see docker-compose.yml).
FROM python:3.13-slim

WORKDIR /app
COPY . /app

# Phase 0/1 core is stdlib-only; no pip install required.
ENV OLTWIN_HOST=0.0.0.0 \
    OLTWIN_PORT=15502 \
    OLTWIN_REGISTRY=conveyor_sorting_cell \
    OLTWIN_CONTROL=control_logic

EXPOSE 15502
CMD ["python", "scripts/run_soft_plc.py"]
