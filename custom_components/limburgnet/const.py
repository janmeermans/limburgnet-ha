"""Constanten voor de Limburg.net integratie."""

DOMAIN = "limburgnet"

BASE_URL    = "https://limburg.net"
LOGIN_PAGE  = "https://limburg.net/inloggen"
LOGIN_CHECK = "https://limburg.net/api-proxy/login_check"

# Huis-aan-huis fracties
FRACTIES = ["restfractie", "gft"]

FRACTIE_NAMEN = {
    "restfractie": "Restfractie (Huisvuil)",
    "gft":         "GFT (Groente, Fruit, Tuin)",
}

# Containerpark quota API
RECYCLEPARK_QUOTA_URL = f"{BASE_URL}/api-proxy/recyclepark/quotum/fracties"

SCAN_INTERVAL_HOURS = 6

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)
