# Levoit Classic 300S -- Humidifier Bridge (HACS)

A tiny Home Assistant custom integration that combines the entities
already exposed by the [Levoit Classic 300S ESPHome
firmware](https://github.com/alray31/levoit-classic300s-esphome) (a
`select` for mode, three `number` entities for Auto/Sleep target and
Manual level, and a `switch` for power) into a single native
`humidifier` entity -- so Lovelace shows one standard humidifier card
with a power toggle, an Auto/Sleep/Manual mode dropdown, and a target
dial, instead of several separate entities.

Set up entirely through the UI (Settings -> Devices & services -> Add
integration) -- no YAML to edit. The setup form auto-detects your
device's entities and pre-fills them; you just confirm.

It does **not** talk to the appliance directly. It has no idea the
device is a humidifier, a UART protocol, or anything hardware-specific
-- it just relays `switch.turn_on/turn_off`, `select.select_option`, and
`number.set_value` calls to entities that already exist, and mirrors
their state back.

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
MCU.

There's also a third-party HACS integration,
[tsunglung/hass_humidifier_template](https://github.com/tsunglung/hass_humidifier_template),
which is a genuine templated humidifier platform -- but its
`min_humidity`/`max_humidity` are fixed at setup time (static config
values, not templates), so it can't give Manual mode its own 1-9 dial
range the way this integration does; you'd be stuck with one fixed
range across all three modes.

This integration doesn't try to regulate anything -- it's a thin,
honest relay. The appliance keeps doing its own thing; Home Assistant
just gets a proper `humidifier` entity to show and control it with.

## Installation

### Via HACS (custom repository)

1. HACS -> the 3-dot menu (top right) -> **Custom repositories**.
2. Add this repository's URL, category **Integration**.
3. Find "Levoit Classic 300S Humidifier Card" in HACS and install it.
4. Restart Home Assistant.

### Manually

1. Copy `custom_components/levoit_humidifier_bridge/` into
   `<your Home Assistant config>/custom_components/`.
2. Restart Home Assistant.

## Configuration

No YAML. After restarting:

1. **Settings -> Devices & services -> Add integration**.
2. Search for **"Levoit Classic 300S Humidifier Card"**.
3. A form appears. If you haven't renamed any of the ESPHome entities,
   every field is already filled in -- just hit **Submit**.

### How the auto-detection works

The form first looks for the one `select` entity anywhere in Home
Assistant whose `options` are exactly `auto`/`manual`/`sleep` -- that's
distinctive enough to reliably find the right device even if you have
several ESPHome devices. From there, it looks at every other entity on
that same device and matches them by their default friendly name from
`common_entities.yaml`: "Power", "Auto Target Humidity", "Sleep Target
Humidity", "Manual Mist Level", "Current Humidity".

Every field on the form is still a normal entity picker/dropdown,
though -- so if a guess is missing or wrong (you renamed something, or
have an unusual setup), just pick the right entity yourself. Nothing is
hardcoded or required to match exactly.

To bridge more than one Classic 300S, just run "Add integration" again
-- each one becomes its own config entry.

## What it does, and doesn't, do

- **On/Off** is the card's power toggle, wired to the Power switch you
  picked. Off is not one of the modes below -- it's the entity's own
  on/off state, exactly like every other `humidifier` entity works.
- **Mode** (Auto / Sleep / Manual) is wired to the mode select you
  picked.
- **Target dial** depends on the currently active mode:
  - Auto -> reads/writes Auto Target Humidity (30-80%, a real humidity
    target)
  - Sleep -> reads/writes Sleep Target Humidity (30-80%, a real
    humidity target)
  - Manual -> reads/writes Manual Mist Level (1-9, a mist *level*, not
    a real humidity percentage)
- **In Manual mode the dial genuinely runs 1-9** instead of being stuck
  on a 30-80% scale that wouldn't make sense there. One caveat:
  Lovelace's humidifier card always labels this dial with "%" no matter
  what min/max are set to -- that's hardcoded in the HA frontend, not
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
- No options flow yet to change the entity mapping after initial setup
  -- if you need to repoint it at different entities, remove the config
  entry and add it again.

## Credit

Built to sit on top of
[alray31/levoit-classic300s-esphome](https://github.com/alray31/levoit-classic300s-esphome),
the ESPHome firmware that replaces the stock WiFi module on a Levoit
Classic 300S humidifier and exposes it locally over the A5 UART
protocol documented by
[Taxom/levoit-classic-300s-uart-protocol](https://github.com/Taxom/levoit-classic-300s-uart-protocol).
