"""Config flow for OpnSense integration."""

import logging
from urllib.parse import urlparse

from homeassistant import config_entries
from homeassistant.const import (
    CONF_NAME,
    CONF_PASSWORD,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
import voluptuous as vol

from .const import DEFAULT_USERNAME, DEFAULT_VERIFY_SSL, DOMAIN
from ..pfsense.pypfsense_opnsense import probe_opnsense

_LOGGER = logging.getLogger(__name__)


class ConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpnSense."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            # Basic URL validation
            url = user_input[CONF_URL].strip()
            url_parts = urlparse(url)
            if not url_parts.scheme or not url_parts.netloc:
                errors["base"] = "invalid_url_format"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_user_schema(),
                    errors=errors,
                )

            url = f"{url_parts.scheme}://{url_parts.netloc}"
            username = user_input.get(CONF_USERNAME, DEFAULT_USERNAME)
            password = user_input.get(CONF_PASSWORD)
            verify_ssl = user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

            # Probe the OpnSense API to validate connectivity and credentials
            try:
                system_info = await probe_opnsense(
                    url, username, password, verify_ssl=verify_ssl
                )
            except Exception as err:  # network/auth/ssl/timeouts
                _LOGGER.debug("OpnSense probe failed: %s", err)
                errors["base"] = "cannot_connect"
                return self.async_show_form(
                    step_id="user",
                    data_schema=self._get_user_schema(),
                    errors=errors,
                )

            # Use a device identifier if the probe returned one, otherwise fall back
            unique_id = None
            try:
                unique_id = system_info.get("device", {}).get("id")
            except Exception:
                unique_id = None

            if unique_id:
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

            title = user_input.get(CONF_NAME) or system_info.get("hostname") or url

            return self.async_create_entry(
                title=title,
                data={
                    CONF_URL: url,
                    CONF_USERNAME: username,
                    CONF_PASSWORD: password,
                    CONF_VERIFY_SSL: verify_ssl,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_user_schema(),
        )

    @staticmethod
    def _get_user_schema():
        return vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
                vol.Optional(CONF_NAME): str,
            }
        )
