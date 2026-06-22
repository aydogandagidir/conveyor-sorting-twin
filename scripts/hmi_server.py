"""Live HMI server (V3) — streams the real twin to the web HMI over WebSocket.

Runs the soft-PLC + deterministic scene in REAL TIME, auto-feeds parcels, and broadcasts a
per-tick frame (same shape as an exported trace frame) to connected browsers. Commands from the
HMI (start / stop / reset / estop / jam) drive the actual control logic, so the buttons are live.

Hand-rolled WebSocket (RFC 6455) + stdlib only — same zero-dependency ethos as the Modbus server
(ADR-0002). Frames are JSON: {t, motor, diverter, jam, a, b, pe1, pe2, parcels:[{id,x,dest,stuck}]}.

Usage:  python scripts/hmi_server.py            # ws://127.0.0.1:8765
        HMI_HOST=0.0.0.0 HMI_PORT=8765 python scripts/hmi_server.py
Then open the web HMI and switch it to LIVE (it connects to ws://<host>:8765).
"""
import base64
import hashlib
import json
import os
import socket
import struct
import sys
import threading
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for _sub in ("protocol-gateway", "plc", "simulation"):
    sys.path.insert(0, os.path.join(_ROOT, _sub))

from tag_registry import TagRegistry          # noqa: E402
from modbus_tcp import LocalStoreClient        # noqa: E402
from gateway import TagGateway                 # noqa: E402
from soft_plc import SoftPlc                   # noqa: E402
import control_logic_mvp                       # noqa: E402
from scene_model import SceneModel             # noqa: E402

MVP_REGISTRY = os.path.join(_ROOT, "protocol-gateway", "config", "tags.sorting_cell_mvp.json")
_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


# =============================================================================
# Minimal WebSocket (RFC 6455) — handshake + text framing, stdlib only
# =============================================================================
def ws_accept_key(key):
    return base64.b64encode(hashlib.sha1((key + _GUID).encode()).digest()).decode()


def _recv_exact(sock, n):
    buf = b""
    while len(buf) < n:
        c = sock.recv(n - len(buf))
        if not c:
            return None
        buf += c
    return buf


def ws_handshake_server(sock):
    req = b""
    while b"\r\n\r\n" not in req:
        c = sock.recv(1024)
        if not c:
            return False
        req += c
    headers = {}
    for line in req.decode("latin1").split("\r\n")[1:]:
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    key = headers.get("sec-websocket-key")
    if not key:
        return False
    sock.sendall(("HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n"
                  "Connection: Upgrade\r\nSec-WebSocket-Accept: " + ws_accept_key(key) +
                  "\r\n\r\n").encode())
    return True


def ws_handshake_client(sock, host="localhost"):
    key = base64.b64encode(os.urandom(16)).decode()
    sock.sendall(("GET / HTTP/1.1\r\nHost: " + host + "\r\nUpgrade: websocket\r\n"
                  "Connection: Upgrade\r\nSec-WebSocket-Key: " + key + "\r\n"
                  "Sec-WebSocket-Version: 13\r\n\r\n").encode())
    resp = b""
    while b"\r\n\r\n" not in resp:
        c = sock.recv(1024)
        if not c:
            return False
        resp += c
    return b" 101 " in resp.split(b"\r\n")[0] and ws_accept_key(key).encode() in resp


def ws_send(sock, data, mask=False, opcode=0x1):
    if isinstance(data, str):
        data = data.encode("utf-8")
    n = len(data)
    mbit = 0x80 if mask else 0
    header = bytes([0x80 | opcode])   # FIN + opcode (0x1 text, 0xA pong, 0x8 close)
    if n < 126:
        header += bytes([mbit | n])
    elif n < 65536:
        header += bytes([mbit | 126]) + struct.pack(">H", n)
    else:
        header += bytes([mbit | 127]) + struct.pack(">Q", n)
    if mask:
        mk = os.urandom(4)
        header += mk
        data = bytes(data[i] ^ mk[i % 4] for i in range(n))
    sock.sendall(header + data)


