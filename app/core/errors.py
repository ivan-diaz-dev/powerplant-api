# -*- coding: utf-8 -*-

class PowerPlantError(Exception):
    """Base error for the powerplants domain."""


class DispatchComputationError(PowerPlantError):
    """Raised when the dispatch algorithm cannot satisfy the requested load."""
