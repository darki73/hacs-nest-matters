"""Constants for the Nest Matters integration."""
from homeassistant.const import Platform

DOMAIN = "nest_matters"
PLATFORMS = [Platform.CLIMATE, Platform.SENSOR]

# Configuration keys
CONF_MATTER_ENTITY = "matter_entity"
CONF_GOOGLE_ENTITY = "google_entity"
