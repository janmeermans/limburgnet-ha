"""Limburg.net API client."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

import requests

from .const import (
    BASE_URL,
    LOGIN_CHECK,
    LOGIN_PAGE,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


class LimburgNetAPI:
    """Client voor de Limburg.net API."""

    def __init__(self, username: str, password: str, locatie: str = "") -> None:
        self._username = username
        self._password = password
        self._locatie  = locatie

    def haal_ledigingen_op(self) -> dict[str, dict]:
        """
        Login en haal ledigingen op voor alle fracties.
        Geeft een dict terug: {"restfractie": {...}, "gft": {...}}
        """
        token = self._login()
        resultaat = {}

        from .const import FRACTIES
        for fractie in FRACTIES:
            try:
                data   = self._haal_fractie_op(token, fractie)
                leging = self._parse_laatste_leging(data, fractie)
                resultaat[fractie] = leging
                _LOGGER.debug("✅ %s: %s kg op %s", fractie, leging["gewicht_kg"], leging["datum"])
            except Exception as err:
                _LOGGER.error("Fout bij ophalen %s: %s", fractie, err)
                resultaat[fractie] = None

        return resultaat

    def _login(self) -> str:
        """Login op Limburg.net en geef JWT token terug."""
        session = requests.Session()

        if self._locatie:
            session.cookies.set("locatie", self._locatie, domain=".limburg.net")

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

        payload = {
            "useAuthenticator": "1",
            "email":            self._username,
            "password":         self._password,
        }

        resp = session.post(LOGIN_CHECK, data=payload, timeout=20)

        if resp.status_code != 200:
            raise ValueError(f"Login mislukt (HTTP {resp.status_code}): controleer je e-mail en wachtwoord")

        try:
            data = resp.json()
        except json.JSONDecodeError as err:
            raise ValueError(f"Onverwacht antwoord van server: {resp.text[:200]}") from err

        token = (
            data.get("token")
            or (data.get("data") or {}).get("jwtToken")
            or data.get("jwtToken")
            or data.get("access_token")
            or ""
        )

        if not token:
            raise ValueError("Geen token ontvangen — controleer je inloggegevens")

        return token

    def _haal_fractie_op(self, token: str, fractie: str) -> list:
        """Haal ledigingen op voor één fractie."""
        headers = {
            "User-Agent":      USER_AGENT,
            "Accept":          "application/json, text/plain, */*",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Authorization":   f"Bearer {token}",
            "Referer":         f"{BASE_URL}/mijn-limburg/huis-aan-huis-ophalingen",
            "Origin":          BASE_URL,
            "Sec-Fetch-Dest":  "empty",
            "Sec-Fetch-Mode":  "cors",
            "Sec-Fetch-Site":  "same-origin",
        }
        if self._locatie:
            headers["Cookie"] = f"locatie={self._locatie}"

        url = f"{BASE_URL}/api-proxy/container/ledigingen/{fractie}"
        resp = requests.get(url, headers=headers, timeout=20, allow_redirects=True)

        if resp.status_code == 401:
            raise ValueError("Token verlopen — opnieuw inloggen vereist")
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
