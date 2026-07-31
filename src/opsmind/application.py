"""FastAPI application factory."""

from fastapi import FastAPI

from opsmind.api.router import api_router
from opsmind.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an OpsMind application with one resolved settings instance."""
    resolved_settings = settings if settings is not None else get_settings()

    def provide_settings() -> Settings:
        return resolved_settings

    application = FastAPI(
        title=resolved_settings.application_name,
        description=f"{resolved_settings.service_name} API",
        debug=resolved_settings.debug,
    )
    application.dependency_overrides[get_settings] = provide_settings
    application.include_router(api_router)
    return application
