"""Constants for Rise Gardens integration."""

DOMAIN = "rise_garden"

# Auth0 Configuration
AUTH0_DOMAIN = "rise-api-prod.auth0.com"
CLIENT_ID = "emZRRctislhPO5ghhbWsJi5DNbvl4yUt"
REALM = "Username-Password-Authentication"
GRANT_TYPE = "http://auth0.com/oauth/grant-type/password-realm"
SCOPE = "openid profile email offline_access"

# API Configuration
API_BASE = "https://prod-api.risegds.com/v2"

# Config keys are imported from homeassistant.const

# Update interval (seconds)
UPDATE_INTERVAL = 60

# Platforms
PLATFORMS = ["sensor", "light"]
