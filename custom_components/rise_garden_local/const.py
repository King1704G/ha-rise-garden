"""Constants for the local (LAN) Rise Garden integration."""

DOMAIN = "rise_garden_local"

CONF_HOST = "host"
CONF_PORT = "port"

DEFAULT_PORT = 1000

# The controller is single-client and slow; poll gently.
UPDATE_INTERVAL = 60  # seconds

PLATFORMS = ["light", "sensor", "binary_sensor", "switch", "number"]

# Re-set the controller clock when its time of day drifts more than this (seconds).
CLOCK_MAX_DRIFT = 30

# The grow light has three independently dimmable channels: "lamp <1-3> <0-100>".
LAMP_CHANNELS = (1, 2, 3)
