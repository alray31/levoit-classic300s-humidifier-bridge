"""Humidifier platform for the Levoit Classic 300S bridge.

Wraps the entities already exposed by the ESPHome device (a select for
mode, three numbers for auto/sleep target and manual level, and a power
switch) into a single native Home Assistant `humidifier` entity -- so it
shows up in Lovelace as one standard humidifier card with a power
toggle, an Auto/Sleep/Manual mode dropdown, and a target dial, instead
of several separate select/number/switch entities.

Configured entirely via the config flow (config_flow.py) -- no YAML.

Not part of the ESPHome firmware: this runs entirely on the Home
Assistant side and just orchestrates the existing entities the ESPHome
device already exposes. It sends no commands of its own to the
appliance -- every action here is a plain `switch.turn_on`,
`select.select_option` or `number.set_value` call on an entity that
already exists.

"Stop At Target" is deliberately NOT part of this entity: the humidifier
domain only has room for on/off + one mode dropdown + one target dial,
with no slot for a second independent boolean setting. Keep using the
"Stop At Target" switch from common_entities.yaml on its own, alongside
this card.

Off is not one of the modes below -- it's the entity's own on/off state
(the power toggle on the card / more-info dialog), wired to the Power
switch, exactly like the rest of the humidifier domain works.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    AUTO_SLEEP_MAX_HUMIDITY,
    AUTO_SLEEP_MIN_HUMIDITY,
    AVAILABLE_MODES,
    CONF_AUTO_TARGET,
    CONF_CURRENT_HUMIDITY,
    CONF_MANUAL_LEVEL,
    CONF_MODE_SELECT,
    CONF_POWER_SWITCH,
    CONF_SLEEP_TARGET,
    MANUAL_MAX_LEVEL,
    MANUAL_MIN_LEVEL,
    MODE_AUTO,
    MODE_MANUAL,
    MODE_SLEEP,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the bridged humidifier entity from a config entry."""
    async_add_entities([LevoitHumidifierBridge(entry)])


class LevoitHumidifierBridge(HumidifierEntity):
    """A humidifier entity that mirrors/drives the underlying ESPHome
    select + number + switch entities instead of talking to any device
    directly. Every property below reads the underlying entity's current
    state live from `hass.states`, rather than caching it -- this keeps
    the bridge trivially correct if the underlying entities change from
    any source (HA UI, an automation, or a physical button press on the
    appliance relayed back through the ESPHome status frames)."""

    _attr_should_poll = False
    _attr_device_class = HumidifierDeviceClass.HUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature.MODES
    _attr_available_modes = AVAILABLE_MODES

    def __init__(self, entry: ConfigEntry) -> None:
        data = entry.data
        self._power_switch: str = data[CONF_POWER_SWITCH]
        self._mode_select: str = data[CONF_MODE_SELECT]
        self._auto_target: str = data[CONF_AUTO_TARGET]
        self._sleep_target: str = data[CONF_SLEEP_TARGET]
        self._manual_level: str = data[CONF_MANUAL_LEVEL]
        self._current_humidity_entity: str | None = data.get(CONF_CURRENT_HUMIDITY)
        self._attr_name = entry.title
        self._attr_unique_id = entry.entry_id

    async def async_added_to_hass(self) -> None:
        """Re-publish our own state whenever any underlying entity changes."""
        tracked = [
            self._power_switch,
            self._mode_select,
            self._auto_target,
            self._sleep_target,
            self._manual_level,
        ]
        if self._current_humidity_entity:
            tracked.append(self._current_humidity_entity)

        @callback
        def _relay(_event: Any) -> None:
            self.async_write_ha_state()

        self.async_on_remove(async_track_state_change_event(self.hass, tracked, _relay))

    # -- internal helpers -------------------------------------------------

    def _mode(self) -> str:
        state = self.hass.states.get(self._mode_select)
        if state is not None and state.state in AVAILABLE_MODES:
            return state.state
        return MODE_AUTO

    def _numeric_state(self, entity_id: str) -> float | None:
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        try:
            return float(state.state)
        except ValueError:
            return None

    # -- HumidifierEntity / ToggleEntity properties ------------------------

    @property
    def is_on(self) -> bool | None:
        state = self.hass.states.get(self._power_switch)
        if state is None or state.state in ("unknown", "unavailable"):
            return None
        return state.state == STATE_ON

    @property
    def mode(self) -> str:
        return self._mode()

    @property
    def current_humidity(self) -> float | None:
        if self._current_humidity_entity is None:
            return None
        return self._numeric_state(self._current_humidity_entity)

    @property
    def target_humidity(self) -> float | None:
        mode = self._mode()
        if mode == MODE_MANUAL:
            return self._numeric_state(self._manual_level)
        if mode == MODE_SLEEP:
            return self._numeric_state(self._sleep_target)
        return self._numeric_state(self._auto_target)

    @property
    def min_humidity(self) -> float:
        # NOTE: Lovelace's humidifier card always labels this dial's
        # values with "%", no matter what min/max are set to -- that's
        # hardcoded in the frontend, not something this integration (or
        # any template) can change. In Manual mode the dial genuinely
        # goes from 1 to 9 and sets the real mist level correctly; it
        # just *displays* as e.g. "3 %" instead of "Level 3". Cosmetic
        # only -- the control itself works as intended.
        return MANUAL_MIN_LEVEL if self._mode() == MODE_MANUAL else AUTO_SLEEP_MIN_HUMIDITY

    @property
    def max_humidity(self) -> float:
        return MANUAL_MAX_LEVEL if self._mode() == MODE_MANUAL else AUTO_SLEEP_MAX_HUMIDITY

    # -- commands -----------------------------------------------------------

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_on", {"entity_id": self._power_switch}, blocking=True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.hass.services.async_call(
            "switch", "turn_off", {"entity_id": self._power_switch}, blocking=True
        )

    async def async_set_mode(self, mode: str) -> None:
        if mode not in AVAILABLE_MODES:
            _LOGGER.warning("Ignoring unsupported humidifier mode: %s", mode)
            return
        await self.hass.services.async_call(
            "select",
            "select_option",
            {"entity_id": self._mode_select, "option": mode},
            blocking=True,
        )

    async def async_set_humidity(self, humidity: int) -> None:
        mode = self._mode()
        if mode == MODE_MANUAL:
            target_entity = self._manual_level
            value = max(MANUAL_MIN_LEVEL, min(MANUAL_MAX_LEVEL, round(humidity)))
        elif mode == MODE_SLEEP:
            target_entity = self._sleep_target
            value = max(AUTO_SLEEP_MIN_HUMIDITY, min(AUTO_SLEEP_MAX_HUMIDITY, round(humidity)))
        else:
            target_entity = self._auto_target
            value = max(AUTO_SLEEP_MIN_HUMIDITY, min(AUTO_SLEEP_MAX_HUMIDITY, round(humidity)))

        await self.hass.services.async_call(
            "number",
            "set_value",
            {"entity_id": target_entity, "value": value},
            blocking=True,
        )
