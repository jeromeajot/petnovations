"""Binary sensors: cycle running, problem, and connectivity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_CLEANING
from .coordinator import PetnovationsCoordinator
from .entity import PetnovationsEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetnovationsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[BinarySensorEntity] = []
    for device in coordinator.data.get("thingList", []):
        entities.append(CatGenieRunningBinarySensor(coordinator, device))
        entities.append(CatGenieProblemBinarySensor(coordinator, device))
        entities.append(CatGenieOnlineBinarySensor(coordinator, device))
    async_add_entities(entities)


class CatGenieRunningBinarySensor(PetnovationsEntity, BinarySensorEntity):
    """On while a cleaning cycle is in progress."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_translation_key = "cleaning"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._manufacturer_id}_running"

    @property
    def is_on(self) -> bool:
        return self.device.get("operationStatus", {}).get("state") == STATE_CLEANING

    @property
    def extra_state_attributes(self) -> dict:
        op = self.device.get("operationStatus", {})
        return {"progress": op.get("progress"), "state_code": op.get("state")}


class CatGenieProblemBinarySensor(PetnovationsEntity, BinarySensorEntity):
    """On when the device reports an operation error."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "problem"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._manufacturer_id}_problem"

    @property
    def is_on(self) -> bool:
        error = self.device.get("operationStatus", {}).get("error")
        return error not in (None, 0, "0", "", "none")

    @property
    def extra_state_attributes(self) -> dict:
        return {"error": self.device.get("operationStatus", {}).get("error")}


class CatGenieOnlineBinarySensor(PetnovationsEntity, BinarySensorEntity):
    """Cloud connectivity of the device."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_translation_key = "online"

    def __init__(self, coordinator, device) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{self._manufacturer_id}_online"

    @property
    def is_on(self) -> bool:
        status = str(self.device.get("reportedStatus", "")).lower()
        return status in ("online", "connected", "1", "true")
