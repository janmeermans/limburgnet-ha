"""Config flow voor Limburg.net integratie."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.data_entry_flow import FlowResult

from .api import LimburgNetAPI
from .const import CONF_LOCATIE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STAP_GEBRUIKER = vol.Schema({
    vol.Required(CONF_EMAIL):    str,
    vol.Required(CONF_PASSWORD): str,
    vol.Optional(CONF_LOCATIE, default=""): str,
})


class LimburgNetConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Setup wizard voor Limburg.net."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Stap 1: gebruiker vult email, wachtwoord en locatie-cookie in."""
        errors: dict[str, str] = {}

        if user_input is not None:
            email    = user_input[CONF_EMAIL]
            password = user_input[CONF_PASSWORD]
            locatie  = user_input.get(CONF_LOCATIE, "")

            # Unieke entry per e-mailadres
            await self.async_set_unique_id(email.lower())
            self._abort_if_unique_id_configured()

            # Test de inloggegevens
            api = LimburgNetAPI(email, password, locatie)
            try:
                await self.hass.async_add_executor_job(api.haal_ledigingen_op)
            except Exception as err:
                _LOGGER.error("Login test mislukt: %s", err)
                errors["base"] = "invalid_auth"
            else:
                return self.async_create_entry(
                    title=f"Limburg.net ({email})",
                    data={
                        CONF_EMAIL:    email,
                        CONF_PASSWORD: password,
                        CONF_LOCATIE:  locatie,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STAP_GEBRUIKER,
            errors=errors,
            description_placeholders={
                "locatie_help": (
                    "Optioneel: kopieer de 'locatie' cookie uit je browser "
                    "(DevTools → Application → Cookies → limburg.net)"
                )
            },
        )
