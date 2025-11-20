# -*- coding: utf-8 -*-

import typing

from pydantic import BaseModel, Field


class PowerDispatch(BaseModel):
    """Assignment of a certain amount of power to a plant."""

    name: str
    p: float = Field(..., ge=0)


ProductionPlanResponse = typing.List[PowerDispatch]
