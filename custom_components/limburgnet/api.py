"""Limburg.net API client."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from .const import (
    AANSLAGBILJETTEN_URL,
    BASE_URL,
    KOHIER_ARTIKEL_URL,
    LOGIN_CHECK,
    LOGIN_PAGE,
    OPHALING_OVERZICHT_URL,
    PARKBEZOEK_HISTORIEK_URL,
    RECYCLEPARK_QUOTA_URL,
    REKENSTAAT_BEWEGINGEN_URL,
    REKENSTAAT_DIRECTE_INNING_URL,
    REKENSTAAT_HUIDIG_SALDO_URL,
    REKENSTAAT_OPENSTAAND_URL,
    REKENSTAAT_TIMELINE_URL,
    SLIMME_SORTEERPUNTEN_ACTIES_URL,
    SLIMME_SORTEERPUNTEN_HISTORIEK_URL,
    SLIMME_SORTEERPUNTEN_USER_URL,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)


def _api_headers(token: str, referer: str) -> dict:
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Authorization": f"Bearer {token}",
        "Referer": referer,
        "Origin": BASE_URL,
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
    }


def _to_float(value) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def _pick(item: dict, *keys, default=None):
    for key in keys:
        if key in item and item[key] is not None:
            return item[key]
    return default


class LimburgNetAPI:
    """Client voor de Limburg.net API."""

    def __init__(self, username: str, password: str) -> None:
        self._username = username
        self._password = password

    def haal_alle_data_op(self) -> dict:
        """Login en haal alle gekende account-data op."""
        token = self._login()
        resultaat: dict = {
            "ledigingen": {},
            "quota": [],
            "rekenstaat": {},
            "parkbezoeken": {},
            "slimme_sorteerpunten": {},
            "ophaling_overzicht": None,
        }

        from .const import FRACTIES

        for fractie in FRACTIES:
            try:
                data = self._haal_ledigingen_op(token, fractie)
                leging = self._parse_laatste_leging(data, fractie)
                resultaat["ledigingen"][fractie] = leging
                _LOGGER.debug(
                    "✅ leging %s: %s kg op %s (%d in historie)",
                    fractie,
                    leging["gewicht_kg"],
                    leging["datum"],
                    len(leging.get("historie") or []),
                )
            except Exception as err:
                _LOGGER.error("Fout bij ophalen leging %s: %s", fractie, err)
                resultaat["ledigingen"][fractie] = None

        try:
            resultaat["quota"] = self._haal_quota_op(token)
            _LOGGER.debug("✅ %d containerpark fracties opgehaald", len(resultaat["quota"]))
        except Exception as err:
            _LOGGER.error("Fout bij ophalen containerpark quota: %s", err)

        resultaat["rekenstaat"] = self._haal_rekenstaat_blok(token)
        resultaat["parkbezoeken"] = self._haal_parkbezoeken(token)
        resultaat["slimme_sorteerpunten"] = self._haal_slimme_sorteerpunten(token)

        try:
            resultaat["ophaling_overzicht"] = self._haal_ophaling_overzicht(token)
        except Exception as err:
            _LOGGER.warning("Ophaling-overzicht niet beschikbaar: %s", err)
            resultaat["ophaling_overzicht"] = None

        return resultaat

    def _haal_rekenstaat_blok(self, token: str) -> dict:
        blok: dict = {
            "openstaand": None,
            "huidig_saldo": None,
            "bewegingen": [],
            "timeline": [],
            "directe_inning": None,
            "kohier": [],
            "aanslagbiljetten": None,
        }
        try:
            blok["openstaand"] = self._parse_openstaand(
                self._get_json(token, REKENSTAAT_OPENSTAAND_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("totaal-openstaand mislukt: %s", err)

        try:
            blok["huidig_saldo"] = self._parse_huidig_saldo(
                self._get_json(token, REKENSTAAT_HUIDIG_SALDO_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("huidig-saldo mislukt: %s", err)

        try:
            blok["bewegingen"] = self._parse_bewegingen(
                self._get_json(token, REKENSTAAT_BEWEGINGEN_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("bewegingen mislukt: %s", err)

        try:
            blok["timeline"] = self._parse_bewegingen(
                self._get_json(token, REKENSTAAT_TIMELINE_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("bewegingen-timeline mislukt: %s", err)

        try:
            blok["directe_inning"] = self._parse_directe_inning(
                self._get_json(token, REKENSTAAT_DIRECTE_INNING_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("saldo-directe-inning mislukt: %s", err)

        try:
            blok["kohier"] = self._parse_kohier(
                self._get_json(token, KOHIER_ARTIKEL_URL, f"{BASE_URL}/mijn-limburg/afvalbelasting")
            )
        except Exception as err:
            _LOGGER.warning("kohier-artikel mislukt: %s", err)

        try:
            list_data = self._get_json(token, AANSLAGBILJETTEN_URL, f"{BASE_URL}/mijn-limburg/afvalbelasting")
            blok["aanslagbiljetten"] = self._parse_aanslagbiljetten(list_data)
            detail_id = (blok["aanslagbiljetten"] or {}).get("eerste_id")
            if detail_id is not None:
                try:
                    detail = self._get_json(
                        token,
                        f"{AANSLAGBILJETTEN_URL}/{detail_id}",
                        f"{BASE_URL}/mijn-limburg/afvalbelasting",
                    )
                    blok["aanslagbiljetten"]["detail"] = self._parse_aanslag_detail(detail)
                except Exception as err:
                    _LOGGER.warning("aanslagbiljet detail %s mislukt: %s", detail_id, err)
        except Exception as err:
            _LOGGER.warning("aanslagbiljetten mislukt: %s", err)

        return blok

    def _haal_parkbezoeken(self, token: str) -> dict:
        try:
            data = self._get_json(token, PARKBEZOEK_HISTORIEK_URL, f"{BASE_URL}/mijn-limburg/historiek-parkbezoeken")
            return self._parse_parkbezoeken(data)
        except Exception as err:
            _LOGGER.warning("parkbezoek-historiek mislukt: %s", err)
            return {"recente": [], "laatste": None, "kosten_dit_jaar": 0.0}

    def _haal_slimme_sorteerpunten(self, token: str) -> dict:
        out: dict = {"saldo": None, "historiek": [], "acties": [], "raw_user": None}
        try:
            user = self._get_json(
                token, SLIMME_SORTEERPUNTEN_USER_URL, f"{BASE_URL}/mijn-limburg/slimmesorteerpunten/saldo-en-transacties"
            )
            out["raw_user"] = user if isinstance(user, dict) else None
            out["saldo"] = self._parse_punten_saldo(user)
        except Exception as err:
            _LOGGER.warning("slimme-sorteerpunten user-extension mislukt: %s", err)

        try:
            year = datetime.now().year
            params = urlencode({"dateFrom": f"{year}-01-01", "dateTo": f"{year}-12-31"})
            hist = self._get_json(
                token,
                f"{SLIMME_SORTEERPUNTEN_HISTORIEK_URL}?{params}",
                f"{BASE_URL}/mijn-limburg/slimmesorteerpunten/saldo-en-transacties",
            )
            out["historiek"] = hist if isinstance(hist, list) else (hist.get("historiek") if isinstance(hist, dict) else []) or []
        except Exception as err:
            _LOGGER.warning("slimme-sorteerpunten historiek mislukt: %s", err)

        try:
            acties = self._get_json(
                token, SLIMME_SORTEERPUNTEN_ACTIES_URL, f"{BASE_URL}/mijn-limburg/slimmesorteerpunten/mijn-acties"
            )
            out["acties"] = acties if isinstance(acties, list) else (acties.get("acties") if isinstance(acties, dict) else []) or []
        except Exception as err:
            _LOGGER.warning("slimme-sorteerpunten acties mislukt: %s", err)

        return out

    def _haal_ophaling_overzicht(self, token: str):
        data = self._get_json(token, OPHALING_OVERZICHT_URL, f"{BASE_URL}/mijn-limburg/ophaling-aan-huis-overview")
        if isinstance(data, list):
            return data[:20]
        if isinstance(data, dict):
            for key in ("list", "items", "overzicht", "data"):
                if isinstance(data.get(key), list):
                    return data[key][:20]
            return data
        return None

    def _get_json(self, token: str, url: str, referer: str):
        resp = requests.get(url, headers=_api_headers(token, referer), timeout=20, allow_redirects=True)
        if resp.status_code == 401:
            raise ValueError("Token verlopen")
        if resp.status_code == 404:
            raise ValueError(f"Endpoint niet gevonden: {url}")
        resp.raise_for_status()
        try:
            return resp.json()
        except json.JSONDecodeError as err:
            raise ValueError(f"Ongeldig JSON van {url}") from err

    def _login(self) -> str:
        session = requests.Session()
        session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
        })
        session.get(LOGIN_PAGE, allow_redirects=True, timeout=20)
        session.headers.update({
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": BASE_URL,
            "Referer": LOGIN_PAGE,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Ch-Ua": '"Chromium";v="148", "Google Chrome";v="148", "Not/A)Brand";v="99"',
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": '"Windows"',
            "Priority": "u=1, i",
        })
        resp = session.post(LOGIN_CHECK, data={
            "useAuthenticator": "1",
            "email": self._username,
            "password": self._password,
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

    def _haal_ledigingen_op(self, token: str, fractie: str) -> list:
        url = f"{BASE_URL}/api-proxy/container/ledigingen/{fractie}"
        data = self._get_json(token, url, f"{BASE_URL}/mijn-limburg/huis-aan-huis-ophalingen")
        return data

    def _extract_ledigingen_lijst(self, data: list | dict, fractie: str) -> list:
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
        return ledigingen

    def _parse_leging_item(self, item: dict, fractie: str) -> dict:
        datum_raw = item.get("datum") or ""
        try:
            dt = datetime.fromisoformat(datum_raw.replace("Z", "+00:00"))
            datum_str = dt.strftime("%d/%m/%Y %H:%M")
            datum_iso = dt.isoformat()
        except (ValueError, AttributeError):
            datum_str = datum_raw
            datum_iso = datum_raw
        gewicht_kg = _to_float(item.get("opgehaaldeKgs") or item.get("opgehaaldGewicht")) or 0.0
        bedrag_raw = item.get("bedrag")
        if bedrag_raw is None:
            bedrag_raw = item.get("totaalBedrag") or 0
        bedrag = _to_float(bedrag_raw) or 0.0
        prijs_per_kg = _to_float(item.get("prijsPerKgs") or item.get("prijsPerKg")) or 0.0
        return {
            "gewicht_kg": gewicht_kg,
            "datum": datum_str,
            "datum_iso": datum_iso,
            "betaald_bedrag": bedrag,
            "prijs_per_kg": prijs_per_kg,
            "fractie": fractie,
        }

    def _parse_laatste_leging(self, data: list | dict, fractie: str) -> dict:
        ruwe = self._extract_ledigingen_lijst(data, fractie)

        def datum_key(item: dict) -> datetime:
            raw = item.get("datum") or ""
            try:
                return datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return datetime.min.replace(tzinfo=timezone.utc)

        gesorteerd = sorted(ruwe, key=datum_key, reverse=True)
        historie = [self._parse_leging_item(item, fractie) for item in gesorteerd]
        laatste = dict(historie[0])
        laatste["historie"] = historie
        return laatste

    def _haal_quota_op(self, token: str) -> list[dict]:
        data = self._get_json(token, RECYCLEPARK_QUOTA_URL, f"{BASE_URL}/mijn-limburg/quota")
        resultaat = []
        for item in (data if isinstance(data, list) else []):
            try:
                resterend = float(item.get("resterendAantal") or 0)
                totaal = float(item.get("aantal") or 0)
                resultaat.append({
                    "fractie": item.get("fractie", ""),
                    "quotum_nummer": item.get("quotumNummer", ""),
                    "resterend_aantal": resterend,
                    "totaal_aantal": totaal,
                    "eenheid": item.get("eenheid", "Kg"),
                    "tarief_bedrag": float(item.get("tariefBedrag") or 0),
                })
            except (TypeError, ValueError) as err:
                _LOGGER.warning("Kon quota item niet parsen: %s — %s", item, err)
        return resultaat

    def _parse_openstaand(self, data) -> dict:
        if not isinstance(data, dict):
            data = {}
        return {
            "totaal_bedrag": _to_float(_pick(data, "totaalBedrag", "totaal", "bedrag", "amount")),
            "datum_laatste_update": _pick(data, "datumLaatsteUpdate", "laatsteUpdate", "updatedAt"),
            "rekening_nummer": _pick(data, "rekeningNummer", "rekeningnummer", "iban"),
            "raw_keys": sorted(list(data.keys()))[:20],
        }

    def _parse_huidig_saldo(self, data) -> dict:
        if isinstance(data, list):
            saldo_lijst = data
            root = {"saldoLijst": data}
        elif isinstance(data, dict):
            root = data
            saldo_lijst = data.get("saldoLijst") or data.get("saldi") or []
        else:
            root, saldo_lijst = {}, []
        bedragen = []
        for item in saldo_lijst if isinstance(saldo_lijst, list) else []:
            if isinstance(item, dict):
                val = _to_float(_pick(item, "saldo", "bedrag", "amount", "value"))
                if val is not None:
                    bedragen.append(val)
        hoofd = _to_float(_pick(root, "saldo", "huidigSaldo", "bedrag", "amount"))
        if hoofd is None and bedragen:
            hoofd = bedragen[0]
        return {
            "saldo": hoofd,
            "saldo_lijst": saldo_lijst if isinstance(saldo_lijst, list) else [],
            "minimum_saldo": _pick(root, "minimumSaldo", "minimum", "drempel"),
        }

    def _parse_bewegingen(self, data) -> list:
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = (
                data.get("bewegingen")
                or data.get("timeline")
                or data.get("historiek")
                or data.get("items")
                or data.get("rekenstaat")
                or []
            )
            if isinstance(items, dict):
                items = items.get("bewegingen") or items.get("items") or []
        else:
            items = []
        result = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            result.append({
                "datum": _pick(item, "datum", "date", "datumIso", "datum_iso"),
                "bedrag": _to_float(_pick(item, "bedrag", "amount", "totaalBedrag")),
                "omschrijving": _pick(item, "omschrijving", "beschrijving", "description", "titel", "type"),
                "type": _pick(item, "type", "bewegingType", "eventType"),
            })
            if len(result) >= 25:
                break
        return result

    def _parse_directe_inning(self, data) -> dict:
        if not isinstance(data, dict):
            data = {}
        return {
            "saldo": _to_float(_pick(data, "saldo", "bedrag", "balance", "amount", "huidigSaldo")),
            "rekening_nummer": _pick(data, "rekeningNummer", "rekeningnummer", "iban", "accountNumber"),
            "rekenstaat": _pick(data, "rekenstaat", "rekenstaatNummer", "nummer"),
        }

    def _parse_kohier(self, data) -> list:
        items = data if isinstance(data, list) else (data.get("items") if isinstance(data, dict) else []) or []
        result = []
        for item in items:
            if not isinstance(item, dict):
                continue
            result.append({
                "id": _pick(item, "id"),
                "year": _pick(item, "year", "jaar", "anslagJaar"),
                "municipality": _pick(item, "municipality", "gemeente", "gemeenteNaam"),
                "article": _pick(item, "article", "artikel", "artikelNummer"),
                "amount": _to_float(_pick(item, "amount", "bedrag", "totaalBedrag")),
                "address": _pick(item, "address", "adres"),
                "status": _pick(item, "status"),
            })
        return result

    def _parse_aanslagbiljetten(self, data) -> dict:
        if isinstance(data, list):
            biljetten = data
            root = {}
        elif isinstance(data, dict):
            root = data
            biljetten = data.get("aanslagbiljetten") or data.get("items") or data.get("list") or []
        else:
            root, biljetten = {}, []
        compact = []
        eerste_id = None
        for item in biljetten if isinstance(biljetten, list) else []:
            if not isinstance(item, dict):
                continue
            item_id = _pick(item, "id", "aanslagbiljetId")
            if eerste_id is None and item_id is not None:
                eerste_id = item_id
            compact.append({
                "id": item_id,
                "year": _pick(item, "year", "jaar"),
                "amount": _to_float(_pick(item, "amount", "bedrag", "totaalBedrag")),
                "status": _pick(item, "status"),
                "reference": _pick(item, "paymentReference", "betalingsreferentie", "referentie"),
            })
            if len(compact) >= 10:
                break
        return {
            "betaald": _pick(root, "betaald", "paid"),
            "onvolledig": _pick(root, "onvolledig", "incomplete"),
            "overgedragen": _pick(root, "overgedragen"),
            "aantal": len(biljetten) if isinstance(biljetten, list) else len(compact),
            "recente": compact,
            "eerste_id": eerste_id,
            "detail": None,
        }

    def _parse_aanslag_detail(self, data) -> dict:
        if not isinstance(data, dict):
            return {}
        return {
            "id": _pick(data, "id"),
            "payment_reference": _pick(data, "paymentReference", "betalingsreferentie", "referentie"),
            "addresses": _pick(data, "addresses", "adressen"),
            "calculation_list": _pick(data, "calculationList", "berekening", "calculations"),
            "household_list": _pick(data, "householdList", "huishoudens", "households"),
            "amount": _to_float(_pick(data, "amount", "bedrag", "totaalBedrag")),
        }

    def _parse_parkbezoeken(self, data) -> dict:
        if isinstance(data, list):
            records = data
        elif isinstance(data, dict):
            records = data.get("historiekRecords") or data.get("historiek") or data.get("records") or data.get("items") or []
        else:
            records = []
        recente = []
        for item in records if isinstance(records, list) else []:
            if not isinstance(item, dict):
                continue
            recente.append({
                "datum": _pick(item, "datum", "date", "datumIso"),
                "activiteit": _pick(item, "activiteit", "activity", "event", "rule", "fractie"),
                "gewicht_kg": _to_float(_pick(item, "kg", "gewicht", "gewichtKg", "opgehaaldeKgs")),
                "bedrag": _to_float(_pick(item, "bedrag", "amount", "totaalBedrag")),
                "event": _pick(item, "event", "eventType", "rule"),
            })
        jaar = datetime.now().year
        kosten = 0.0
        for item in recente:
            raw = item.get("datum") or ""
            try:
                y = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).year
            except (ValueError, TypeError):
                try:
                    y = int(str(raw)[:4])
                except ValueError:
                    y = None
            if y == jaar and item.get("bedrag") is not None:
                kosten += float(item["bedrag"])
        return {
            "recente": recente[:12],
            "laatste": recente[0] if recente else None,
            "kosten_dit_jaar": round(kosten, 2),
            "aantal": len(recente),
        }

    def _parse_punten_saldo(self, data) -> float | None:
        if isinstance(data, (int, float)):
            return float(data)
        if not isinstance(data, dict):
            return None
        user = data.get("user") if isinstance(data.get("user"), dict) else data
        return _to_float(_pick(user, "saldo", "punten", "puntensaldo", "points", "balance"))
