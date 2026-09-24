"""Constants for the Levoit Classic 300S humidifier bridge."""

DOMAIN = "levoit_humidifier_bridge"

CONF_POWER_SWITCH = "power_switch"
CONF_MODE_SELECT = "mode_select"
CONF_AUTO_TARGET = "auto_target"
CONF_SLEEP_TARGET = "sleep_target"
CONF_MANUAL_LEVEL = "manual_level"
CONF_CURRENT_HUMIDITY = "current_humidity"

# Must match components/lv_classic300s_humidifier/select.py's MODE_OPTIONS
# in the ESPHome firmware repo exactly.
MODE_AUTO = "auto"
MODE_SLEEP = "sleep"
MODE_MANUAL = "manual"
AVAILABLE_MODES = [MODE_AUTO, MODE_SLEEP, MODE_MANUAL]

# Must match components/lv_classic300s_humidifier/number.py's min/max for
# auto_target_humidity / sleep_target_humidity (30-80, real %) and
# manual_level (1-9, a mist level -- not a real humidity %).
AUTO_SLEEP_MIN_HUMIDITY = 30
AUTO_SLEEP_MAX_HUMIDITY = 80
MANUAL_MIN_LEVEL = 1
MANUAL_MAX_LEVEL = 9

DEFAULT_NAME = "Levoit Classic 300S"
