# -*- coding: utf-8 -*-

class PowerPlantError(Exception):
    """Base error for the powerplants domain."""


class InvalidPayloadError(PowerPlantError):
    """Raised when the incoming payload fails validation beyond schema checks."""


class DispatchComputationError(PowerPlantError):
    """Raised when the dispatch algorithm cannot satisfy the requested load."""
