"""Barcode decoding for the conveyor sorting cell (per-parcel destinations).

Decouples scenario authoring from the routing domain: a parcel carries a **barcode**
(string) instead of a raw chute, and the decoder maps it to a destination — the way a
real cell's WMS/barcode reader assigns a chute. Supports EAN-13 (with checksum) and a
simple alpha-prefix fallback, plus an explicit `routes` override table.

Pure / stdlib only. Destinations match the registry: CHUTE_A = 1, CHUTE_B = 2.
"""
from __future__ import annotations

CHUTE_A = 1
CHUTE_B = 2


def ean13_check_digit(payload12: str) -> int:
    """The 13th (check) digit for the first 12 digits of an EAN-13 barcode."""
    digits = [int(c) for c in payload12]
    weighted = sum(d * (1 if i % 2 == 0 else 3) for i, d in enumerate(digits))
    return (10 - (weighted % 10)) % 10


def is_valid_ean13(code: str) -> bool:
    code = str(code)
    return len(code) == 13 and code.isdigit() and ean13_check_digit(code[:12]) == int(code[12])


def _to_dest(value) -> int:
    if isinstance(value, int):
        return CHUTE_A if value == CHUTE_A else CHUTE_B
    return CHUTE_B if str(value).strip().upper().endswith("B") else CHUTE_A


class BarcodeDecoder:
    """Maps a barcode string to a destination chute.

    Resolution order:
      1. explicit `routes` table (exact barcode -> "CHUTE_A"/"CHUTE_B" or 1/2),
      2. valid EAN-13 -> route by the parity of the last payload digit (even=A, odd=B),
      3. alpha prefix -> "B*" => CHUTE_B, otherwise CHUTE_A.
    """

    def __init__(self, routes=None):
        self.routes = {str(k): _to_dest(v) for k, v in (routes or {}).items()}

    def decode(self, barcode) -> int:
        barcode = str(barcode)
        if barcode in self.routes:
            return self.routes[barcode]
        if is_valid_ean13(barcode):
            return CHUTE_A if int(barcode[11]) % 2 == 0 else CHUTE_B
        return CHUTE_B if barcode[:1].upper() == "B" else CHUTE_A
