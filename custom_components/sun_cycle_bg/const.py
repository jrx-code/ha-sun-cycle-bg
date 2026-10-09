"""Constants for the sun-cycle-bg profiles store."""

DOMAIN = "sun_cycle_bg"
STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1
# a profile is a whole card config; keep a sane ceiling on what one write takes
MAX_PROFILE_BYTES = 256 * 1024
