"""Constanten voor de Limburg.net integratie."""

DOMAIN = "limburgnet"

BASE_URL    = "https://limburg.net"
LOGIN_PAGE  = "https://limburg.net/inloggen"
LOGIN_CHECK = "https://limburg.net/api-proxy/login_check"
API_PROXY   = f"{BASE_URL}/api-proxy"

# Huis-aan-huis fracties
FRACTIES = ["restfractie", "gft"]

FRACTIE_NAMEN = {
    "restfractie": "Restfractie (Huisvuil)",
    "gft":         "GFT (Groente, Fruit, Tuin)",
}

# Containerpark quota API
RECYCLEPARK_QUOTA_URL = f"{API_PROXY}/recyclagepark/quotum/fracties"

# Saldo / afvalbelasting — paths from limnet.js authorizedRequest()
HUIDIG_SALDO_URL = f"{API_PROXY}/huidig-saldo"
SALDO_BEWEGINGEN_URL = f"{API_PROXY}/saldo/bewegingen"
SALDO_TIMELINE_URL = f"{API_PROXY}/saldo/bewegingen-timeline"
SALDO_BEWEGINGEN_JAAR_URL = f"{API_PROXY}/saldo/bewegingen-per-jaar"
OPENSTAAND_URL = f"{API_PROXY}/afvalbelasting/saldo/totaal-openstaand"
KOHIER_ARTIKEL_URL = f"{API_PROXY}/afvalbelasting/kohier-artikel"
# Detail endpoints need kohier/aanslag id:
#   /afvalbelasting/kohier-artikel/{id}/aanslagbiljetten
#   /afvalbelasting/kohier-artikel/{id}/saldo-directe-inning
#   /afvalbelasting/aanslagbiljet/{id}

# Park & slimmesorteerpunten
PARKBEZOEK_HISTORIEK_URL = f"{API_PROXY}/parkbezoek-historiek"
SLIMME_SORTEERPUNTEN_USER_URL = f"{API_PROXY}/slimme-sorteerpunten/user-extension"
SLIMME_SORTEERPUNTEN_HISTORIEK_URL = f"{API_PROXY}/slimme-sorteerpunten/list-historiek-puntensaldo"
SLIMME_SORTEERPUNTEN_ACTIES_URL = f"{API_PROXY}/slimme-sorteerpunten/list-acties"

# Ophaling aan huis (optioneel)
OPHALING_OVERZICHT_URL = f"{API_PROXY}/ophaling-aan-huis/overzicht/list"

SCAN_INTERVAL_HOURS = 6

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/148.0.0.0 Safari/537.36"
)
