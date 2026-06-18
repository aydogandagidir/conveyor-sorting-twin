"""Conveyor sorting cell simulation stand-in for Phase 0.

STUB for the Godot scene (Phase 1). It drives sensor tags and reads actuator
tags through the protocol gateway — exactly the contract the Godot adapter will
implement. Replaceable by simulation/godot-project (see its README).

This module deliberately has no knowledge of Modbus; it only speaks tag names.
"""
from __future__ import annotations


class ConveyorCellSimulator:
    def __init__(self, gateway, telemetry=None):
        self.gateway = gateway
        self.telemetry = telemetry

    def set_estop(self, engaged: bool):
        self.gateway.write_tag("estop", engaged)
        if self.telemetry:
            self.telemetry.log_event("estop", tag="estop", value=engaged)

    def present_parcel(self, destination: int):
        """A parcel arrives at the divert point carrying a decoded destination."""
        self.gateway.write_tag("barcode.destination", destination)
        self.gateway.write_tag("sensor.preDivert", True)
        if self.telemetry:
            self.telemetry.log_event(
                "parcel_present", tag="sensor.preDivert", value=True,
                detail=f"destination={destination}",
            )

    def clear_parcel(self):
        """The parcel leaves the divert point."""
        self.gateway.write_tag("sensor.preDivert", False)
        if self.telemetry:
            self.telemetry.log_event("parcel_cleared", tag="sensor.preDivert", value=False)

    def read_actuators(self) -> dict:
        return self.gateway.read_many()