def _read_frame(sock):
    """Read one WebSocket frame. Returns (fin, opcode, payload), or (None, None, None)
    on EOF / a truncated header (peer vanished mid-frame)."""
    h = _recv_exact(sock, 2)
    if h is None:
        return (None, None, None)
    fin = h[0] & 0x80
    opcode = h[0] & 0x0F
    masked = h[1] & 0x80
    n = h[1] & 0x7F
    if n == 126:
        ext = _recv_exact(sock, 2)
        if ext is None:
            return (None, None, None)
        n = struct.unpack(">H", ext)[0]
    elif n == 127:
        ext = _recv_exact(sock, 8)
        if ext is None:
            return (None, None, None)
        n = struct.unpack(">Q", ext)[0]
    mk = None
    if masked:
        mk = _recv_exact(sock, 4)
        if mk is None:
            return (None, None, None)
    payload = _recv_exact(sock, n) if n else b""
    if payload is None:
        return (None, None, None)
    if masked:
        payload = bytes(payload[i] ^ mk[i % 4] for i in range(n))
    return (fin, opcode, payload)


def ws_recv(sock):
    """Receive one logical WebSocket message, reassembling continuation frames (RFC 6455).
    Returns (opcode, payload) or None on disconnect. Control frames (close/ping/pong) are
    never fragmented and are returned individually."""
    fin, opcode, payload = _read_frame(sock)
    if opcode is None:
        return None
    if opcode in (0x8, 0x9, 0xA):
        return (opcode, payload)
    data = payload
    while not fin:                              # data frame fragmented across frames
        fin, op, part = _read_frame(sock)
        if op is None:
            return None
        if op in (0x8, 0x9, 0xA):               # interleaved control frame
            if op == 0x8:
                return (0x8, b"")
            continue                            # ignore ping/pong between fragments
        data += part
    return (opcode, data)


# =============================================================================
# Real-time twin engine (soft-PLC + scene), command-driven
# =============================================================================
class TwinEngine:
    def __init__(self, registry_path=MVP_REGISTRY, spawn_interval=2.6):
        self.registry = TagRegistry.from_file(registry_path)
        self.plc = SoftPlc(self.registry, scan_interval=0.0, control=control_logic_mvp)
        self.gw = TagGateway(self.registry, LocalStoreClient(self.plc.store))
        self.gw.initialize_inputs()
        self.scene = SceneModel()
        self.inputs = {"input.start_pb": False, "input.stop_pb": False,
                       "input.reset_pb": False, "input.estop": False}
        self._pulse = set()
        self._spawn_t = 0.0
        self._spawn_interval = spawn_interval
        self._next = 1
        self.t = 0.0

    def command(self, cmd):
        if cmd == "start":
            self.inputs["input.start_pb"] = True; self._pulse.add("input.start_pb")
        elif cmd == "stop":
            self.inputs["input.stop_pb"] = True; self._pulse.add("input.stop_pb")
        elif cmd == "reset":
            self.inputs["input.reset_pb"] = True; self._pulse.add("input.reset_pb")
            self.inputs["input.estop"] = False
            self.scene.clear_jam()
        elif cmd == "estop":
            self.inputs["input.estop"] = True            # latched until reset
        elif cmd == "jam":
            # stick a parcel blocking PE-002 so the jam timer reliably trips
            pid = self.scene.spawn(1)
            for p in self.scene.parcels:
                if p.id == pid:
                    p.pos = self.scene.pe2_x
                    p.scanned = True
                    p.stuck = True
                    break

    def tick(self, dt):
        self.t += dt
        self._spawn_t += dt
        if self._spawn_t >= self._spawn_interval:
            self._spawn_t = 0.0
            self.scene.spawn(self._next)
            self._next = 2 if self._next == 1 else 1
        stags = self.scene.sensor_tags()
        self.gw.write_tag("sensor.pe_001", stags["sensor.pe_001"])
        self.gw.write_tag("sensor.pe_002", stags["sensor.pe_002"])
        self.gw.write_tag("data.parcel_destination", stags["data.parcel_destination"])
        for name, value in self.inputs.items():
            self.gw.write_tag(name, value)
        self.plc.scan_once()
        motor = self.gw.read_tag("output.motor_conv_001_run")
        divert = self.gw.read_tag("output.diverter_dv_001_extend")
        frame = {
            "t": round(self.t, 2), "motor": bool(motor), "diverter": bool(divert),
            "jam": bool(self.gw.read_tag("alarm.jam_001")),
            "estop": bool(self.inputs["input.estop"]),
            "a": int(self.gw.read_tag("counter.sorted_chute_a")),
            "b": int(self.gw.read_tag("counter.sorted_chute_b")),
            "pe1": self.scene.sensor_blocked(self.scene.pe1_x),
            "pe2": self.scene.sensor_blocked(self.scene.pe2_x),
            "parcels": [{"id": p.id, "x": round(p.pos, 2), "dest": p.destination, "stuck": p.stuck}
                        for p in self.scene.parcels],
        }
        self.scene.step(dt, motor, divert)
        for b in self._pulse:
            self.inputs[b] = False
        self._pulse.clear()
        return frame


