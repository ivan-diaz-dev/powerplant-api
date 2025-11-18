# -*- coding: utf-8 -*-

"""Business logic to compute the optimal production plan."""

import dataclasses
import functools
import math
import typing

import app.core.errors as errors
import app.models.payload as payload_models

UNIT_SCALE = 10  # Represent 0.1 MW increments as integers.
EMISSION_COEFFICIENT = {
    payload_models.PowerPlantType.GAS: 0.3,
    payload_models.PowerPlantType.TURBO: 0.3,
    payload_models.PowerPlantType.WIND: 0.0,
}


@dataclasses.dataclass(frozen=True)
class PlantSpec:
    """Internal representation used by the dispatcher."""

    original_index: int
    name: str
    type: payload_models.PowerPlantType
    min_units: int
    max_units: int
    cost_per_unit: float  # cost of producing 0.1 MW for one hour


def build_production_plan(payload: payload_models.ProductionPlanRequest) -> payload_models.ProductionPlanResponse:
    """Compute the least-cost production plan that satisfies the requested load."""

    specs = _build_specs(payload.powerplants, payload.fuels)
    load_units = _to_units(payload.load)
    total_capacity = sum(spec.max_units for spec in specs)
    if load_units > total_capacity:
        raise errors.DispatchComputationError("Requested load exceeds available capacity.")

    sorted_specs = sorted(specs, key=lambda item: (item.cost_per_unit, -item.max_units))
    assignment_units = _solve_dispatch(sorted_specs, load_units)
    if assignment_units is None:
        raise errors.DispatchComputationError("Unable to satisfy load with provided fleet configuration.")

    units_by_index = {spec.original_index: units for spec, units in zip(sorted_specs, assignment_units)}
    dispatch_plan: typing.List[payload_models.PowerDispatch] = []
    for idx, plant in enumerate(payload.powerplants):
        units = units_by_index.get(idx, 0)
        dispatch_plan.append(payload_models.PowerDispatch(name=plant.name, p=_from_units(units)))

    return dispatch_plan


def _build_specs(
    powerplants: typing.Sequence[payload_models.PowerPlant],
    fuels: payload_models.FuelBreakdown,
) -> typing.List[PlantSpec]:
    specs: typing.List[PlantSpec] = []
    for index, plant in enumerate(powerplants):
        min_output = plant.pmin if plant.type != payload_models.PowerPlantType.WIND else 0.0
        max_output = _effective_max_output(plant, fuels)
        if max_output < 0:
            max_output = 0.0
        min_units = _to_units(min_output)
        max_units = _to_units(max_output)

        if min_units > max_units:
            raise errors.InvalidPayloadError(
                f"Invalid bounds for plant '{plant.name}': pmin exceeds pmax after adjustments.",
            )

        cost_per_mwh = _marginal_cost(plant, fuels)
        cost_per_unit = cost_per_mwh / UNIT_SCALE
        specs.append(
            PlantSpec(
                original_index=index,
                name=plant.name,
                type=plant.type,
                min_units=min_units,
                max_units=max_units,
                cost_per_unit=cost_per_unit,
            ),
        )

    return specs


def _effective_max_output(
    plant: payload_models.PowerPlant,
    fuels: payload_models.FuelBreakdown,
) -> float:
    if plant.type == payload_models.PowerPlantType.WIND:
        return plant.pmax * (fuels.wind_percentage / 100.0)
    return plant.pmax


def _marginal_cost(plant: payload_models.PowerPlant, fuels: payload_models.FuelBreakdown) -> float:
    if plant.type == payload_models.PowerPlantType.WIND:
        return 0.0

    if plant.type == payload_models.PowerPlantType.GAS:
        fuel_price = fuels.gas_euro_mwh
    else:
        fuel_price = fuels.kerosine_euro_mwh

    co2_component = EMISSION_COEFFICIENT[plant.type] * fuels.co2_euro_ton
    return fuel_price / plant.efficiency + co2_component


def _solve_dispatch(specs: typing.Sequence[PlantSpec], load_units: int) -> typing.List[int] | None:
    @functools.lru_cache(maxsize=None)
    def min_cost(index: int, remaining: int) -> float:
        if remaining < 0:
            return math.inf
        if index == len(specs):
            return 0.0 if remaining == 0 else math.inf

        spec = specs[index]
        best = math.inf
        for units in _iter_feasible_units(spec, remaining):
            candidate = units * spec.cost_per_unit + min_cost(index + 1, remaining - units)
            if candidate < best:
                best = candidate
        return best

    best_total_cost = min_cost(0, load_units)
    if best_total_cost == math.inf:
        return None

    assignments: typing.List[int] = []
    remaining = load_units
    for idx, spec in enumerate(specs):
        target_cost = min_cost(idx, remaining)
        chosen_units = 0
        for units in _iter_feasible_units(spec, remaining):
            candidate_cost = units * spec.cost_per_unit + min_cost(idx + 1, remaining - units)
            if math.isclose(candidate_cost, target_cost, rel_tol=1e-9, abs_tol=1e-6):
                chosen_units = units
                remaining -= units
                break
        assignments.append(chosen_units)

    return assignments


def _iter_feasible_units(spec: PlantSpec, remaining: int) -> typing.Iterable[int]:
    max_assignable = min(spec.max_units, remaining)
    if max_assignable <= 0:
        yield 0
        return

    yield 0

    start = max(spec.min_units, 0)
    if start == 0:
        start = 1

    if start > max_assignable:
        return

    for units in range(start, max_assignable + 1):
        yield units


def _to_units(value: float) -> int:
    return int(round((value + 1e-9) * UNIT_SCALE))


def _from_units(units: int) -> float:
    value = units / UNIT_SCALE
    return round(value + 1e-9, 1)
