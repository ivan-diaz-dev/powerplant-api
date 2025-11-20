# -*- coding: utf-8 -*-

from fastapi import APIRouter

import app.api.production_plan as production_plan

router = APIRouter()
router.include_router(production_plan.router)
