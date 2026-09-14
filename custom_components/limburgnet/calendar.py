"""Calendar platform voor Limburg.net ophalingkalender."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_GEMEENTE_NAAM,
    CONF_HUISNUMMER,
    CONF_STRAAT_NAAM,
    DOMAIN,
)
from .coordinator import LimburgNetCoordinator, calendar_config_from_entry

DEVICE_INFO = {
    "identifiers": {(DOMAIN, "limburgnet")},
    "name": "Limburg.net Afvalophaling",
    "manufacturer": "Limburg.net",
    "model": "Huis-aan-huis & Containerpark",
    "entry_type": "service",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: LimburgNetCoordinator = hass.data[DOMAIN][entry.entry_id]
    if not calendar_config_from_entry(entry):
        return
    async_add_entities([LimburgNetCalendar(coordinator, entry)])


class LimburgNetCalendar(CoordinatorEntity, CalendarEntity):
    """Kalenderentiteit met aankomende ophalingen."""

    _attr_icon = "mdi:calendar-month"
    _attr_has_entity_name = False

    def __init__(
        self, coordinator: LimburgNetCoordinator, entry: ConfigEntry
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"limburgnet_kalender_{entry.entry_id}"
        merged = {**entry.data, **entry.options}
        gemeente = merged.get(CONF_GEMEENTE_NAAM) or ""
        straat = merged.get(CONF_STRAAT_NAAM) or ""
        huis = merged.get(CONF_HUISNUMMER) or ""
        suffix = f"{straat} {huis}".strip()
        if gemeente and suffix:
            name = f"Limburg.net Ophalingen ({gemeente})"
        else:
            name = "Limburg.net Ophalingen"
        self._attr_name = name

    @property
    def device_info(self) -> dict:
        return DEVICE_INFO

    def _events(self) -> list[dict[str, Any]]:
        data = self.coordinator.data or {}
        kalender = data.get("kalender") or {}
        return list(kalender.get("events") or [])

    @property
    def event(self) -> CalendarEvent | None:
        """Volgende ophaling."""
        data = self.coordinator.data or {}
        kalender = data.get("kalender") or {}
        nxt = kalender.get("next_overall")
        if not nxt:
            return None
        return self._to_calendar_event(nxt)

    async def async_get_events(
        self,
        hass: HomeAssistant,
        start_date: datetime,
        end_date: datetime,
    ) -> list[CalendarEvent]:
        start_d = start_date.date() if isinstance(start_date, datetime) else start_date
        end_d = end_date.date() if isinstance(end_date, datetime) else end_date
        result: list[CalendarEvent] = []
        for item in self._events():
            try:
                d = date.fromisoformat(item["date"])
            except (KeyError, ValueError, TypeError):
                continue
            if start_d <= d < end_d:
                result.append(self._to_calendar_event(item))
        return result

    @staticmethod
    def _to_calendar_event(item: dict[str, Any]) -> CalendarEvent:
        d = date.fromisoformat(item["date"])
        summary = item.get("fractie") or item.get("title") or "Ophaling"
        description_parts = []
        if item.get("type"):
            description_parts.append(str(item["type"]))
        if item.get("detail_url"):
            description_parts.append(str(item["detail_url"]))
        return CalendarEvent(
            summary=summary,
            start=d,
            end=d + timedelta(days=1),
            description=" — ".join(description_parts) if description_parts else None,
            uid=f"{item.get('fractie_slug', 'x')}-{item['date']}",
        )
