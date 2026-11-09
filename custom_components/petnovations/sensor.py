"""Sensors for the CatGenie: cycle state, progress, error, cartridge, timing."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, STATE_CLEANING, STATE_IDLE, STATE_PAUSED
from .coordinator import PetnovationsCoordinator
from .entity import PetnovationsEntity

CYCLE_STATES = {STATE_IDLE: "Idle", STATE_CLEANING: "Cleaning", STATE_PAUSED: "Paused"}


def _cycle_state(dev: dict):
    return CYCLE_STATES.get(dev.get("operationStatus", {}).get("state"), "Unknown")


def _progress(dev: dict):
    op = dev.get("operationStatus", {})
    return op.get("progress") if op.get("state") == STATE_CLEANING else 0


def _error(dev: dict):
    err = dev.get("operationStatus", {}).get("error")
    return "None" if err in (None, 0, "0", "") else str(err)


def _last_clean(dev: dict):
    raw = dev.get("lastClean")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).replace(tzinfo=UTC)
    except (ValueError, TypeError):
        return None


@dataclass(frozen=True, kw_only=True)
class CatGenieSensor(SensorEntityDescription):
    value: Callable[[dict], object] = lambda d: None


SENSORS: tuple[CatGenieSensor, ...] = (
    CatGenieSensor(
        key="cycle_state",
        name="Cycle status",
        icon="mdi:sync",
        value=_cycle_state,
    ),
    CatGenieSensor(
        key="progress",
        name="Cycle progress",
        native_unit_of_measurement=PERCENTAGE,
        icon="mdi:percent",
        value=_progress,
    ),
    CatGenieSensor(
        key="error",
        name="Operation error",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:alert-circle",
        value=_error,
    ),
    CatGenieSensor(
        key="cartridge_remaining",
        name="Cartridge remaining",
        native_unit_of_measurement="cycles",
        icon="mdi:cup-water",
        value=lambda d: d.get("remainingSaniSolution"),
    ),
    CatGenieSensor(
        key="last_clean",
        name="Last clean",
        device_class=SensorDeviceClass.TIMESTAMP,
        value=_last_clean,
    ),
    CatGenieSensor(
        key="firmware",
        name="Firmware",
        entity_category=EntityCategory.DIAGNOSTIC,
        icon="mdi:chip",
        value=lambda d: d.get("fwVersion"),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: PetnovationsCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities = [
        PetnovationsSensor(coordinator, device, desc)
        for device in coordinator.data.get("thingList", [])
        for desc in SENSORS
    ]
    async_add_entities(entities)


class PetnovationsSensor(PetnovationsEntity, SensorEntity):
    """One CatGenie reading."""

    entity_description: CatGenieSensor

    def __init__(self, coordinator, device, description: CatGenieSensor) -> None:
        super().__init__(coordinator, device)
        self.entity_description = description
        self._attr_unique_id = f"{self._manufacturer_id}_{description.key}"

    @property
    def native_value(self):
        return self.entity_description.value(self.device)