class HmiServer:
    def __init__(self, engine=None, host="127.0.0.1", port=8765, dt=0.1):
        self.engine = engine or TwinEngine()
        self.host, self.port, self.dt = host, port, dt
        self.clients, self.lock = set(), threading.Lock()
        self._sock, self._stop = None, threading.Event()

    def serve(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(8)
        self.port = self._sock.getsockname()[1]
        threading.Thread(target=self._engine_loop, daemon=True).start()
        threading.Thread(target=self._accept_loop, daemon=True).start()
        return self.port

    def _accept_loop(self):
        while not self._stop.is_set():
            try:
                cli, _ = self._sock.accept()
            except OSError:
                break
            threading.Thread(target=self._client, args=(cli,), daemon=True).start()

    def _client(self, sock):
        try:
            if not ws_handshake_server(sock):
                sock.close()
                return
            with self.lock:
                self.clients.add(sock)
            while not self._stop.is_set():
                msg = ws_recv(sock)
                if msg is None or msg[0] == 0x8:        # disconnect / close
                    break
                if msg[0] == 0x9:                       # ping -> pong (keep-alive)
                    try:
                        ws_send(sock, msg[1], opcode=0xA)
                    except Exception:
                        break
                    continue
                if msg[0] == 0x1:
                    try:
                        cmd = json.loads(msg[1].decode("utf-8")).get("cmd")
                        if cmd:
                            self.engine.command(cmd)
                    except Exception:
                        pass
        finally:
            with self.lock:
                self.clients.discard(sock)
            try:
                sock.close()
            except Exception:
                pass

    def _engine_loop(self):
        while not self._stop.is_set():
            t0 = time.time()
            data = json.dumps(self.engine.tick(self.dt))
            with self.lock:
                cs = list(self.clients)
            dead = []
            for c in cs:
                try:
                    ws_send(c, data)
                except Exception:
                    dead.append(c)
            if dead:
                with self.lock:
                    for c in dead:
                        self.clients.discard(c)
                for c in dead:                       # close so the client's reader thread unblocks
                    try:
                        c.close()
                    except Exception:
                        pass
            time.sleep(max(0, self.dt - (time.time() - t0)))

    def stop(self):
        self._stop.set()
        try:
            self._sock.close()
        except Exception:
            pass


def main():
    host = os.environ.get("HMI_HOST", "127.0.0.1")
    port = int(os.environ.get("HMI_PORT", "8765"))
    srv = HmiServer(TwinEngine(), host, port)
    bound = srv.serve()
    print("OpenLogiTwin HMI live server on ws://%s:%d  (Ctrl-C to stop)" % (host, bound))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        srv.stop()
        print("\nstopped.")


if __name__ == "__main__":
    main()
