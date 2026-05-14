"""Sensor platform voor Limburg.net afvalophaling."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfMass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, FRACTIES, FRACTIE_NAMEN
from .coordinator import LimburgNetCoordinator

DEVICE_INFO = {
    "identifiers":  {(DOMAIN, "limburgnet")},
    "name":         "Limburg.net Afvalophaling",
    "manufacturer": "Limburg.net",
    "model":        "Huis-aan-huis & Containerpark",
    "entry_type":   "service",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Maak alle sensor entiteiten aan."""
    coordinator: LimburgNetCoordinator = hass.data[DOMAIN][entry.entry_id]

    entiteiten = []

    # Huis-aan-huis sensoren
    for fractie in FRACTIES:
        entiteiten.append(LimburgNetLedingSensor(coordinator, fractie))

    # Containerpark quota sensoren — één per fractie in de quota lijst
    data = coordinator.data or {}
    for quota in (data.get("quota") or []):
        entiteiten.append(LimburgNetQuotaSensor(coordinator, quota["fractie"]))

    async_add_entities(entiteiten)


# ── HUIS-AAN-HUIS SENSOR ─────────────────────────────────────────────────────

class LimburgNetLedingSensor(CoordinatorEntity, SensorEntity):
    """Sensor voor één huis-aan-huis afvalfractie."""

    _attr_device_class               = SensorDeviceClass.WEIGHT
    _attr_state_class                = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfMass.KILOGRAMS
    _attr_icon                       = "mdi:trash-can-outline"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie: str) -> None:
        super().__init__(coordinator)
        self._fractie        = fractie
        self._attr_unique_id = f"limburgnet_leiding_{fractie}"
        self._attr_name      = f"Limburg.net {FRACTIE_NAMEN.get(fractie, fractie)}"

    @property
    def native_value(self) -> float | None:
        """Gewicht van de laatste ophaling in kg."""
        data = self.coordinator.data
        if not data:
            return None
        leging = (data.get("ledigingen") or {}).get(self._fractie)
        return leging["gewicht_kg"] if leging else None

    @property
    def extra_state_attributes(self) -> dict:
        """Extra attributen."""
        data = self.coordinator.data
        if not data:
            return {}
        leging = (data.get("ledigingen") or {}).get(self._fractie)
        if not leging:
            return {}
        return {
            "datum":          leging.get("datum"),
            "datum_iso":      leging.get("datum_iso"),
            "betaald_bedrag": leging.get("betaald_bedrag"),
            "prijs_per_kg":   leging.get("prijs_per_kg"),
            "fractie":        self._fractie,
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO


# ── CONTAINERPARK QUOTA SENSOR ───────────────────────────────────────────────

class LimburgNetQuotaSensor(CoordinatorEntity, SensorEntity):
    """Sensor voor het resterend quota van één containerpark fractie."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon        = "mdi:recycle"

    def __init__(self, coordinator: LimburgNetCoordinator, fractie_naam: str) -> None:
        super().__init__(coordinator)
        self._fractie_naam   = fractie_naam
        # Maak een veilige entity ID van de fractienaam
        safe_naam            = fractie_naam.lower().replace(" ", "_").replace(",", "").replace(".", "")
        self._attr_unique_id = f"limburgnet_quota_{safe_naam}"
        self._attr_name      = f"Limburg.net Quota {fractie_naam}"

    def _quota_item(self) -> dict | None:
        """Zoek het quota item voor deze fractie."""
        data = self.coordinator.data
        if not data:
            return None
        for item in (data.get("quota") or []):
            if item.get("fractie") == self._fractie_naam:
                return item
        return None

    @property
    def native_value(self) -> float | None:
        """Resterend quota — de hoofdwaarde van de sensor."""
        item = self._quota_item()
        return item["resterend_aantal"] if item else None

    @property
    def native_unit_of_measurement(self) -> str:
        """Eenheid dynamisch bepalen op basis van API data (Kg, stuks, ...)."""
        item = self._quota_item()
        if item:
            eenheid = item.get("eenheid", "Kg")
            # HA begrijpt "kg" maar niet "Kg" — normaliseer
            return eenheid.lower() if eenheid.lower() == "kg" else eenheid
        return "kg"

    @property
    def extra_state_attributes(self) -> dict:
        """Alle quota details als attributen."""
        item = self._quota_item()
        if not item:
            return {}
        return {
            "totaal_quota":   item.get("totaal_aantal"),
            "gebruikt":       round(
                (item.get("totaal_aantal") or 0) - (item.get("resterend_aantal") or 0), 2
            ),
            "eenheid":        item.get("eenheid"),
            "tarief_bedrag":  item.get("tarief_bedrag"),
            "quotum_nummer":  item.get("quotum_nummer"),
            "fractie":        self._fractie_naam,
        }

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO
