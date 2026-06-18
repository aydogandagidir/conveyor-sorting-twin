"""Minimal, standards-compliant Modbus TCP (subset) for OpenLogiTwin Phase 0.

This is a REAL Modbus TCP implementation (MBAP header + standard function codes),
not a fake transport. It is intentionally a *subset*: it implements the function
codes the conveyor sorting cell needs and is meant to be swappable for pymodbus
or a real OpenPLC endpoint later.

Why hand-rolled instead of pymodbus for Phase 0:
  - Zero third-party dependencies -> the verification script runs anywhere Python
    runs, with no pip install and no version pinning.
  - pymodbus has large API differences across 2.x/3.x; depending on it would add
    fragility to the Phase 0 proof.
See adr/0002-minimal-modbus-implementation-and-soft-plc-stub.md.

Supported function codes:
  0x01 Read Coils            0x05 Write Single Coil
  0x02 Read Discrete Inputs  0x06 Write Single Register
  0x03 Read Holding Regs     0x0F Write Multiple Coils
  0x04 Read Input Regs       0x10 Write Multiple Registers
"""
from __future__ import annotations

import socket
import socketserver
import struct
import threading

# --- Modbus function codes ---------------------------------------------------
READ_COILS = 0x01
READ_DISCRETE_INPUTS = 0x02
READ_HOLDING_REGISTERS = 0x03
READ_INPUT_REGISTERS = 0x04
WRITE_SINGLE_COIL = 0x05
WRITE_SINGLE_REGISTER = 0x06
WRITE_MULTIPLE_COILS = 0x0F
WRITE_MULTIPLE_REGISTERS = 0x10

# --- Modbus exception codes --------------------------------------------------
ILLEGAL_FUNCTION = 0x01
ILLEGAL_DATA_ADDRESS = 0x02
ILLEGAL_DATA_VALUE = 0x03


class ModbusError(Exception):
    """A Modbus protocol exception (function code | 0x80, exception code)."""

    def __init__(self, function: int, exception_code: int):
        self.function = function
        self.exception_code = exception_code
        super().__init__(f"Modbus exception fc=0x{function:02X} code=0x{exception_code:02X}")


