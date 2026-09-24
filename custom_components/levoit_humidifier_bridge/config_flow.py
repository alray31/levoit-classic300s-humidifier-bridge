"""Config flow for the Levoit Classic 300S humidifier bridge.

Instead of hand-editing YAML with entity IDs, this walks the entity
registry looking for the device's select entity (identified by its
`options` attribute being exactly {auto, manual, sleep} -- distinctive
enough to this integration that it reliably finds the right device even
if you have several ESPHome devices around), then, on that same device,
matches every other field by its default friendly name from
common_entities.yaml ("Power", "Auto Target Humidity", "Sleep Target
Humidity", "Manual Mist Level", "Current Humidity").

If you haven't renamed any of the ESPHome entities, every field on the
form below comes pre-filled and you can just hit Submit. Every field is
still a normal entity picker, though, so a wrong or missing guess never
blocks setup -- just pick the right one from the dropdown.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import (
    AVAILABLE_MODES,
    CONF_AUTO_TARGET,
    CONF_CURRENT_HUMIDITY,
    CONF_MANUAL_LEVEL,
    CONF_MODE_SELECT,
    CONF_POWER_SWITCH,
    CONF_SLEEP_TARGET,
    DEFAULT_NAME,
    DOMAIN,
)


def _friendly_name(hass: HomeAssistant, entity_id: str) -> str:
    state = hass.states.get(entity_id)
    if state is None:
        return ""
    return str(state.name or "").strip().lower()


def _autodetect(hass: HomeAssistant) -> dict[str, str | None]:
    """Best-effort guess for each field. Returns None for anything not
    found -- the form always lets the user pick manually regardless."""

    guesses: dict[str, str | None] = {
        CONF_POWER_SWITCH: None,
        CONF_MODE_SELECT: None,
        CONF_AUTO_TARGET: None,
        CONF_SLEEP_TARGET: None,
        CONF_MANUAL_LEVEL: None,
        CONF_CURRENT_HUMIDITY: None,
    }

    # Anchor: the one select entity anywhere in HA whose options are
    # exactly {auto, manual, sleep}. Very unlikely to collide with
    # anything else.
    mode_entity_id = None
    for state in hass.states.async_all("select"):
        options = state.attributes.get("options")
        if options is not None and set(options) == set(AVAILABLE_MODES):
            mode_entity_id = state.entity_id
            break

    if mode_entity_id is None:
        return guesses

    guesses[CONF_MODE_SELECT] = mode_entity_id

    registry = er.async_get(hass)
    mode_entry = registry.async_get(mode_entity_id)
    device_id = mode_entry.device_id if mode_entry else None
    if device_id is None:
        return guesses

    for entry in er.async_entries_for_device(registry, device_id):
        name = _friendly_name(hass, entry.entity_id)
        if not name:
            continue
        if entry.domain == "switch" and name == "power":
            guesses[CONF_POWER_SWITCH] = entry.entity_id
        elif entry.domain == "number" and name == "auto target humidity":
            guesses[CONF_AUTO_TARGET] = entry.entity_id
        elif entry.domain == "number" and name == "sleep target humidity":
            guesses[CONF_SLEEP_TARGET] = entry.entity_id
        elif entry.domain == "number" and name == "manual mist level":
            guesses[CONF_MANUAL_LEVEL] = entry.entity_id
        elif entry.domain == "sensor" and name == "current humidity":
            guesses[CONF_CURRENT_HUMIDITY] = entry.entity_id

    return guesses


def _entity_selector(domain: str) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


class LevoitHumidifierBridgeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the Levoit Classic 300S humidifier bridge."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_POWER_SWITCH])
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input.get(CONF_NAME) or DEFAULT_NAME, data=user_input
            )

        guesses = _autodetect(self.hass)

        schema = vol.Schema(
            {
                vol.Optional(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(
                    CONF_POWER_SWITCH, default=guesses[CONF_POWER_SWITCH]
                ): _entity_selector("switch"),
                vol.Required(
                    CONF_MODE_SELECT, default=guesses[CONF_MODE_SELECT]
                ): _entity_selector("select"),
                vol.Required(
                    CONF_AUTO_TARGET, default=guesses[CONF_AUTO_TARGET]
                ): _entity_selector("number"),
                vol.Required(
                    CONF_SLEEP_TARGET, default=guesses[CONF_SLEEP_TARGET]
                ): _entity_selector("number"),
                vol.Required(
                    CONF_MANUAL_LEVEL, default=guesses[CONF_MANUAL_LEVEL]
                ): _entity_selector("number"),
                vol.Optional(
                    CONF_CURRENT_HUMIDITY, default=guesses[CONF_CURRENT_HUMIDITY]
                ): _entity_selector("sensor"),
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema)
