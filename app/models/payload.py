# -*- coding: utf-8 -*-

from enum import Enum
from typing import List, TypeAlias

from pydantic import BaseModel, ConfigDict, Field


class PowerPlantType(str, Enum):
    """Supported PowerPlant categories."""

    GAS = "gasfired"
    TURBO = "turbojet"
    WIND = "windturbine"


class FuelBreakdown(BaseModel):
    """Cost data and environmental parameters required for dispatch."""

    gas_euro_mwh: float = Field(..., alias="gas(euro/MWh)", gt=0)
    kerosine_euro_mwh: float = Field(..., alias="kerosine(euro/MWh)", gt=0)
    co2_euro_ton: float = Field(..., alias="co2(euro/ton)", ge=0)
    wind_percentage: float = Field(..., alias="wind(%)", ge=0, le=100)


class PowerPlant(BaseModel):
    """Descriptor for a single powerplant instance."""

    name: str
    type: PowerPlantType
    efficiency: float = Field(..., gt=0)
    pmin: float = Field(..., ge=0)  # Minimum power output
    pmax: float = Field(..., gt=0)  # Maximum power output

    model_config = ConfigDict(populate_by_name=True)


class ProductionPlanRequest(BaseModel):
    """Incoming payload describing the load and available powerplants."""

    load: float = Field(..., gt=0)
    fuels: FuelBreakdown
    powerplants: List[PowerPlant] = Field(..., min_length=1)


class PowerDispatch(BaseModel):
    """Assignment of a certain amount of power to a plant."""

    name: str
    p: float = Field(..., ge=0)


ProductionPlanResponse: TypeAlias = List[PowerDispatch]
