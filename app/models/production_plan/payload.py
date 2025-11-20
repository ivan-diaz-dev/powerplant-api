# -*- coding: utf-8 -*-

import enum
import typing

import pydantic


class PowerPlantType(str, enum.Enum):
    """Supported PowerPlant categories."""

    GAS = "gasfired"
    TURBO = "turbojet"
    WIND = "windturbine"


class FuelBreakdown(pydantic.BaseModel):
    """Cost data and environmental parameters required for dispatch."""

    gas_euro_mwh: float = pydantic.Field(..., alias="gas(euro/MWh)", gt=0)
    kerosine_euro_mwh: float = pydantic.Field(..., alias="kerosine(euro/MWh)", gt=0)
    co2_euro_ton: float = pydantic.Field(..., alias="co2(euro/ton)", ge=0)
    wind_percentage: float = pydantic.Field(..., alias="wind(%)", ge=0, le=100)

    # Allow population by both alias and field name (more flexible for tests)
    model_config = pydantic.ConfigDict(populate_by_name=True)


class PowerPlant(pydantic.BaseModel):
    """Descriptor for a single powerplant instance."""

    name: str
    type: PowerPlantType
    efficiency: float = pydantic.Field(..., gt=0)
    pmin: float = pydantic.Field(..., ge=0)  # Minimum power output
    pmax: float = pydantic.Field(..., gt=0)  # Maximum power output

    @pydantic.model_validator(mode="after")
    def validate_bounds(self, /):
        """Ensure the minimum output never exceeds the maximum."""

        if self.pmin > self.pmax:
            raise ValueError(
                f"Invalid bounds for plant '{self.name}': pmin exceeds pmax.",
            )
        return self


class ProductionPlanRequest(pydantic.BaseModel):
    """Incoming payload describing the load and available powerplants."""

    load: float = pydantic.Field(..., gt=0)
    fuels: FuelBreakdown
    powerplants: typing.List[PowerPlant] = pydantic.Field(..., min_length=1)
