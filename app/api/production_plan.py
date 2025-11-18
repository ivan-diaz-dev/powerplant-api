# -*- coding: utf-8 -*-

import logging

import fastapi

import app.core.errors as errors
import app.models.payload as payload_models
import app.services.dispatch as dispatch_service

router = fastapi.APIRouter(prefix="/productionplan", tags=["production-plan"])
logger = logging.getLogger(__name__)


@router.post("", response_model=payload_models.ProductionPlanResponse, status_code=fastapi.status.HTTP_200_OK)
def calculate_production_plan(
    payload: payload_models.ProductionPlanRequest,
) -> payload_models.ProductionPlanResponse:
    """Compute a production plan given the incoming payload constraints."""

    logger.info(
        "Starting production plan computation",
        extra={"load": payload.load, "powerplant_count": len(payload.powerplants)},
    )
    try:
        plan = dispatch_service.build_production_plan(payload)
    except errors.PowerPlantError as exc:
        logger.warning(
            "Invalid production plan request",
            exc_info=(exc.__class__, exc, exc.__traceback__),
        )
        raise fastapi.HTTPException(status_code=fastapi.status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - safeguard
        logger.exception("Unexpected failure while building production plan")
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute production plan.",
        ) from exc

    logger.info(
        "Production plan computation completed",
        extra={"load": payload.load, "powerplant_count": len(payload.powerplants)},
    )
    return plan
