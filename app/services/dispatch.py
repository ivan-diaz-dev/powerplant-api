# -*- coding: utf-8 -*-

"""Business logic to compute the optimal production plan."""

import dataclasses
import functools
import math
import operator

import app.core.errors as errors
import app.models.production_plan.payload as payload_models
import app.models.production_plan.response as response_models

UNIT_SCALE = 10  # Represent 0.1 MW increments as integers.
WIND_MARGINAL_COST = 0.0  # Wind power has no marginal cost.
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


def build_production_plan(payload, /):
    """
    Compute the least-cost production plan that satisfies the requested load.

    :param payload_models.ProductionPlanRequest payload: Incoming request payload.

    :raises errors.DispatchComputationError: If the load cannot be satisfied.

    :return: Computed production plan.
    :retype: typing.Iterator
    """

    specs = tuple(_build_specs(payload.powerplants, payload.fuels))
    load_units = _to_units(payload.load)
    total_capacity = sum(spec.max_units for spec in specs)
    if load_units > total_capacity:
        raise errors.DispatchComputationError("Requested load exceeds available capacity.")

    sorted_specs = _sort_specs_by_cost_and_capacity(specs)
    assignment_units = _solve_dispatch(sorted_specs, load_units)

    units_by_index = {spec.original_index: units for spec, units in zip(sorted_specs, assignment_units)}
    for idx, plant in enumerate(payload.powerplants):
        units = units_by_index.get(idx, 0)
        yield response_models.PowerDispatch(name=plant.name, p=_from_units(units))


def _sort_specs_by_cost_and_capacity(specs, /):
    """
    Sort plant specifications by cost per unit (ascending) and max units (descending).

    :param typing.Iterable specs: The plant specifications.

    :return: The sorted plant specifications.
    :retype: typing.Iterable
    """

    sort_key = operator.attrgetter("cost_per_unit", "max_units")
    sorted_specs = sorted(specs, key=sort_key)
    return sorted_specs


def _build_specs(powerplants, fuels, /):
    """
    Build internal plant specifications from the incoming payload.

    :param typing.Iterable powerplants: The powerplants from the payload.
    :param payload_models.FuelBreakdown fuels: The fuel breakdown from the payload.

    :return: The plant specifications.
    :retype: typing.Iterator
    """

    for index, plant in enumerate(powerplants):
        min_output = plant.pmin if plant.type != payload_models.PowerPlantType.WIND else 0.0
        max_output = _effective_max_output(plant, fuels)

        cost_per_mwh = _marginal_cost(plant, fuels)
        cost_per_unit = cost_per_mwh / UNIT_SCALE
        yield PlantSpec(
                original_index=index,
                name=plant.name,
                type=plant.type,
                min_units=_to_units(min_output),
                max_units=_to_units(max_output),
                cost_per_unit=cost_per_unit,
        )


def _effective_max_output(plant, fuels, /):
    """
    Compute the effective maximum output for a plant given the fuel breakdown.

    :param payload_models.PowerPlant plant: The powerplant instance.
    :param payload_models.FuelBreakdown fuels: The fuel breakdown.

    :return: The effective maximum output in MW.
    :retype: float
    """

    if plant.type == payload_models.PowerPlantType.WIND:
        max_output = plant.pmax * (fuels.wind_percentage / 100.0)
    else:
        max_output = plant.pmax
    return max(0.0, max_output)


def _marginal_cost(plant, fuels, /):
    """
    Compute the marginal cost of producing power for a given plant.

    :param payload_models.PowerPlant plant: The powerplant instance.
    :param payload_models.FuelBreakdown fuels: The fuel breakdown.

    :return: The marginal cost in euro per MWh.
    :retype: float
    """

    if plant.type == payload_models.PowerPlantType.WIND:
        return WIND_MARGINAL_COST
    elif plant.type == payload_models.PowerPlantType.GAS:
        fuel_price = fuels.gas_euro_mwh
    else:
        fuel_price = fuels.kerosine_euro_mwh

    co2_component = EMISSION_COEFFICIENT[plant.type] * fuels.co2_euro_ton
    return fuel_price / plant.efficiency + co2_component


def _solve_dispatch(specs, load_units, /):
    """
    Solve the dispatch problem.

    :param typing.Iterable specs: The plant specifications.
    :param int load_units: The required load in 0.1 MW units.

    :return: The assigned units per plant, or None if no solution exists.
    :retype: typing.Iterator
    """

    @functools.lru_cache(maxsize=None)
    def min_cost(index, remaining, /):
        """
        Compute the minimum cost to satisfy the remaining load using plants from index onward.

        This function is here to capture `specs` via closure and keep the LRU cache arguments only
        as index/remaining.

        Note: Cache subproblem results so the DP does not recompute identical (index, remaining) states.

        :param int index: Current plant index.
        :param int remaining: Remaining load in 0.1 MW units.

        :return: The minimum cost to satisfy the remaining load.
        :retype: float
        """

        if remaining < 0:
            # Over-allocated power is invalid → treat this branch as infeasible.
            return math.inf
        if index == len(specs):
            # If no plants remain, only a zero load is solvable.
            return 0.0 if remaining == 0 else math.inf

        spec = specs[index]
        best = math.inf
        for units in _iter_feasible_units(spec, remaining):
            # Explore every feasible dispatch for this plant and add the optimal
            # cost from the rest of the fleet.
            candidate = units * spec.cost_per_unit + min_cost(index + 1, remaining - units)
            if candidate < best:
                best = candidate
        return best

    best_total_cost = min_cost(0, load_units)
    if best_total_cost == math.inf:
        raise errors.DispatchComputationError("Unable to satisfy load with provided fleet configuration.")

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
        yield chosen_units


def _iter_feasible_units(spec, remaining, /):
    """
    Iterate over feasible unit assignments for a plant given the remaining load.

    :param PlantSpec spec: The plant specification.
    :param int remaining: The remaining load in 0.1 MW units.

    :return: the feasible unit assignments.
    :retype: typing.Iterator
    """

    max_assignable = min(spec.max_units, remaining)
    if max_assignable <= 0:
        yield 0
    else:
        start = max(spec.min_units, 1)
        if start <= max_assignable:
            for units in range(start, max_assignable + 1):
                yield units


def _to_units(value, /):
    """
    Convert a floating-point value to scaled integer units by applying rounding and a small
    epsilon to mitigate floating-point precision issues.

    :param float value: The value in MW.

    :return: The value in 0.1 MW units.
    :retype: int
    """

    return int(round((value + 1e-9) * UNIT_SCALE))


def _from_units(units, /):
    """
    Convert scaled integer units back to a floating-point value.
    :param int units: The value in 0.1 MW units.

    :return: The value in MW.
    :retype: float
    """

    value = units / UNIT_SCALE
    return round(value + 1e-9, 1)
