"""Config and options flow for the Petnovations / CatGenie integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import PetnovationsAPI, PetnovationsApiError, PetnovationsAuthError
from .const import (
    CONF_HMAC_KEY,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def _validate(hass, data: dict) -> str | None:
    """Return an error key, or None on success."""
    session = async_get_clientsession(hass)
    api = PetnovationsAPI(
        session,
        hmac_key=data[CONF_HMAC_KEY],
        refresh_token=data[CONF_REFRESH_TOKEN],
    )
    try:
        await api.async_validate()
    except PetnovationsAuthError:
        return "invalid_auth"
    except PetnovationsApiError:
        return "cannot_connect"
    except Exception:  # noqa: BLE001
        _LOGGER.exception("Unexpected error validating CatGenie credentials")
        return "unknown"
    return None


class PetnovationsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup and re-auth."""

    VERSION = 2

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            data = {
                CONF_HMAC_KEY: user_input[CONF_HMAC_KEY].strip(),
                CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN].strip(),
            }
            error = await _validate(self.hass, data)
            if error is None:
                return self.async_create_entry(title="CatGenie", data=data)
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_HMAC_KEY): str,
                vol.Required(CONF_REFRESH_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_reauth(self, entry_data: dict[str, Any]) -> ConfigFlowResult:
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self._reauth_entry
        if user_input is not None:
            data = {
                CONF_HMAC_KEY: user_input[CONF_HMAC_KEY].strip(),
                CONF_REFRESH_TOKEN: user_input[CONF_REFRESH_TOKEN].strip(),
            }
            error = await _validate(self.hass, data)
            if error is None:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")
            errors["base"] = error

        schema = vol.Schema(
            {
                vol.Required(CONF_HMAC_KEY, default=entry.data.get(CONF_HMAC_KEY, "")): str,
                vol.Required(CONF_REFRESH_TOKEN): str,
            }
        )
        return self.async_show_form(step_id="reauth_confirm", data_schema=schema, errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return PetnovationsOptionsFlow(config_entry)


class PetnovationsOptionsFlow(OptionsFlow):
    """Let the user tune the poll interval."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Optional(CONF_SCAN_INTERVAL, default=current): vol.All(
                    vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
