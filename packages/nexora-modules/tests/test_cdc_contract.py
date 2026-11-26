from __future__ import annotations

from collections.abc import Callable

import pytest
from pydantic import ValidationError

from nexora_core.errors import NotFoundError
from nexora_modules.cdc import CdcConnectorManager, CdcConnectorSpec, ConnectorState
from nexora_modules.cdc.fakes import InMemoryCdcConnectorManager

MANAGERS = [pytest.param(InMemoryCdcConnectorManager, id="in-memory")]


def spec(tables: tuple[str, ...] = ("public.orders",)) -> CdcConnectorSpec:
    return CdcConnectorSpec(
        name="orders-cdc",
        source_type="postgres",
        connection_ref="k8s://nexora/orders-db",
        tables=tables,
        topic_prefix="orders",
    )


@pytest.mark.contract
@pytest.mark.parametrize("factory", MANAGERS)
async def test_deploy_is_idempotent_update(factory: Callable[[], CdcConnectorManager]) -> None:
    manager = factory()
    assert isinstance(manager, CdcConnectorManager)
    first = await manager.deploy(spec())
    assert first.state is ConnectorState.RUNNING
    second = await manager.deploy(spec(("public.orders", "public.items")))
    assert second.tasks_running == 2
    assert (await manager.status("orders-cdc")).tasks_running == 2


@pytest.mark.contract
@pytest.mark.parametrize("factory", MANAGERS)
async def test_unknown_connector_and_remove(factory: Callable[[], CdcConnectorManager]) -> None:
    manager = factory()
    with pytest.raises(NotFoundError):
        await manager.status("missing")
    with pytest.raises(NotFoundError):
        await manager.remove("missing")
    await manager.deploy(spec())
    await manager.remove("orders-cdc")
    with pytest.raises(NotFoundError):
        await manager.status("orders-cdc")


def test_spec_rejects_bad_name_and_empty_tables() -> None:
    with pytest.raises(ValidationError):
        CdcConnectorSpec(
            name="Bad Name", source_type="x", connection_ref="r", tables=("a.b",), topic_prefix="p"
        )
    with pytest.raises(ValidationError):
        CdcConnectorSpec(
            name="ok", source_type="x", connection_ref="r", tables=(), topic_prefix="p"
        )