def _recv_exact(sock: socket.socket, n: int):
    """Read exactly n bytes; return None if the peer closed the connection."""
    buf = bytearray()
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def _pack_bits(values) -> bytes:
    n = len(values)
    out = bytearray((n + 7) // 8)
    for i, v in enumerate(values):
        if v:
            out[i // 8] |= 1 << (i % 8)
    return bytes(out)


def _unpack_bits(raw: bytes, count: int):
    return [bool((raw[i // 8] >> (i % 8)) & 1) for i in range(count)]


# =============================================================================
# Shared data store (the I/O process image)
# =============================================================================
class ModbusDataStore:
    """The four standard Modbus data blocks behind one re-entrant lock.

    In OpenLogiTwin this is the soft-PLC's process image. The gateway (master)
    reaches it over TCP; the soft-PLC scan reaches it directly.
    """

    def __init__(self, size: int = 512):
        self.size = size
        self.lock = threading.RLock()
        self.coils = [False] * size
        self.discrete_inputs = [False] * size
        self.holding_registers = [0] * size
        self.input_registers = [0] * size


# =============================================================================
# Server (Modbus slave)
# =============================================================================
class _RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        store = self.server.store  # type: ignore[attr-defined]
        sock = self.request
        while True:
            header = _recv_exact(sock, 6)
            if header is None:
                return
            txn, _proto, length = struct.unpack(">HHH", header)
            body = _recv_exact(sock, length)
            if body is None or len(body) < 1:
                return
            unit = body[0]
            pdu = body[1:]
            resp_pdu = self._dispatch(store, pdu)
            resp_body = bytes([unit]) + resp_pdu
            sock.sendall(struct.pack(">HHH", txn, 0, len(resp_body)) + resp_body)

    def _dispatch(self, store: ModbusDataStore, pdu: bytes) -> bytes:
        fc = pdu[0]
        data = pdu[1:]
        try:
            if fc == READ_COILS:
                return self._read_bits(fc, store, store.coils, data)
            if fc == READ_DISCRETE_INPUTS:
                return self._read_bits(fc, store, store.discrete_inputs, data)
            if fc == READ_HOLDING_REGISTERS:
                return self._read_regs(fc, store, store.holding_registers, data)
            if fc == READ_INPUT_REGISTERS:
                return self._read_regs(fc, store, store.input_registers, data)
            if fc == WRITE_SINGLE_COIL:
                return self._write_single_coil(store, data)
            if fc == WRITE_SINGLE_REGISTER:
                return self._write_single_register(store, data)
            if fc == WRITE_MULTIPLE_COILS:
                return self._write_multiple_coils(store, data)
            if fc == WRITE_MULTIPLE_REGISTERS:
                return self._write_multiple_registers(store, data)
            raise ModbusError(fc, ILLEGAL_FUNCTION)
        except ModbusError as e:
            return bytes([fc | 0x80, e.exception_code])

    @staticmethod
    def _read_bits(fc, store, bits, data) -> bytes:
        address, count = struct.unpack(">HH", data[:4])
        if count < 1 or count > 2000:
            raise ModbusError(fc, ILLEGAL_DATA_VALUE)
        with store.lock:
            if address + count > len(bits):
                raise ModbusError(fc, ILLEGAL_DATA_ADDRESS)
            vals = bits[address:address + count]
        payload = _pack_bits(vals)
        return bytes([fc, len(payload)]) + payload

    @staticmethod
    def _read_regs(fc, store, regs, data) -> bytes:
        address, count = struct.unpack(">HH", data[:4])
        if count < 1 or count > 125:
            raise ModbusError(fc, ILLEGAL_DATA_VALUE)
        with store.lock:
            if address + count > len(regs):
                raise ModbusError(fc, ILLEGAL_DATA_ADDRESS)
            vals = regs[address:address + count]
        payload = b"".join(struct.pack(">H", v & 0xFFFF) for v in vals)
        return bytes([fc, len(payload)]) + payload

    @staticmethod
    def _write_single_coil(store, data) -> bytes:
        address, value = struct.unpack(">HH", data[:4])
        if value not in (0x0000, 0xFF00):
            raise ModbusError(WRITE_SINGLE_COIL, ILLEGAL_DATA_VALUE)
        with store.lock:
            if address >= len(store.coils):
                raise ModbusError(WRITE_SINGLE_COIL, ILLEGAL_DATA_ADDRESS)
            store.coils[address] = (value == 0xFF00)
        return bytes([WRITE_SINGLE_COIL]) + data[:4]

    @staticmethod
    def _write_single_register(store, data) -> bytes:
        address, value = struct.unpack(">HH", data[:4])
        with store.lock:
            if address >= len(store.holding_registers):
                raise ModbusError(WRITE_SINGLE_REGISTER, ILLEGAL_DATA_ADDRESS)
            store.holding_registers[address] = value & 0xFFFF
        return bytes([WRITE_SINGLE_REGISTER]) + data[:4]

    @staticmethod
    def _write_multiple_coils(store, data) -> bytes:
        address, count, _bytecount = struct.unpack(">HHB", data[:5])
        coil_bytes = data[5:]
        with store.lock:
            if address + count > len(store.coils):
                raise ModbusError(WRITE_MULTIPLE_COILS, ILLEGAL_DATA_ADDRESS)
            for i in range(count):
                store.coils[address + i] = bool((coil_bytes[i // 8] >> (i % 8)) & 1)
        return bytes([WRITE_MULTIPLE_COILS]) + struct.pack(">HH", address, count)

    @staticmethod
    def _write_multiple_registers(store, data) -> bytes:
        address, count, _bytecount = struct.unpack(">HHB", data[:5])
        regs_bytes = data[5:]
        with store.lock:
            if address + count > len(store.holding_registers):
                raise ModbusError(WRITE_MULTIPLE_REGISTERS, ILLEGAL_DATA_ADDRESS)
            for i in range(count):
                (v,) = struct.unpack(">H", regs_bytes[i * 2:i * 2 + 2])
                store.holding_registers[address + i] = v
        return bytes([WRITE_MULTIPLE_REGISTERS]) + struct.pack(">HH", address, count)


class _ThreadingServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ModbusTCPServer:
    """Threaded Modbus TCP slave that serves a ModbusDataStore."""

    def __init__(self, store: ModbusDataStore, host: str = "127.0.0.1", port: int = 15502):
        self.store = store
        self._server = _ThreadingServer((host, port), _RequestHandler)
        self._server.store = store  # type: ignore[attr-defined]
        self._thread = None

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def host(self) -> str:
        return self._server.server_address[0]

    def start(self) -> "ModbusTCPServer":
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()


# =============================================================================
# Client (Modbus master)
# =============================================================================
class ModbusTCPClient:
    """Synchronous Modbus TCP master speaking standard MBAP framing.

    Interface (read_*/write_*) is duck-typed and shared with LocalStoreClient so
    the gateway is backend-agnostic.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 15502, unit: int = 1, timeout: float = 3.0):
        self.host = host
        self.port = port
        self.unit = unit
        self.timeout = timeout
        self._sock = None
        self._txn = 0
        self._lock = threading.Lock()

    def connect(self) -> "ModbusTCPClient":
        self._sock = socket.create_connection((self.host, self.port), self.timeout)
        self._sock.settimeout(self.timeout)
        return self

    def close(self):
        if self._sock is not None:
            try:
                self._sock.close()
            finally:
                self._sock = None

    def _request(self, function: int, data: bytes) -> bytes:
        if self._sock is None:
            raise ConnectionError("ModbusTCPClient is not connected")
        with self._lock:
            self._txn = (self._txn + 1) & 0xFFFF
            body = bytes([self.unit, function]) + data
            self._sock.sendall(struct.pack(">HHH", self._txn, 0, len(body)) + body)
            header = _recv_exact(self._sock, 6)
            if header is None:
                raise ConnectionError("connection closed by peer")
            _txn, _proto, length = struct.unpack(">HHH", header)
            resp_body = _recv_exact(self._sock, length)
            if resp_body is None:
                raise ConnectionError("connection closed by peer")
        resp_pdu = resp_body[1:]
        fc = resp_pdu[0]
        if fc & 0x80:
            raise ModbusError(fc & 0x7F, resp_pdu[1])
        return resp_pdu[1:]

    def read_coils(self, address: int, count: int = 1):
        resp = self._request(READ_COILS, struct.pack(">HH", address, count))
        return _unpack_bits(resp[1:1 + resp[0]], count)

    def read_discrete_inputs(self, address: int, count: int = 1):
        resp = self._request(READ_DISCRETE_INPUTS, struct.pack(">HH", address, count))
        return _unpack_bits(resp[1:1 + resp[0]], count)

    def read_holding_registers(self, address: int, count: int = 1):
        resp = self._request(READ_HOLDING_REGISTERS, struct.pack(">HH", address, count))
        raw = resp[1:1 + resp[0]]
        return [struct.unpack(">H", raw[i * 2:i * 2 + 2])[0] for i in range(count)]

    def read_input_registers(self, address: int, count: int = 1):
        resp = self._request(READ_INPUT_REGISTERS, struct.pack(">HH", address, count))
        raw = resp[1:1 + resp[0]]
        return [struct.unpack(">H", raw[i * 2:i * 2 + 2])[0] for i in range(count)]

    def write_coil(self, address: int, value: bool) -> bool:
        self._request(WRITE_SINGLE_COIL, struct.pack(">HH", address, 0xFF00 if value else 0x0000))
        return True

    def write_register(self, address: int, value: int) -> bool:
        self._request(WRITE_SINGLE_REGISTER, struct.pack(">HH", address, int(value) & 0xFFFF))
        return True


class LocalStoreClient:
    """In-process client for the local control fallback (no sockets).

    Same interface as ModbusTCPClient, but reads/writes a shared ModbusDataStore
    directly. Used for fast development without the TCP layer.
    """

    def __init__(self, store: ModbusDataStore):
        self.store = store

    def connect(self) -> "LocalStoreClient":
        return self

    def close(self):
        pass

    def read_coils(self, address, count=1):
        with self.store.lock:
            return list(self.store.coils[address:address + count])

    def read_discrete_inputs(self, address, count=1):
        with self.store.lock:
            return list(self.store.discrete_inputs[address:address + count])

    def read_holding_registers(self, address, count=1):
        with self.store.lock:
            return list(self.store.holding_registers[address:address + count])

    def read_input_registers(self, address, count=1):
        with self.store.lock:
            return list(self.store.input_registers[address:address + count])

    def write_coil(self, address, value):
        with self.store.lock:
            self.store.coils[address] = bool(value)
        return True

    def write_register(self, address, value):
        with self.store.lock:
            self.store.holding_registers[address] = int(value) & 0xFFFF
        return True
