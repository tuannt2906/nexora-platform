"""Read-only platform catalog: build info, domain modules, engine adapters."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from nexora_control_plane import __version__
from nexora_control_plane.container import Container
from nexora_control_plane.schemas import AdapterInfo, PlatformInfo
from nexora_control_plane.security import get_container, require_token
from nexora_core.modules import ModuleSpec

router = APIRouter(prefix="/api/v1", tags=["catalog"], dependencies=[Depends(require_token)])


@router.get("/platform", response_model=PlatformInfo)
def platform_info(container: Container = Depends(get_container)) -> PlatformInfo:  # noqa: B008
    return PlatformInfo(
        name="nexora-control-plane",
        version=__version__,
        environment=container.settings.environment,
        git_sha=container.settings.git_sha,
    )


@router.get("/modules", response_model=list[ModuleSpec])
def list_modules(container: Container = Depends(get_container)) -> list[ModuleSpec]:  # noqa: B008
    """Domain modules with responsibilities, interfaces and acceptance status (module.toml)."""
    return container.modules


@router.get("/adapters", response_model=list[AdapterInfo])
def list_adapters(container: Container = Depends(get_container)) -> list[AdapterInfo]:  # noqa: B008
    """Engine adapters shipped in this release and their honest maturity level."""
    return [
        AdapterInfo(
            kind=d.kind,
            display_name=d.display_name,
            maturity=d.maturity.value,
            capabilities=list(d.capabilities),
            contract_doc=d.contract_doc,
        )
        for d in container.registry.descriptors()
    ]
