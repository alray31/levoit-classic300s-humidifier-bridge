"""Levoit Classic 300S humidifier bridge.

Wraps the entities already exposed by the ESPHome device (a select for
mode, three numbers for auto/sleep target and manual level, and a power
switch) into a single native Home Assistant `humidifier` entity -- so it
shows up in Lovelace as one standard humidifier card with a power toggle,
an Auto/Sleep/Manual mode dropdown, and a target dial, instead of several
separate select/number/switch entities.

This is a plain YAML platform (no config flow, nothing to set up in the
UI) -- add it under a `humidifier:` block in configuration.yaml. See the
README in this same folder for the exact YAML and how to find your real
entity IDs.

Not part of the ESPHome firmware: this runs entirely on the Home
Assistant side and just orchestrates the existing entities the ESPHome
device already exposes. It sends no commands of its own to the appliance
-- every action here is a plain `switch.turn_on`, `select.select_option`
or `number.set_value` call on an entity that already exists.

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

import voluptuous as vol

from homeassistant.components.humidifier import PLATFORM_SCHEMA, HumidifierEntity
from homeassistant.components.humidifier.const import (
    HumidifierDeviceClass,
    HumidifierEntityFeature,
)
from homeassistant.const import CONF_NAME, CONF_UNIQUE_ID, STATE_ON
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

CONF_POWER_SWITCH = "power_switch"
CONF_MODE_SELECT = "mode_select"
CONF_AUTO_TARGET = "auto_target"
CONF_SLEEP_TARGET = "sleep_target"
CONF_MANUAL_LEVEL = "manual_level"
CONF_CURRENT_HUMIDITY = "current_humidity"

# Must match components/lv_classic300s_humidifier/select.py's MODE_OPTIONS
# exactly -- these are the literal option strings the ESPHome select
# entity uses, and conveniently they already line up with what the
# humidifier domain expects for its mode dropdown, so no translation
# table is needed either direction.
MODE_AUTO = "auto"
MODE_SLEEP = "sleep"
MODE_MANUAL = "manual"
AVAILABLE_MODES = [MODE_AUTO, MODE_SLEEP, MODE_MANUAL]

# Must match components/lv_classic300s_humidifier/number.py's min/max/step
# for auto_target_humidity / sleep_target_humidity (30-80, real %) and
# manual_level (1-9, a mist level -- not a real humidity %).
AUTO_SLEEP_MIN_HUMIDITY = 30
AUTO_SLEEP_MAX_HUMIDITY = 80
MANUAL_MIN_LEVEL = 1
MANUAL_MAX_LEVEL = 9

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_POWER_SWITCH): cv.entity_id,
        vol.Required(CONF_MODE_SELECT): cv.entity_id,
        vol.Required(CONF_AUTO_TARGET): cv.entity_id,
        vol.Required(CONF_SLEEP_TARGET): cv.entity_id,
        vol.Required(CONF_MANUAL_LEVEL): cv.entity_id,
        vol.Optional(CONF_CURRENT_HUMIDITY): cv.entity_id,
        vol.Optional(CONF_NAME, default="Levoit Classic 300S"): cv.string,
        vol.Optional(CONF_UNIQUE_ID): cv.string,
    }
)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the single bridged humidifier entity from YAML."""
    async_add_entities([LevoitHumidifierBridge(config)])


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

    def __init__(self, config: ConfigType) -> None:
        self._power_switch: str = config[CONF_POWER_SWITCH]
        self._mode_select: str = config[CONF_MODE_SELECT]
        self._auto_target: str = config[CONF_AUTO_TARGET]
        self._sleep_target: str = config[CONF_SLEEP_TARGET]
        self._manual_level: str = config[CONF_MANUAL_LEVEL]
        self._current_humidity_entity: str | None = config.get(CONF_CURRENT_HUMIDITY)
        self._attr_name = config[CONF_NAME]
        self._attr_unique_id = (
            config.get(CONF_UNIQUE_ID) or f"levoit_humidifier_bridge_{self._power_switch}"
        )

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
