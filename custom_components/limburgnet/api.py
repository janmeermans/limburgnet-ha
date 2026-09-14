"""Limburg.net API client."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlencode

import requests

from .const import (
    API_PROXY,
    BASE_URL,
    HUIDIG_SALDO_URL,
    KOHIER_ARTIKEL_URL,
    LOGIN_CHECK,
    LOGIN_PAGE,
    OPHALING_OVERZICHT_URL,
    OPENSTAAND_URL,
    PARKBEZOEK_HISTORIEK_URL,
    RECYCLEPARK_QUOTA_URL,
    SALDO_BEWEGINGEN_JAAR_URL,
    SALDO_BEWEGINGEN_URL,
    SALDO_TIMELINE_URL,
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
            "bewegingen_per_jaar": None,
            "directe_inning": None,
            "kohier": [],
            "aanslagbiljetten": None,
        }
        try:
            blok["openstaand"] = self._parse_openstaand(
                self._get_json(token, OPENSTAAND_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("totaal-openstaand mislukt: %s", err)

        try:
            blok["huidig_saldo"] = self._parse_huidig_saldo(
                self._get_json(token, HUIDIG_SALDO_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("huidig-saldo mislukt: %s", err)

        try:
            blok["bewegingen"] = self._parse_bewegingen(
                self._get_json(token, SALDO_BEWEGINGEN_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("bewegingen mislukt: %s", err)

        try:
            blok["timeline"] = self._parse_bewegingen(
                self._get_json(token, SALDO_TIMELINE_URL, f"{BASE_URL}/mijn-limburg/betalingen")
            )
        except Exception as err:
            _LOGGER.warning("bewegingen-timeline mislukt: %s", err)

        try:
            blok["kohier"] = self._parse_kohier(
                self._get_json(token, KOHIER_ARTIKEL_URL, f"{BASE_URL}/mijn-limburg/afvalbelasting")
            )
        except Exception as err:
            _LOGGER.warning("kohier-artikel mislukt: %s", err)

        # Aanslagbiljetten + saldo-directe-inning hangen aan een kohier-artikel id
        kohier_id = None
        for item in blok.get("kohier") or []:
            if item.get("id") is not None:
                kohier_id = item["id"]
                break

        if kohier_id is not None:
            try:
                list_data = self._get_json(
                    token,
                    f"{API_PROXY}/afvalbelasting/kohier-artikel/{kohier_id}/aanslagbiljetten",
                    f"{BASE_URL}/mijn-limburg/afvalbelasting",
                )
                blok["aanslagbiljetten"] = self._parse_aanslagbiljetten(list_data)
                blok["aanslagbiljetten"]["kohier_id"] = kohier_id
                detail_id = (blok["aanslagbiljetten"] or {}).get("eerste_id")
                if detail_id is not None:
                    try:
                        detail = self._get_json(
                            token,
                            f"{API_PROXY}/afvalbelasting/aanslagbiljet/{detail_id}",
                            f"{BASE_URL}/mijn-limburg/afvalbelasting",
                        )
                        blok["aanslagbiljetten"]["detail"] = self._parse_aanslag_detail(detail)
                    except Exception as err:
                        _LOGGER.warning("aanslagbiljet detail %s mislukt: %s", detail_id, err)
            except Exception as err:
                _LOGGER.warning("aanslagbiljetten mislukt: %s", err)

            try:
                blok["directe_inning"] = self._parse_directe_inning(
                    self._get_json(
                        token,
                        f"{API_PROXY}/afvalbelasting/kohier-artikel/{kohier_id}/saldo-directe-inning",
                        f"{BASE_URL}/mijn-limburg/afvalbelasting",
                    )
                )
            except Exception as err:
                _LOGGER.warning("saldo-directe-inning mislukt: %s", err)
        else:
            _LOGGER.debug("Geen kohier-artikel id — skip aanslagbiljetten/directe inning")

        try:
            jaar_data = self._get_json(
                token, SALDO_BEWEGINGEN_JAAR_URL, f"{BASE_URL}/mijn-limburg/betalingen"
            )
            if isinstance(jaar_data, list):
                blok["bewegingen_per_jaar"] = jaar_data[:20]
            elif isinstance(jaar_data, dict):
                blok["bewegingen_per_jaar"] = jaar_data
        except Exception as err:
            _LOGGER.warning("bewegingen-per-jaar mislukt: %s", err)

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
        rekening = _pick(data, "rekeningNummer", "rekeningnummer", "iban")
        if isinstance(rekening, str):
            rekening = rekening.strip() or None
        return {
            "totaal_bedrag": _to_float(_pick(data, "totaalBedrag", "totaal", "bedrag", "amount", "saldoRekenstaat")),
            "datum_laatste_update": _pick(data, "datumLaatsteUpdate", "laatsteUpdate", "updatedAt"),
            "rekening_nummer": rekening,
        }


    def _parse_huidig_saldo(self, data) -> dict:
        if isinstance(data, list):
            root = {"saldoLijst": data}
            saldo_lijst = data
        elif isinstance(data, dict):
            root = data
            saldo_lijst = data.get("saldoLijst") or data.get("saldi") or []
        else:
            root, saldo_lijst = {}, []

        if not isinstance(saldo_lijst, list):
            saldo_lijst = []

        gekozen = None
        for item in saldo_lijst:
            if isinstance(item, dict) and item.get("eerstGetoond"):
                gekozen = item
                break
        if gekozen is None:
            for item in saldo_lijst:
                if isinstance(item, dict):
                    gekozen = item
                    break

        saldo = None
        rekening = None
        datum = None
        if gekozen:
            saldo = _to_float(_pick(gekozen, "saldoRekenstaat", "saldo", "bedrag", "amount", "value"))
            rekening = _pick(gekozen, "rekeningNummer", "rekeningnummer")
            datum = _pick(gekozen, "datumLaatsteUpdate", "datum")
        if saldo is None:
            saldo = _to_float(_pick(root, "saldo", "huidigSaldo", "bedrag", "amount", "saldoRekenstaat"))
        if isinstance(rekening, str):
            rekening = rekening.strip() or None

        compact_lijst = []
        for item in saldo_lijst:
            if not isinstance(item, dict):
                continue
            rn = item.get("rekeningNummer")
            if isinstance(rn, str):
                rn = rn.strip()
            compact_lijst.append({
                "saldo_rekenstaat": _to_float(_pick(item, "saldoRekenstaat", "saldo")),
                "rekening_nummer": rn,
                "eerst_getoond": bool(item.get("eerstGetoond")),
                "datum_laatste_update": _pick(item, "datumLaatsteUpdate", "datum"),
            })

        return {
            "saldo": saldo,
            "rekening_nummer": rekening,
            "datum_laatste_update": datum or _pick(root, "datumLaatsteUpdate"),
            "saldo_lijst": compact_lijst,
            "minimum_saldo": {
                "rest": _to_float(root.get("minimumSaldoRestLediging")),
                "gft": _to_float(root.get("minimumSaldoGftLediging")),
                "park": _to_float(root.get("minimumSaldoVoorParkbezoek")),
            },
        }


    def _parse_bewegingen(self, data) -> list:
        """Flatten saldo/bewegingen(+timeline) grouped by rekenstaat.

        Timeline items: {datum, omschrijving, bedrag}
        Bewegingen items: {beweging: {datum, bedrag, ...}, details: [{omschrijving, ...}]}
        """
        groups: list = []
        if isinstance(data, list):
            groups = data
        elif isinstance(data, dict):
            if any(k in data for k in ("timeline", "historiek", "bewegingen")):
                groups = [data]
            else:
                groups = data.get("results") or data.get("items") or data.get("data") or []

        result = []
        for group in groups if isinstance(groups, list) else []:
            if not isinstance(group, dict):
                continue
            rekenstaat = group.get("rekenstaat") if isinstance(group.get("rekenstaat"), dict) else {}
            code = rekenstaat.get("rekenstaatCode") or group.get("rekenstaatCode")
            items = (
                group.get("timeline")
                or group.get("historiek")
                or group.get("bewegingen")
                or group.get("items")
                or []
            )
            if not items and (_pick(group, "datum", "omschrijving", "bedrag", "beweging") is not None):
                items = [group]
            if not isinstance(items, list):
                continue
            for item in items:
                if not isinstance(item, dict):
                    continue
                # /saldo/bewegingen nested shape
                if isinstance(item.get("beweging"), dict):
                    b = item["beweging"]
                    details = item.get("details") if isinstance(item.get("details"), list) else []
                    omschrijving = None
                    for d in details:
                        if isinstance(d, dict) and d.get("omschrijving"):
                            omschrijving = d.get("omschrijving")
                            break
                    result.append({
                        "datum": _pick(b, "datum", "date"),
                        "bedrag": _to_float(_pick(b, "bedrag", "amount", "mutatieSaldo")),
                        "omschrijving": omschrijving or _pick(b, "omschrijving", "activiteit", "type"),
                        "oud_saldo": _to_float(_pick(b, "oudSaldo")),
                        "nieuw_saldo": _to_float(_pick(b, "nieuwSaldo")),
                        "rekenstaat_code": code,
                        "details_count": len(details),
                    })
                else:
                    result.append({
                        "datum": _pick(item, "datum", "date", "datumIso", "datum_iso"),
                        "bedrag": _to_float(_pick(item, "bedrag", "amount", "totaalBedrag", "mutatieSaldo")),
                        "omschrijving": _pick(item, "omschrijving", "beschrijving", "description", "titel", "type"),
                        "rekenstaat_code": code,
                    })
                if len(result) >= 25:
                    return result
        return result


    def _parse_directe_inning(self, data) -> dict:
        if not isinstance(data, dict):
            data = {}
        rekening = _pick(data, "rekeningNummer", "rekeningnummer", "iban", "accountNumber")
        if isinstance(rekening, str):
            rekening = rekening.strip() or None
        return {
            "saldo": _to_float(_pick(
                data,
                "saldoOpDezeRekenstaat",
                "saldo",
                "bedrag",
                "balance",
                "amount",
                "huidigSaldo",
                "saldoRekenstaat",
            )),
            "rekening_nummer": rekening,
            "datum_laatste_update": _pick(data, "datumLaatsteUpdate", "laatsteUpdate"),
            "rekenstaat": _pick(data, "rekenstaat", "rekenstaatNummer", "nummer", "rekenstaatCode"),
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
        """Parse /parkbezoek-historiek.

        API returns a list of per-rekening groups:
          [{ rekening: {rekeningNummer}, historiekRecords: [row|group...] }, ...]
        """
        groups: list = []
        if isinstance(data, list):
            groups = data
        elif isinstance(data, dict):
            groups = [data]
        else:
            groups = []

        rekening_nummer = None
        flat: list[dict] = []

        for group in groups:
            if not isinstance(group, dict):
                continue
            rekening = group.get("rekening") if isinstance(group.get("rekening"), dict) else {}
            rn = rekening.get("rekeningNummer") or group.get("rekeningNummer")
            if isinstance(rn, str) and rn.strip():
                if rekening_nummer is None:
                    rekening_nummer = rn.strip()

            records = (
                group.get("historiekRecords")
                or group.get("historiek")
                or group.get("records")
                or group.get("items")
            )
            # If this dict itself looks like a visit row, keep it
            if records is None and any(
                k in group for k in ("datumParkbezoek", "activiteit", "hoeveelheid", "opgehaaldeKgs")
            ):
                records = [group]
            if records is None:
                continue
            if not isinstance(records, list):
                continue

            for entry in records:
                if isinstance(entry, list):
                    for row in entry:
                        if isinstance(row, dict):
                            flat.append(row)
                elif isinstance(entry, dict):
                    # nested historiekRecords inside type groups
                    nested = entry.get("historiekRecords")
                    if isinstance(nested, list) and not any(
                        k in entry for k in ("datumParkbezoek", "activiteit", "hoeveelheid")
                    ):
                        for row in nested:
                            if isinstance(row, dict):
                                flat.append(row)
                    else:
                        flat.append(entry)

        recente = []
        for item in flat:
            gewicht = _to_float(_pick(item, "opgehaaldeKgs", "gewicht", "gewichtKg", "hoeveelheid"))
            recente.append({
                "datum": _pick(item, "datumParkbezoek", "datum", "date", "datumIso"),
                "activiteit": _pick(item, "activiteit", "activity", "event", "rule", "fractie", "omschrijving"),
                "gewicht_kg": gewicht,
                "bedrag": _to_float(_pick(item, "bedrag", "amount", "totaalBedrag")),
                "kaart": _pick(item, "kaart"),
                "eenheid": _pick(item, "eenheid"),
                "event": _pick(item, "eventNummer", "event", "eventType"),
                "raw_keys": sorted(item.keys())[:20],
            })

        def sort_key(item: dict):
            raw = item.get("datum") or ""
            try:
                from datetime import datetime
                return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
            except Exception:
                return str(raw)

        recente_sorted = sorted(recente, key=sort_key, reverse=True)

        from datetime import datetime
        jaar = datetime.now().year
        kosten = 0.0
        for item in recente_sorted:
            raw = item.get("datum") or ""
            try:
                y = datetime.fromisoformat(str(raw).replace("Z", "+00:00")).year
            except Exception:
                try:
                    y = int(str(raw)[:4])
                except Exception:
                    y = None
            if y == jaar and item.get("bedrag") is not None:
                kosten += float(item["bedrag"])

        # Prefer a "header" row with datum for native_value
        laatste = None
        for item in recente_sorted:
            if item.get("datum") or item.get("gewicht_kg") is not None or item.get("bedrag") is not None:
                laatste = item
                break
        if laatste is None and recente_sorted:
            laatste = recente_sorted[0]

        return {
            "recente": recente_sorted[:12],
            "laatste": laatste,
            "kosten_dit_jaar": round(kosten, 2),
            "aantal": len(recente_sorted),
            "rekening_nummer": rekening_nummer,
            "groepen": len(groups),
        }


    def _parse_punten_saldo(self, data) -> float | None:
        if isinstance(data, (int, float)):
            return float(data)
        if not isinstance(data, dict):
            return None
        user = data.get("user") if isinstance(data.get("user"), dict) else data
        return _to_float(_pick(user, "saldo", "punten", "puntensaldo", "points", "balance"))
