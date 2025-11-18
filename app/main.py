# -*-coding: utf-8 -*-

import fastapi
import uvicorn

import app.api.production_plan as production_plan
import app.core.config as config
import app.core.logging as logging


def create_application() -> fastapi.FastAPI:
    """Instantiate and configure the FastAPI app."""

    settings = config.get_settings()
    logging.configure_logging(settings.log_level)

    app = fastapi.FastAPI(title=settings.app_name, version=settings.app_version)
    app.include_router(production_plan.router)
    return app


app = create_application()


if __name__ == "__main__":

    settings = config.get_settings()
    uvicorn.run(
        "app.main:app",
        port=settings.app_port,
        reload=True,
    )
