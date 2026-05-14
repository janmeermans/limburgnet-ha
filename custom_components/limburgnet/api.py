"""Limburg.net API client."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests

from .const import BASE_URL, LOGIN_CHECK, LOGIN_PAGE, RECYCLEPARK_QUOTA_URL, USER_AGENT

_LOGGER = logging.getLogger(__name__)

# Standaard headers voor API calls
def _api_headers(token: str, referer: str) -> dict:
    return {
        "User-Agent":      USER_AGENT,
        "Accept":          "application/json, text/plain, */*",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Authorization":   f"Bearer {token}",
        "Referer":         referer,
        "Origin":          BASE_URL,
        "Sec-Fetch-Dest":  "empty",
        "Sec-Fetch-Mode":  "cors",
        "Sec-Fetch-Site":  "same-origin",
    }


class LimburgNetAPI:
    """Client voor de Limburg.net API."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def haal_alle_data_op(self) -> dict:
        """Login en haal alle data op: ledigingen + containerpark quota."""
        token = self._login()
        resultaat = {
            "ledigingen": {},
            "quota":      [],
        }

        # Huis-aan-huis ledigingen
        from .const import FRACTIES
        for fractie in FRACTIES:
            try:
                data   = self._haal_ledigingen_op(token, fractie)
                leging = self._parse_laatste_leging(data, fractie)
                resultaat["ledigingen"][fractie] = leging
                _LOGGER.debug("✅ leging %s: %s kg op %s", fractie, leging["gewicht_kg"], leging["datum"])
            except Exception as err:
                _LOGGER.error("Fout bij ophalen leging %s: %s", fractie, err)
                resultaat["ledigingen"][fractie] = None

        # Containerpark quota
        try:
            quota = self._haal_quota_op(token)
            resultaat["quota"] = quota
            _LOGGER.debug("✅ %d containerpark fracties opgehaald", len(quota))
        except Exception as err:
            _LOGGER.error("Fout bij ophalen containerpark quota: %s", err)

        return resultaat

    # ── LOGIN ────────────────────────────────────────────────────

    def _login(self) -> str:
        """Login op Limburg.net en geef JWT token terug."""
        session = requests.Session()
        session.headers.update({
            "User-Agent":      USER_AGENT,
            "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
        })
        session.get(LOGIN_PAGE, allow_redirects=True, timeout=20)

        session.headers.update({
            "Accept":             "application/json, text/plain, */*",
            "Content-Type":       "application/x-www-form-urlencoded",
            "Origin":             BASE_URL,
            "Referer":            LOGIN_PAGE,
            "Sec-Fetch-Dest":     "empty",
            "Sec-Fetch-Mode":     "cors",
            "Sec-Fetch-Site":     "same-origin",
            "Sec-Ch-Ua":          '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "Sec-Ch-Ua-Mobile":   "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Priority":           "u=1, i",
        })

        resp = session.post(LOGIN_CHECK, data={
            "useAuthenticator": "1",
            "email":            self._username,
            "password":         self._password,
        }, timeout=20)

        if resp.status_code != 200:
            raise ValueError(f"Login mislukt (HTTP {resp.status_code}): controleer je e-mail en wachtwoord")

        try:
            data = resp.json()
        except json.JSONDecodeError as err:
            raise ValueError("Onverwacht antwoord van server") from err

        token = (
            data.get("token")
            or (data.get("data") or {}).get("jwtToken")
            or data.get("jwtToken")
            or ""
        )
        if not token:
            raise ValueError("Geen token ontvangen — controleer je inloggegevens")
        return token

    # ── HUIS-AAN-HUIS ────────────────────────────────────────────

    def _haal_ledigingen_op(self, token: str, fractie: str) -> list:
        """Haal ledigingen op voor één fractie."""
        url  = f"{BASE_URL}/api-proxy/container/ledigingen/{fractie}"
        resp = requests.get(
            url,
            headers=_api_headers(token, f"{BASE_URL}/mijn-limburg/huis-aan-huis-ophalingen"),
            timeout=20,
            allow_redirects=True,
        )
        if resp.status_code == 401:
            raise ValueError("Token verlopen")
        if resp.status_code == 404:
            raise ValueError(f"Fractie '{fractie}' niet gevonden")
        resp.raise_for_status()
        try:
            return resp.json()
        except json.JSONDecodeError as err:
            raise ValueError(f"Ongeldig antwoord voor {fractie}") from err

    def _parse_laatste_leging(self, data: list | dict, fractie: str) -> dict:
        """Extraheer de meest recente leging uit de API-response."""
        if isinstance(data, list):
            if not data:
                raise ValueError(f"Geen data voor {fractie}")
            ledigingen_obj = data[0].get("ledigingen", {})
            ledigingen = ledigingen_obj.get("ledigingen") or []
            if not ledigingen and isinstance(ledigingen_obj, dict):
                for v in ledigingen_obj.values():
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        ledigingen = v
                        break
        else:
            ledigingen = data.get("ledigingen") or []

        if not ledigingen:
            raise ValueError(f"Geen ledigingen voor {fractie}")

        def datum_key(item: dict) -> datetime:
            raw = item.get("datum") or ""
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return datetime.min.replace(tzinfo=timezone.utc)

        laatste = sorted(ledigingen, key=datum_key, reverse=True)[0]

        datum_raw = laatste.get("datum") or ""
        try:
            dt        = datetime.fromisoformat(datum_raw.replace("Z", "+00:00"))
            datum_str = dt.strftime("%d/%m/%Y %H:%M")
            datum_iso = dt.isoformat()
        except (ValueError, AttributeError):
            datum_str = datum_raw
            datum_iso = datum_raw

        try:
            gewicht_kg = round(float(
                laatste.get("opgehaaldeKgs") or laatste.get("opgehaaldGewicht") or 0
            ), 2)
        except (TypeError, ValueError):
            gewicht_kg = 0.0

        try:
            bedrag_raw = laatste.get("bedrag")
            if bedrag_raw is None:
                bedrag_raw = laatste.get("totaalBedrag") or 0
            bedrag = round(float(bedrag_raw), 2)
        except (TypeError, ValueError):
            bedrag = 0.0

        try:
            prijs_per_kg = float(laatste.get("prijsPerKgs") or laatste.get("prijsPerKg") or 0.0)
        except (TypeError, ValueError):
            prijs_per_kg = 0.0

        return {
            "gewicht_kg":     gewicht_kg,
            "datum":          datum_str,
            "datum_iso":      datum_iso,
            "betaald_bedrag": bedrag,
            "prijs_per_kg":   prijs_per_kg,
            "fractie":        fractie,
        }

    # ── CONTAINERPARK QUOTA ──────────────────────────────────────

    def _haal_quota_op(self, token: str) -> list[dict]:
        """Haal containerpark quota op voor alle fracties."""
        resp = requests.get(
            RECYCLEPARK_QUOTA_URL,
            headers=_api_headers(token, f"{BASE_URL}/mijn-limburg/quota"),
            timeout=20,
            allow_redirects=True,
        )
        if resp.status_code == 401:
            raise ValueError("Token verlopen")
        if resp.status_code == 404:
            raise ValueError("Containerpark quota endpoint niet gevonden")
        resp.raise_for_status()

        try:
            data = resp.json()
        except json.JSONDecodeError as err:
            raise ValueError("Ongeldig antwoord voor containerpark quota") from err

        # data is een lijst van fracties
        # Elk item: {"quotumNummer": "51", "fractie": "Tuinafval",
        #            "aantal": "400", "resterendAantal": "400",
        #            "eenheid": "Kg", "tariefBedrag": "0.05"}
        resultaat = []
        for item in (data if isinstance(data, list) else []):
            try:
                resterend = float(item.get("resterendAantal") or 0)
                totaal    = float(item.get("aantal") or 0)
                resultaat.append({
                    "fractie":          item.get("fractie", ""),
                    "quotum_nummer":    item.get("quotumNummer", ""),
                    "resterend_aantal": resterend,
                    "totaal_aantal":    totaal,
                    "eenheid":          item.get("eenheid", "Kg"),
                    "tarief_bedrag":    float(item.get("tariefBedrag") or 0),
                })
            except (TypeError, ValueError) as err:
                _LOGGER.warning("Kon quota item niet parsen: %s — %s", item, err)

        return resultaat
