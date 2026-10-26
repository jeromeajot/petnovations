"""Constants for the Petnovations / CatGenie integration."""

DOMAIN = "petnovations"

BASE_URL = "https://iot.petnovations.com"

# Config entry keys
CONF_HMAC_KEY = "hmac_key"  # the 32-char signing key, OR the 84-char secret
CONF_REFRESH_TOKEN = "refresh_token"
CONF_ACCESS_TOKEN = "access_token"  # cached, refreshed automatically
CONF_SCAN_INTERVAL = "scan_interval"

# Poll the cloud at a sane cadence. The original integration polled every 5
# seconds, which is abusive and pointless for a litter box. Default 60s.
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30

# Device list: the signed render path equals the URL path here.
DEVICES_PATH = "device/device/v2"
DEVICES_PARAMS = {"useFleetIndexAndGetRealConnectivity": "true"}

# Token refresh. The app signs the path WITHOUT the "facade/v1/" service prefix,
# but sends the request to the full URL. Confirmed against captured traffic.
REFRESH_URL_PATH = "facade/v1/mobile-user/refreshToken/v2"
REFRESH_SIGN_PATH = "mobile-user/refreshToken/v2"

# operationStatus.state values
STATE_IDLE = 0
STATE_CLEANING = 1
STATE_PAUSED = 2
