"""Data update coordinator for the Petnovations / CatGenie integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PetnovationsAPI, PetnovationsApiError, PetnovationsAuthError
from .const import (
    CONF_ACCESS_TOKEN,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class PetnovationsCoordinator(DataUpdateCoordinator):
    """Fetch CatGenie state on a sane interval and expose it to entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, api: PetnovationsAPI) -> None:
        self.api = api
        self.entry = entry
        interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=interval),
        )

    async def _async_update_data(self) -> dict:
        try:
            data = await self.api.async_get_devices()
        except PetnovationsAuthError as err:
            # Trigger HA's re-auth flow instead of spamming failures.
            raise ConfigEntryAuthFailed(str(err)) from err
        except PetnovationsApiError as err:
            raise UpdateFailed(str(err)) from err

        # Persist rotated tokens so they survive restarts.
        updates = {}
        if self.api.access_token != self.entry.data.get(CONF_ACCESS_TOKEN):
            updates[CONF_ACCESS_TOKEN] = self.api.access_token
        if self.api.refresh_token != self.entry.data.get(CONF_REFRESH_TOKEN):
            updates[CONF_REFRESH_TOKEN] = self.api.refresh_token
        if updates:
            self.hass.config_entries.async_update_entry(
                self.entry, data={**self.entry.data, **updates}
            )

        return data

    def device_by_id(self, manufacturer_id: str) -> dict | None:
        """Return one device dict from the latest payload."""
        if not self.data:
            return None
        for dev in self.data.get("thingList", []):
            if dev.get("manufacturerId") == manufacturer_id:
                return dev
        return None
