"""Telemetry logger: SQLite event store with CSV/JSON export.

SQLite-first per the stack direction. PostgreSQL is an optional later swap.
Pure stdlib (sqlite3, csv, json) — no third-party dependencies.
"""
from __future__ import annotations

import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timezone

_FIELDS = ["id", "ts_iso", "ts_unix", "scenario", "event_type", "tag", "value", "detail"]


class TelemetryLogger:
    def __init__(self, db_path: str, scenario: str = "phase0", sink=None):
        self.db_path = db_path
        self.scenario = scenario
        self.sink = sink  # optional callable(event_dict), e.g. an MQTT publisher
        parent = os.path.dirname(os.path.abspath(db_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts_iso      TEXT NOT NULL,
                ts_unix     REAL NOT NULL,
                scenario    TEXT,
                event_type  TEXT NOT NULL,
                tag         TEXT,
                value       TEXT,
                detail      TEXT
            )
            """
        )
        self.conn.commit()

    def log_event(self, event_type: str, tag=None, value=None, detail=None):
        now = time.time()
        iso = datetime.fromtimestamp(now, timezone.utc).isoformat()
        try:
            self.conn.execute(
                "INSERT INTO events (ts_iso, ts_unix, scenario, event_type, tag, value, detail) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (iso, now, self.scenario, event_type, tag, None if value is None else str(value), detail),
            )
            self.conn.commit()
        except sqlite3.Error as exc:
            # Telemetry must never crash the simulation; surface and continue.
            print(f"[telemetry] write failed ({event_type}): {exc}", file=sys.stderr)
        if self.sink is not None:
            try:
                self.sink({
                    "ts_iso": iso, "ts_unix": now, "scenario": self.scenario,
                    "event_type": event_type, "tag": tag,
                    "value": None if value is None else str(value), "detail": detail,
                })
            except Exception as exc:  # a sink (e.g. MQTT) must never crash the run
                print(f"[telemetry] sink failed ({event_type}): {exc}", file=sys.stderr)

    def log_tag_change(self, tag: str, old, new, detail=None):
        self.log_event("tag_change", tag=tag, value=new, detail=detail or f"{old} -> {new}")

    # --- Phase 1 structured event helpers (see telemetry/SCHEMA.md) ----------
    def log_cycle(self, phase: str, detail=None):
        """Cell/parcel cycle events, e.g. 'parcel_spawn'."""
        self.log_event("cycle", tag=phase, detail=detail)

    def log_sort(self, chute: str, destination, detail=None):
        """A parcel was sorted to a chute."""
        self.log_event("sort", tag=chute, value=destination, detail=detail)

    def log_fault(self, name: str, active, detail=None):
        """A fault/alarm asserted (active=True) or cleared (active=False)."""
        self.log_event("fault", tag=name, value=active, detail=detail)

    def log_machine_state(self, state: str, detail=None):
        """A machine state transition, e.g. 'motor_run' / 'motor_stop'."""
        self.log_event("machine_state", tag=state, detail=detail)

    def count(self) -> int:
        return self.conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]

    def rows(self):
        cur = self.conn.execute(
            "SELECT id, ts_iso, ts_unix, scenario, event_type, tag, value, detail "
            "FROM events ORDER BY id"
        )
        return [dict(zip(_FIELDS, r)) for r in cur.fetchall()]

    def export_csv(self, path: str) -> str:
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_FIELDS)
            writer.writeheader()
            for row in self.rows():
                writer.writerow(row)
        return path

    def export_json(self, path: str) -> str:
        rows = self.rows()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"scenario": self.scenario, "count": len(rows), "events": rows}, f, indent=2)
        return path

    def close(self):
        self.conn.close()
