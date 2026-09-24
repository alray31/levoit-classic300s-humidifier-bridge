"""Levoit Classic 300S humidifier bridge integration.

Set up entirely through a config flow (Settings -> Devices & services ->
Add integration -> "Levoit Classic 300S Humidifier Bridge") -- no YAML
needed. See config_flow.py for the entity auto-detection logic and
humidifier.py for the actual bridged entity.
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

PLATFORMS = ["humidifier"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Levoit Classic 300S humidifier bridge from a config entry."""
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
