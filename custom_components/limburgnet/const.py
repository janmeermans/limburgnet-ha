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

# Rekenstaat / afvalbelasting
REKENSTAAT_OPENSTAAND_URL = f"{API_PROXY}/rekenstaat/totaal-openstaand"
REKENSTAAT_HUIDIG_SALDO_URL = f"{API_PROXY}/rekenstaat/huidig-saldo"
REKENSTAAT_BEWEGINGEN_URL = f"{API_PROXY}/rekenstaat/bewegingen"
REKENSTAAT_TIMELINE_URL = f"{API_PROXY}/rekenstaat/bewegingen-timeline"
REKENSTAAT_DIRECTE_INNING_URL = f"{API_PROXY}/rekenstaat/saldo-directe-inning"
KOHIER_ARTIKEL_URL = f"{API_PROXY}/kohier-artikel"
AANSLAGBILJETTEN_URL = f"{API_PROXY}/aanslagbiljetten"

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
