"""Levoit Classic 300S humidifier bridge.

YAML-only integration, no config entries and no config flow: the actual
entity is created by `humidifier.py` from a
`humidifier: platform: levoit_humidifier_bridge` block in
`configuration.yaml`. This file exists only so Home Assistant recognizes
`levoit_humidifier_bridge` as a valid component package.
"""

DOMAIN = "levoit_humidifier_bridge"
