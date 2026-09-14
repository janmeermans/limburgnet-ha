"""Sensor platform voor Limburg.net afvalophaling."""
from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CURRENCY_EURO, UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FRACTIES, FRACTIE_NAMEN
from .coordinator import LimburgNetCoordinator

DEVICE_INFO = {
    "identifiers": {(DOMAIN, "limburgnet")},
    "name": "Limburg.net Afvalophaling",
    "manufacturer": "Limburg.net",
    "model": "Huis-aan-huis & Containerpark",
    "entry_type": "service",
}

MAX_RECENTE_LEDIGINGEN = 12


def _historie(leging: dict | None) -> list[dict]:
    if not leging:
        return []
    return list(leging.get("historie") or [])


def _jaar_van_iso(datum_iso: str | None) -> int | None:
    if not datum_iso:
        return None
    try:
        return datetime.fromisoformat(datum_iso.replace("Z", "+00:00")).year
    except (ValueError, AttributeError, TypeError):
        return None


def kosten_dit_jaar(historie: list[dict], jaar: int | None = None) -> float:
    if jaar is None:
        jaar = datetime.now().year
    totaal = 0.0
    for item in historie:
        if _jaar_van_iso(item.get("datum_iso")) == jaar:
            try:
                totaal += float(item.get("betaald_bedrag") or 0)
            except (TypeError, ValueError):
                continue
    return round(totaal, 2)


def recente_ledigingen(historie: list[dict], limiet: int = MAX_RECENTE_LEDIGINGEN) -> list[dict]:
    resultaat = []
    for item in historie[:limiet]:
        resultaat.append({
            "datum_iso": item.get("datum_iso"),
            "gewicht_kg": item.get("gewicht_kg"),
            "betaald_bedrag": item.get("betaald_bedrag"),
        })
    return resultaat


def _rekenstaat(data: dict | None) -> dict:
    if not data:
        return {}
    return data.get("rekenstaat") or {}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LimburgNetCoordinator = hass.data[DOMAIN][entry.entry_id]
    entiteiten: list[SensorEntity] = []

    for fractie in FRACTIES:
        entiteiten.append(LimburgNetLedingSensor(coordinator, fractie))
        entiteiten.append(LimburgNetKostenJaarSensor(coordinator, fractie))

    entiteiten.append(LimburgNetKostenJaarTotaalSensor(coordinator))

    # Rekenstaat / afvalbelasting
    entiteiten.extend([
        LimburgNetOpenstaandSensor(coordinator),
        LimburgNetHuidigSaldoSensor(coordinator),
        LimburgNetDirecteInningSensor(coordinator),
        LimburgNetAanslagbiljettenSensor(coordinator),
        LimburgNetKohierSensor(coordinator),
        LimburgNetParkbezoekLaatsteSensor(coordinator),
        LimburgNetParkbezoekKostenJaarSensor(coordinator),
        LimburgNetSlimmeSorteerpuntenSaldoSensor(coordinator),
        LimburgNetOphalingOverzichtSensor(coordinator),
    ])

    data = coordinator.data or {}
    quota_lijst = data.get("quota") or []
    for quota in quota_lijst:
        entiteiten.append(LimburgNetQuotaSensor(coordinator, quota["fractie"]))

    async_add_entities(entiteiten, update_before_add=True)

    if not quota_lijst:
        import logging
        logging.getLogger(__name__).warning(
            "Geen containerpark quota gevonden in data. "
            "Controleer of de API bereikbaar is: /api-proxy/recyclagepark/quotum/fracties"
        )


class LimburgNetLedingSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon = "mdi:trash-can-outline"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie: str) -> None:
        super().__init__(coordinator)
        self._fractie = fractie
        self._attr_unique_id = f"limburgnet_leiding_{fractie}"
        self._attr_name = f"Limburg.net {FRACTIE_NAMEN.get(fractie, fractie)}"

    def _leging(self) -> dict | None:
        data = self.coordinator.data
        if not data:
            return None
        return (data.get("ledigingen") or {}).get(self._fractie)

    @property
    def native_value(self) -> float | None:
        leging = self._leging()
        return leging["gewicht_kg"] if leging else None

    @property
    def extra_state_attributes(self) -> dict:
        leging = self._leging()
        if not leging:
            return {}
        historie = _historie(leging)
        return {
            "datum": leging.get("datum"),
            "datum_iso": leging.get("datum_iso"),
            "betaald_bedrag": leging.get("betaald_bedrag"),
            "prijs_per_kg": leging.get("prijs_per_kg"),
            "fractie": self._fractie,
            "kosten_dit_jaar": kosten_dit_jaar(historie),
            "recente_ledigingen": recente_ledigingen(historie),
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetKostenJaarSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:cash"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie: str) -> None:
        super().__init__(coordinator)
        self._fractie = fractie
        self._attr_unique_id = f"limburgnet_kosten_jaar_{fractie}"
        self._attr_name = f"Limburg.net Kosten jaar {FRACTIE_NAMEN.get(fractie, fractie)}"

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        leging = (data.get("ledigingen") or {}).get(self._fractie)
        if not leging:
            return None
        return kosten_dit_jaar(_historie(leging))

    @property
    def extra_state_attributes(self) -> dict:
        return {"fractie": self._fractie, "jaar": datetime.now().year}

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetKostenJaarTotaalSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:cash-multiple"
    _attr_unique_id = "limburgnet_kosten_jaar_totaal"
    _attr_name = "Limburg.net Kosten jaar totaal"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data
        if not data:
            return None
        ledigingen = data.get("ledigingen") or {}
        if not any(ledigingen.get(f) for f in FRACTIES):
            return None
        totaal = sum(kosten_dit_jaar(_historie(ledigingen.get(f))) for f in FRACTIES)
        return round(totaal, 2)

    @property
    def extra_state_attributes(self) -> dict:
        return {"jaar": datetime.now().year}

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetQuotaSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:recycle"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie_naam: str) -> None:
        super().__init__(coordinator)
        self._fractie_naam = fractie_naam
        safe_naam = fractie_naam.lower().replace(" ", "_").replace(",", "").replace(".", "")
        self._attr_unique_id = f"limburgnet_quota_{safe_naam}"
        self._attr_name = f"Limburg.net Quota {fractie_naam}"

    def _quota_item(self) -> dict | None:
        data = self.coordinator.data
        if not data:
            return None
        for item in (data.get("quota") or []):
            if item.get("fractie") == self._fractie_naam:
                return item
        return None

    @property
    def native_value(self) -> float | None:
        item = self._quota_item()
        return item["resterend_aantal"] if item else None

    @property
    def native_unit_of_measurement(self) -> str:
        item = self._quota_item()
        if item:
            eenheid = item.get("eenheid", "Kg")
            return eenheid.lower() if eenheid.lower() == "kg" else eenheid
        return "kg"

    @property
    def extra_state_attributes(self) -> dict:
        item = self._quota_item()
        if not item:
            return {}
        return {
            "totaal_quota": item.get("totaal_aantal"),
            "gebruikt": round((item.get("totaal_aantal") or 0) - (item.get("resterend_aantal") or 0), 2),
            "eenheid": item.get("eenheid"),
            "tarief_bedrag": item.get("tarief_bedrag"),
            "quotum_nummer": item.get("quotum_nummer"),
            "fractie": self._fractie_naam,
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetOpenstaandSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:file-document-outline"
    _attr_unique_id = "limburgnet_openstaand"
    _attr_name = "Limburg.net Openstaand bedrag"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        openstaand = _rekenstaat(self.coordinator.data).get("openstaand") or {}
        return openstaand.get("totaal_bedrag")

    @property
    def extra_state_attributes(self) -> dict:
        openstaand = _rekenstaat(self.coordinator.data).get("openstaand") or {}
        bewegingen = _rekenstaat(self.coordinator.data).get("bewegingen") or []
        timeline = _rekenstaat(self.coordinator.data).get("timeline") or []
        per_jaar = _rekenstaat(self.coordinator.data).get("bewegingen_per_jaar")
        return {
            "datum_laatste_update": openstaand.get("datum_laatste_update"),
            "rekening_nummer": openstaand.get("rekening_nummer"),
            "recente_bewegingen": bewegingen[:12],
            "timeline": timeline[:12],
            "bewegingen_per_jaar": per_jaar,
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetHuidigSaldoSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:wallet-outline"
    _attr_unique_id = "limburgnet_huidig_saldo"
    _attr_name = "Limburg.net Huidig saldo"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        saldo = _rekenstaat(self.coordinator.data).get("huidig_saldo") or {}
        return saldo.get("saldo")

    @property
    def extra_state_attributes(self) -> dict:
        saldo = _rekenstaat(self.coordinator.data).get("huidig_saldo") or {}
        return {
            "rekening_nummer": saldo.get("rekening_nummer"),
            "datum_laatste_update": saldo.get("datum_laatste_update"),
            "minimum_saldo": saldo.get("minimum_saldo"),
            "saldo_lijst": saldo.get("saldo_lijst") or [],
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetDirecteInningSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:bank-transfer"
    _attr_unique_id = "limburgnet_saldo_directe_inning"
    _attr_name = "Limburg.net Saldo directe inning"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        item = _rekenstaat(self.coordinator.data).get("directe_inning") or {}
        return item.get("saldo")

    @property
    def extra_state_attributes(self) -> dict:
        item = _rekenstaat(self.coordinator.data).get("directe_inning") or {}
        return {
            "rekening_nummer": item.get("rekening_nummer"),
            "rekenstaat": item.get("rekenstaat"),
            "datum_laatste_update": item.get("datum_laatste_update"),
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetAanslagbiljettenSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:file-cabinet"
    _attr_unique_id = "limburgnet_aanslagbiljetten"
    _attr_name = "Limburg.net Aanslagbiljetten"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    def _data(self) -> dict:
        return _rekenstaat(self.coordinator.data).get("aanslagbiljetten") or {}

    @property
    def native_value(self) -> int | None:
        data = self._data()
        if not data:
            return None
        return data.get("aantal")

    @property
    def extra_state_attributes(self) -> dict:
        data = self._data()
        if not data:
            return {}
        detail = data.get("detail") or {}
        recente = data.get("recente") or []
        laatste_bedrag = None
        if recente and isinstance(recente[0], dict):
            laatste_bedrag = recente[0].get("amount")
        elif detail:
            laatste_bedrag = detail.get("amount")
        return {
            "betaald": data.get("betaald"),
            "onvolledig": data.get("onvolledig"),
            "overgedragen": data.get("overgedragen"),
            "recente": recente,
            "laatste_bedrag": laatste_bedrag,
            "payment_reference": detail.get("payment_reference"),
            "detail_id": detail.get("id"),
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetKohierSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:receipt-text-outline"
    _attr_unique_id = "limburgnet_kohier_huidig_jaar"
    _attr_name = "Limburg.net Kohier huidig jaar"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    def _items(self) -> list:
        return _rekenstaat(self.coordinator.data).get("kohier") or []

    @property
    def native_value(self) -> float | None:
        items = self._items()
        if not items:
            return None
        jaar = datetime.now().year
        totaal = 0.0
        matched = False
        for item in items:
            y = item.get("year")
            try:
                y_int = int(y) if y is not None else None
            except (TypeError, ValueError):
                y_int = None
            if y_int == jaar and item.get("amount") is not None:
                totaal += float(item["amount"])
                matched = True
        if matched:
            return round(totaal, 2)
        # fallback: som van alle of eerste
        amounts = [float(i["amount"]) for i in items if i.get("amount") is not None]
        return round(sum(amounts), 2) if amounts else None

    @property
    def extra_state_attributes(self) -> dict:
        return {"artikelen": self._items()[:15], "jaar": datetime.now().year}

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetParkbezoekLaatsteSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.WEIGHT
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon = "mdi:forest"
    _attr_unique_id = "limburgnet_parkbezoek_laatste"
    _attr_name = "Limburg.net Parkbezoek laatste gewicht"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    def _park(self) -> dict:
        data = self.coordinator.data or {}
        return data.get("parkbezoeken") or {}

    @property
    def native_value(self) -> float | None:
        laatste = self._park().get("laatste") or {}
        return laatste.get("gewicht_kg")

    @property
    def extra_state_attributes(self) -> dict:
        park = self._park()
        laatste = park.get("laatste") or {}
        return {
            "datum": laatste.get("datum"),
            "activiteit": laatste.get("activiteit"),
            "bedrag": laatste.get("bedrag"),
            "kaart": laatste.get("kaart"),
            "event": laatste.get("event"),
            "rekening_nummer": park.get("rekening_nummer"),
            "recente_bezoeken": park.get("recente") or [],
            "aantal": park.get("aantal"),
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetParkbezoekKostenJaarSensor(CoordinatorEntity, SensorEntity):
    _attr_device_class = SensorDeviceClass.MONETARY
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = CURRENCY_EURO
    _attr_icon = "mdi:cash"
    _attr_unique_id = "limburgnet_parkbezoek_kosten_jaar"
    _attr_name = "Limburg.net Parkbezoek kosten jaar"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> float | None:
        data = self.coordinator.data or {}
        park = data.get("parkbezoeken")
        if not park:
            return None
        return park.get("kosten_dit_jaar")

    @property
    def extra_state_attributes(self) -> dict:
        return {"jaar": datetime.now().year}

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetSlimmeSorteerpuntenSaldoSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:star-circle-outline"
    _attr_unique_id = "limburgnet_slimme_sorteerpunten_saldo"
    _attr_name = "Limburg.net Slimmesorteerpunten saldo"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    def _punten(self) -> dict:
        data = self.coordinator.data or {}
        return data.get("slimme_sorteerpunten") or {}

    @property
    def native_value(self) -> float | None:
        return self._punten().get("saldo")

    @property
    def extra_state_attributes(self) -> dict:
        punten = self._punten()
        historiek = punten.get("historiek") or []
        acties = punten.get("acties") or []
        # Compact hold size for HA state machine
        return {
            "historiek": historiek[:20] if isinstance(historiek, list) else historiek,
            "acties": acties[:20] if isinstance(acties, list) else acties,
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


class LimburgNetOphalingOverzichtSensor(CoordinatorEntity, SensorEntity):
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:calendar-month-outline"
    _attr_unique_id = "limburgnet_ophaling_overzicht"
    _attr_name = "Limburg.net Ophaling overzicht"

    def __init__(self, coordinator: LimburgNetCoordinator) -> None:
        super().__init__(coordinator)

    @property
    def native_value(self) -> int | None:
        data = self.coordinator.data or {}
        overzicht = data.get("ophaling_overzicht")
        if overzicht is None:
            return None
        if isinstance(overzicht, list):
            return len(overzicht)
        if isinstance(overzicht, dict):
            return 1
        return None

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        overzicht = data.get("ophaling_overzicht")
        if overzicht is None:
            return {}
        return {"items": overzicht if isinstance(overzicht, (list, dict)) else str(overzicht)}

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO
