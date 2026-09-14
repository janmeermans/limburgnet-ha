"""Config flow voor Limburg.net integratie."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import LimburgNetAPI, search_gemeenten, search_straten
from .const import (
    CONF_GEMEENTE_NAAM,
    CONF_HUISNUMMER,
    CONF_NIS_CODE,
    CONF_STRAAT_NAAM,
    CONF_STRAAT_NUMMER,
    CONF_TOEVOEGING,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STAP_GEBRUIKER = vol.Schema({
    vol.Required(CONF_EMAIL): str,
    vol.Required(CONF_PASSWORD): str,
})


def _calendar_dict(
    nis_code: str,
    straat_nummer: str,
    huisnummer: str,
    toevoeging: str,
    gemeente_naam: str,
    straat_naam: str,
) -> dict[str, str]:
    return {
        CONF_NIS_CODE: nis_code,
        CONF_STRAAT_NUMMER: straat_nummer,
        CONF_HUISNUMMER: str(huisnummer).strip(),
        CONF_TOEVOEGING: (toevoeging or "").strip(),
        CONF_GEMEENTE_NAAM: gemeente_naam,
        CONF_STRAAT_NAAM: straat_naam,
    }


class LimburgNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Setup wizard: login → gemeente → straat → huisnummer."""

    VERSION = 1

    def __init__(self) -> None:
        self._email: str | None = None
        self._password: str | None = None
        self._gemeente_choices: dict[str, str] = {}
        self._straat_choices: dict[str, str] = {}
        self._nis_code: str | None = None
        self._gemeente_naam: str | None = None
        self._straat_nummer: str | None = None
        self._straat_naam: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return LimburgNetOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Stap 1: e-mail en wachtwoord."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]

            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            api = LimburgNetAPI(email, password)
            try:
                await self.hass.async_add_executor_job(api.haal_alle_data_op)
            except Exception as err:
                _LOGGER.error("Login test mislukt: %s", err)
                errors["base"] = "invalid_auth"
            else:
                self._email = email
                self._password = password
                return await self.async_step_gemeente()

        return self.async_show_form(
            step_id="user",
            data_schema=STAP_GEBRUIKER,
            errors=errors,
        )

    async def async_step_gemeente(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Stap 2: zoek gemeente."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = (user_input.get("gemeente") or "").strip()
            try:
                results = await self.hass.async_add_executor_job(search_gemeenten, query)
            except Exception as err:
                _LOGGER.error("Gemeente-zoeken mislukt: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not results:
                    errors["base"] = "gemeente_not_found"
                elif len(results) == 1:
                    self._nis_code = results[0]["nisCode"]
                    self._gemeente_naam = results[0]["naam"]
                    return await self.async_step_straat()
                else:
                    self._gemeente_choices = {
                        r["nisCode"]: r["naam"] for r in results
                    }
                    return await self.async_step_gemeente_select()

        return self.async_show_form(
            step_id="gemeente",
            data_schema=vol.Schema({vol.Required("gemeente"): str}),
            errors=errors,
            description_placeholders={"hint": "bijv. Example"},
        )

    async def async_step_gemeente_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Kies gemeente uit zoekresultaten."""
        if user_input is not None:
            nis = user_input["nis_code"]
            self._nis_code = nis
            self._gemeente_naam = self._gemeente_choices.get(nis, nis)
            return await self.async_step_straat()

        return self.async_show_form(
            step_id="gemeente_select",
            data_schema=vol.Schema({
                vol.Required("nis_code"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in self._gemeente_choices.items()
                        ],
                        mode="dropdown",
                    )
                )
            }),
        )

    async def async_step_straat(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Stap 3: zoek straat."""
        errors: dict[str, str] = {}

        if user_input is not None:
            query = (user_input.get("straat") or "").strip()
            try:
                results = await self.hass.async_add_executor_job(
                    search_straten, self._nis_code, query
                )
            except Exception as err:
                _LOGGER.error("Straat-zoeken mislukt: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not results:
                    errors["base"] = "straat_not_found"
                elif len(results) == 1:
                    self._straat_nummer = results[0]["nummer"]
                    self._straat_naam = results[0]["naam"]
                    return await self.async_step_huisnummer()
                else:
                    self._straat_choices = {
                        r["nummer"]: r["naam"] for r in results
                    }
                    return await self.async_step_straat_select()

        return self.async_show_form(
            step_id="straat",
            data_schema=vol.Schema({vol.Required("straat"): str}),
            errors=errors,
            description_placeholders={
                "gemeente": self._gemeente_naam or "",
            },
        )

    async def async_step_straat_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Kies straat uit zoekresultaten."""
        if user_input is not None:
            nummer = user_input["straat_nummer"]
            self._straat_nummer = nummer
            self._straat_naam = self._straat_choices.get(nummer, nummer)
            return await self.async_step_huisnummer()

        return self.async_show_form(
            step_id="straat_select",
            data_schema=vol.Schema({
                vol.Required("straat_nummer"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in self._straat_choices.items()
                        ],
                        mode="dropdown",
                    )
                )
            }),
        )

    async def async_step_huisnummer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Stap 4: huisnummer (+ optionele toevoeging)."""
        errors: dict[str, str] = {}

        if user_input is not None:
            huisnummer = str(user_input.get(CONF_HUISNUMMER) or "").strip()
            if not huisnummer:
                errors["base"] = "huisnummer_required"
            else:
                toevoeging = str(user_input.get(CONF_TOEVOEGING) or "").strip()
                cal = _calendar_dict(
                    nis_code=self._nis_code or "",
                    straat_nummer=self._straat_nummer or "",
                    huisnummer=huisnummer,
                    toevoeging=toevoeging,
                    gemeente_naam=self._gemeente_naam or "",
                    straat_naam=self._straat_naam or "",
                )
                return self.async_create_entry(
                    title=f"Limburg.net ({self._email})",
                    data={
                        CONF_EMAIL: self._email,
                        CONF_PASSWORD: self._password,
                        **cal,
                    },
                )

        return self.async_show_form(
            step_id="huisnummer",
            data_schema=vol.Schema({
                vol.Required(CONF_HUISNUMMER): str,
                vol.Optional(CONF_TOEVOEGING, default=""): str,
            }),
            errors=errors,
            description_placeholders={
                "gemeente": self._gemeente_naam or "",
                "straat": self._straat_naam or "",
            },
        )


class LimburgNetOptionsFlow(config_entries.OptionsFlow):
    """Options flow: kalenderadres instellen/wijzigen voor bestaande entries."""

    def __init__(self) -> None:
        self._gemeente_choices: dict[str, str] = {}
        self._straat_choices: dict[str, str] = {}
        self._nis_code: str | None = None
        self._gemeente_naam: str | None = None
        self._straat_nummer: str | None = None
        self._straat_naam: str | None = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Start options: kalenderadres."""
        return await self.async_step_gemeente()

    async def async_step_gemeente(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            query = (user_input.get("gemeente") or "").strip()
            try:
                results = await self.hass.async_add_executor_job(search_gemeenten, query)
            except Exception as err:
                _LOGGER.error("Gemeente-zoeken mislukt: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not results:
                    errors["base"] = "gemeente_not_found"
                elif len(results) == 1:
                    self._nis_code = results[0]["nisCode"]
                    self._gemeente_naam = results[0]["naam"]
                    return await self.async_step_straat()
                else:
                    self._gemeente_choices = {
                        r["nisCode"]: r["naam"] for r in results
                    }
                    return await self.async_step_gemeente_select()

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }
        default = current.get(CONF_GEMEENTE_NAAM) or ""
        return self.async_show_form(
            step_id="gemeente",
            data_schema=vol.Schema({
                vol.Required("gemeente", default=default): str,
            }),
            errors=errors,
        )

    async def async_step_gemeente_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            nis = user_input["nis_code"]
            self._nis_code = nis
            self._gemeente_naam = self._gemeente_choices.get(nis, nis)
            return await self.async_step_straat()

        return self.async_show_form(
            step_id="gemeente_select",
            data_schema=vol.Schema({
                vol.Required("nis_code"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in self._gemeente_choices.items()
                        ],
                        mode="dropdown",
                    )
                )
            }),
        )

    async def async_step_straat(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            query = (user_input.get("straat") or "").strip()
            try:
                results = await self.hass.async_add_executor_job(
                    search_straten, self._nis_code, query
                )
            except Exception as err:
                _LOGGER.error("Straat-zoeken mislukt: %s", err)
                errors["base"] = "cannot_connect"
            else:
                if not results:
                    errors["base"] = "straat_not_found"
                elif len(results) == 1:
                    self._straat_nummer = results[0]["nummer"]
                    self._straat_naam = results[0]["naam"]
                    return await self.async_step_huisnummer()
                else:
                    self._straat_choices = {
                        r["nummer"]: r["naam"] for r in results
                    }
                    return await self.async_step_straat_select()

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }
        default = current.get(CONF_STRAAT_NAAM) or ""
        return self.async_show_form(
            step_id="straat",
            data_schema=vol.Schema({
                vol.Required("straat", default=default): str,
            }),
            errors=errors,
            description_placeholders={"gemeente": self._gemeente_naam or ""},
        )

    async def async_step_straat_select(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            nummer = user_input["straat_nummer"]
            self._straat_nummer = nummer
            self._straat_naam = self._straat_choices.get(nummer, nummer)
            return await self.async_step_huisnummer()

        return self.async_show_form(
            step_id="straat_select",
            data_schema=vol.Schema({
                vol.Required("straat_nummer"): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"value": k, "label": v}
                            for k, v in self._straat_choices.items()
                        ],
                        mode="dropdown",
                    )
                )
            }),
        )

    async def async_step_huisnummer(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}
        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        if user_input is not None:
            huisnummer = str(user_input.get(CONF_HUISNUMMER) or "").strip()
            if not huisnummer:
                errors["base"] = "huisnummer_required"
            else:
                toevoeging = str(user_input.get(CONF_TOEVOEGING) or "").strip()
                return self.async_create_entry(
                    title="",
                    data=_calendar_dict(
                        nis_code=self._nis_code or "",
                        straat_nummer=self._straat_nummer or "",
                        huisnummer=huisnummer,
                        toevoeging=toevoeging,
                        gemeente_naam=self._gemeente_naam or "",
                        straat_naam=self._straat_naam or "",
                    ),
                )

        return self.async_show_form(
            step_id="huisnummer",
            data_schema=vol.Schema({
                vol.Required(
                    CONF_HUISNUMMER,
                    default=str(current.get(CONF_HUISNUMMER) or ""),
                ): str,
                vol.Optional(
                    CONF_TOEVOEGING,
                    default=str(current.get(CONF_TOEVOEGING) or ""),
                ): str,
            }),
            errors=errors,
            description_placeholders={
                "gemeente": self._gemeente_naam or "",
                "straat": self._straat_naam or "",
            },
        )
