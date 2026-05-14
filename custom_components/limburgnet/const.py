"""Constanten voor de Limburg.net integratie."""

DOMAIN = "limburgnet"
CONF_LOCATIE = "locatie"

BASE_URL    = "https://limburg.net"
LOGIN_PAGE  = "https://limburg.net/inloggen"
LOGIN_CHECK = "https://limburg.net/api-proxy/login_check"

FRACTIES = ["restfractie", "gft"]

FRACTIE_NAMEN = {
    "restfractie": "Restfractie (Huisvuil)",
    "gft":         "GFT (Groente, Fruit, Tuin)",
}

SCAN_INTERVAL_HOURS = 6

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)
