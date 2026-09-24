# Levoit Classic 300S -- Humidifier Bridge (HACS)

A tiny Home Assistant custom integration that combines the entities
already exposed by the [Levoit Classic 300S ESPHome
firmware](https://github.com/alray31/levoit-classic300s-esphome) (a
`select` for mode, three `number` entities for Auto/Sleep target and
Manual level, and a `switch` for power) into a single native
`humidifier` entity -- so Lovelace shows one standard humidifier card
with a power toggle, an Auto/Sleep/Manual mode dropdown, and a target
dial, instead of several separate entities.

It does **not** talk to the appliance directly. It has no idea the
device is a humidifier, a UART protocol, or anything hardware-specific
-- it just relays `switch.turn_on/turn_off`, `select.select_option`, and
`number.set_value` calls to entities that already exist, and mirrors
their state back. You could point this at a different set of
select/number/switch entities entirely and it would work the same way,
though it was built specifically to pair with the [ESPHome firmware
repo](https://github.com/alray31/levoit-classic300s-esphome) above.

## Why this exists instead of a plain `template:` humidifier

Worth explaining, since it's not obvious: Home Assistant's built-in
`template` integration does **not** have a `humidifier` platform,
unlike `switch`, `light`, `select`, `number`, etc., which all have one.
Confirmed directly against the Home Assistant core source -- every
sibling platform file exists under `homeassistant/components/template/`
(`fan.py`, `light.py`, `switch.py`, ...) except `humidifier.py`, which
simply isn't there. So a pure-YAML "template humidifier" the way you'd
do it for other domains isn't possible.

The other built-in option, [Generic
Hygrostat](https://www.home-assistant.io/integrations/generic_hygrostat/),
is a poor fit here: it makes its own on/off decisions from a humidity
sensor using its own hysteresis logic, which would fight with the
Auto/Sleep humidity-band control already running on the appliance's own
MCU. Same problem with repurposing something like [Versatile
Thermostat](https://github.com/jmcollin78/versatile_thermostat) -- it's
a `climate`-domain integration built around thermal inertia (TPI
algorithm) for heating/cooling, with no concept of humidity, and it also
wants to own the control decision itself rather than just exposing modes
a device already has.

This integration doesn't try to regulate anything -- it's a thin,
honest relay. The appliance keeps doing its own thing; Home Assistant
just gets a proper `humidifier` entity to show and control it with.

## Installation

### Via HACS (custom repository)

1. HACS -> the 3-dot menu (top right) -> **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Find "Levoit Classic 300S Humidifier Bridge" in HACS and install it.
4. Restart Home Assistant.

### Manually

1. Copy `custom_components/levoit_humidifier_bridge/` into
   `<your Home Assistant config>/custom_components/`.
2. Restart Home Assistant.

## Configuration

Find your device's real entity IDs first: **Settings -> Devices &
services -> Devices -> Levoit Classic 300S** (or whatever you named it
under `esphome: name:`) -> its Entities tab. You're looking for:

- `switch.xxx_power`
- `select.xxx_mode`
- `number.xxx_auto_target_humidity`
- `number.xxx_sleep_target_humidity`
- `number.xxx_manual_mist_level`
- `sensor.xxx_current_humidity` (optional, shows current humidity on the card)

Then add this to `configuration.yaml` (or a package), with your real
entity IDs substituted in:

```yaml
humidifier:
  - platform: levoit_humidifier_bridge
    name: "Levoit Classic 300S"
    power_switch: switch.xxx_power
    mode_select: select.xxx_mode
    auto_target: number.xxx_auto_target_humidity
    sleep_target: number.xxx_sleep_target_humidity
    manual_level: number.xxx_manual_mist_level
    current_humidity: sensor.xxx_current_humidity
```

Restart Home Assistant. The new `humidifier.levoit_classic_300s` entity
appears -- add it to a dashboard and Lovelace gives it the standard
humidifier card automatically.

## What it does, and doesn't, do

- **On/Off** is the card's power toggle, wired to `power_switch`. Off is
  not one of the modes below -- it's the entity's own on/off state,
  exactly like every other `humidifier` entity works.
- **Mode** (Auto / Sleep / Manual) is wired to `mode_select`.
- **Target dial** depends on the currently active mode:
  - Auto -> reads/writes `auto_target` (30-80%, a real humidity target)
  - Sleep -> reads/writes `sleep_target` (30-80%, a real humidity target)
  - Manual -> reads/writes `manual_level` (1-9, a mist *level*, not a
    real humidity percentage)
- **In Manual mode the dial genuinely runs 1-9** instead of being stuck
  on a 30-80% scale that wouldn't make sense there. One caveat: Lovelace's
  humidifier card always labels this dial with "%" no matter what
  min/max are set to -- that's hardcoded in the HA frontend, not
  something any integration can override. The dial itself works
  correctly (dragging it to "3" really does set mist level 3); it just
  displays as "3 %" instead of "Level 3". Cosmetic only.
- **Stop At Target is intentionally NOT part of this entity.** The
  `humidifier` domain only has room for on/off + one mode dropdown + one
  target dial -- there's no slot for a second, independent boolean
  setting. Keep using the Stop At Target switch from the ESPHome
  firmware's `common_entities.yaml` on its own, next to this card.

## Limitations

- Purely a relay: if an underlying entity (select/number/switch) becomes
  `unavailable` (e.g. the ESPHome device loses WiFi), this entity
  reflects that correctly, but has no extra diagnostics beyond what the
  underlying entities already report.
- YAML only, no config flow / UI setup -- deliberately, to keep this
  simple for a single device.

## Credit

Built to sit on top of
[alray31/levoit-classic300s-esphome](https://github.com/alray31/levoit-classic300s-esphome),
the ESPHome firmware that replaces the stock WiFi module on a Levoit
Classic 300S humidifier and exposes it locally over the A5 UART
protocol documented by
[Taxom/levoit-classic-300s-uart-protocol](https://github.com/Taxom/levoit-classic-300s-uart-protocol).
