"""Change data capture: manage Debezium-style connectors on Kafka Connect."""

from nexora_modules.cdc.models import CdcConnectorSpec, ConnectorState, ConnectorStatus
from nexora_modules.cdc.ports import CdcConnectorManager

__all__ = ["CdcConnectorManager", "CdcConnectorSpec", "ConnectorState", "ConnectorStatus"]
