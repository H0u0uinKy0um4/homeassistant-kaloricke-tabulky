"""Regression tests for household account ownership and service targeting."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
import unittest


COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "kaloricke_tabulky"


def _load_modules():
    """Load __init__.py and button.py with minimal Home Assistant stubs."""
    vol = types.ModuleType("voluptuous")

    class Marker:
        def __init__(self, *args, **kwargs):  # noqa: D107
            pass

    class Schema:
        def __init__(self, schema):  # noqa: D107
            self.schema = schema

    vol.Schema = Schema
    vol.Optional = Marker
    vol.Required = Marker
    vol.Coerce = Marker
    vol.In = Marker
    vol.All = Marker
    vol.Range = Marker
    vol.Invalid = type("Invalid", (Exception,), {})

    config_entries = types.ModuleType("homeassistant.config_entries")

    class ConfigEntryState:
        LOADED = "loaded"

    config_entries.ConfigEntry = object
    config_entries.ConfigEntryState = ConfigEntryState

    ha_const = types.ModuleType("homeassistant.const")
    ha_const.CONF_EMAIL = "email"
    ha_const.CONF_PASSWORD = "password"

    class Platform:
        SENSOR = "sensor"
        BUTTON = "button"

    ha_const.Platform = Platform

    core = types.ModuleType("homeassistant.core")
    core.HomeAssistant = object
    core.ServiceCall = object
    core.ServiceResponse = object
    core.SupportsResponse = type(
        "SupportsResponse", (), {"ONLY": "only", "OPTIONAL": "optional"}
    )

    class HaError(Exception):
        def __init__(self, *args, **kwargs):  # noqa: D107
            super().__init__(*args)

    exceptions = types.ModuleType("homeassistant.exceptions")
    exceptions.HomeAssistantError = type("HomeAssistantError", (HaError,), {})
    exceptions.Unauthorized = type("Unauthorized", (HaError,), {})
    exceptions.UnknownUser = type("UnknownUser", (HaError,), {})

    config_validation = types.ModuleType("homeassistant.helpers.config_validation")
    config_validation.string = lambda value: value

    dt_util = types.ModuleType("homeassistant.util.dt")
    dt_util.now = lambda: None
    util = types.ModuleType("homeassistant.util")
    util.dt = dt_util

    button_component = types.ModuleType("homeassistant.components.button")
    button_component.ButtonEntity = object
    device_registry = types.ModuleType("homeassistant.helpers.device_registry")
    device_registry.DeviceInfo = dict
    entity_platform = types.ModuleType("homeassistant.helpers.entity_platform")
    entity_platform.AddEntitiesCallback = object
    update_coordinator = types.ModuleType("homeassistant.helpers.update_coordinator")

    class CoordinatorEntity:
        def __init__(self, coordinator):  # noqa: D107
            self.coordinator = coordinator

        def __class_getitem__(cls, item):  # noqa: D105
            return cls

    update_coordinator.CoordinatorEntity = CoordinatorEntity

    custom_components = types.ModuleType("custom_components")
    custom_components.__path__ = [str(COMPONENT.parent)]
    package = types.ModuleType("custom_components.kaloricke_tabulky")
    package.__path__ = [str(COMPONENT)]

    api = types.ModuleType("custom_components.kaloricke_tabulky.api")
    api.KalorickeTabulkyApi = object
    api.KalorickeTabulkyError = type("KalorickeTabulkyError", (Exception,), {})
    api.parse_service_date = lambda value: value
    api.parse_service_time = lambda value: value

    const = types.ModuleType("custom_components.kaloricke_tabulky.const")
    const.DOMAIN = "kaloricke_tabulky"
    const.CONF_ACCOUNT_LABEL = "account_label"
    const.CONF_OWNER_USER_ID = "owner_user_id"
    const.CONF_QUICK_FOODS = "quick_foods"
    const.CONF_SCAN_INTERVAL = "scan_interval"
    const.DEFAULT_SCAN_INTERVAL = 240
    const.MIN_SCAN_INTERVAL = 15
    const.ATTR_ACCOUNT = "account"
    const.ATTR_CONFIG_ENTRY_ID = "config_entry_id"
    const.ATTR_WEIGHT = "weight"
    const.ATTR_DATE = "date"
    const.ATTR_QUERY = "query"
    const.ATTR_KIND = "kind"
    const.ATTR_PAGE = "page"
    const.ATTR_FOOD_GUID = "food_guid"
    const.ATTR_AMOUNT = "amount"
    const.ATTR_UNIT = "unit"
    const.ATTR_UNIT_GUID = "unit_guid"
    const.ATTR_TIME = "time"
    const.ATTR_MEAL_TYPE = "meal_type"
    const.SERVICE_RECORD_WEIGHT = "record_weight"
    const.SERVICE_SEARCH_FOOD = "search_food"
    const.SERVICE_RECORD_FOOD = "record_food"
    const.SERVICE_GET_SUMMARY = "get_summary"

    coordinator = types.ModuleType("custom_components.kaloricke_tabulky.coordinator")
    coordinator.KalorickeTabulkyCoordinator = object
    session = types.ModuleType("custom_components.kaloricke_tabulky.session")
    session.async_create_kt_session = lambda hass: None

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.__path__ = []
    helpers = types.ModuleType("homeassistant.helpers")
    helpers.__path__ = []
    components = types.ModuleType("homeassistant.components")
    components.__path__ = []

    stubs = {
        "voluptuous": vol,
        "homeassistant": homeassistant,
        "homeassistant.helpers": helpers,
        "homeassistant.components": components,
        "homeassistant.config_entries": config_entries,
        "homeassistant.const": ha_const,
        "homeassistant.core": core,
        "homeassistant.exceptions": exceptions,
        "homeassistant.helpers.config_validation": config_validation,
        "homeassistant.util": util,
        "homeassistant.util.dt": dt_util,
        "homeassistant.components.button": button_component,
        "homeassistant.helpers.device_registry": device_registry,
        "homeassistant.helpers.entity_platform": entity_platform,
        "homeassistant.helpers.update_coordinator": update_coordinator,
        "custom_components": custom_components,
        "custom_components.kaloricke_tabulky": package,
        "custom_components.kaloricke_tabulky.api": api,
        "custom_components.kaloricke_tabulky.const": const,
        "custom_components.kaloricke_tabulky.coordinator": coordinator,
        "custom_components.kaloricke_tabulky.session": session,
    }
    old_modules = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)

    def _load(name: str, path: Path):
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    try:
        integration = _load("custom_components.kaloricke_tabulky", COMPONENT / "__init__.py")
        button = _load("custom_components.kaloricke_tabulky.button", COMPONENT / "button.py")
        return integration, button, exceptions, ConfigEntryState
    finally:
        for name, previous in old_modules.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous


def _entry(entry_id: str, label: str, owner: str | None = None):
    """Build a minimal config entry with a coordinator."""
    return types.SimpleNamespace(
        entry_id=entry_id,
        title=label,
        data={"account_label": label},
        options={"owner_user_id": owner},
        state="loaded",
        runtime_data=types.SimpleNamespace(entry_id=entry_id),
    )


def _hass(entries, users=None, state="loaded"):
    """Build a minimal Home Assistant object."""
    users = users or {}

    async def _async_get_user(user_id):
        return users.get(user_id)

    for entry in entries:
        entry.state = state
    auth = types.SimpleNamespace(async_get_user=_async_get_user)
    config_entries = types.SimpleNamespace(async_entries=lambda domain: entries)
    registered = {}

    def _async_register(domain, name, handler, **kwargs):
        registered[(domain, name)] = (handler, kwargs)

    services = types.SimpleNamespace(async_register=_async_register)
    return types.SimpleNamespace(
        auth=auth, config_entries=config_entries, services=services,
        registered=registered,
    )


def _call(data=None, user_id=None):
    """Build a minimal service call."""
    return types.SimpleNamespace(
        data=data or {}, context=types.SimpleNamespace(user_id=user_id)
    )


class MultiUserServiceTest(unittest.IsolatedAsyncioTestCase):
    """Cover account selection and owner enforcement for integration services."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.integration, _, cls.exceptions, _ = _load_modules()

    async def _coordinator(self, hass, call):
        return await self.integration._coordinator_from_service_call(
            hass, call, "recording food"
        )

    async def test_owner_is_selected_without_explicit_account(self) -> None:
        entries = [
            _entry("e1", "Ana", "u1"),
            _entry("e2", "Jan", "u2"),
            _entry("e3", "Eva", "u3"),
        ]
        hass = _hass(
            entries,
            {
                "u1": types.SimpleNamespace(id="u1", is_admin=False),
                "u2": types.SimpleNamespace(id="u2", is_admin=False),
            },
        )

        coordinator = await self._coordinator(hass, _call(user_id="u2"))

        self.assertEqual(coordinator.entry_id, "e2")

    async def test_cross_account_service_call_is_rejected(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = _hass(
            entries,
            {
                "u1": types.SimpleNamespace(id="u1", is_admin=False),
                "u2": types.SimpleNamespace(id="u2", is_admin=False),
            },
        )
        call = _call({"config_entry_id": "e1"}, user_id="u2")

        with self.assertRaises(self.exceptions.Unauthorized):
            await self._coordinator(hass, call)

    async def test_account_label_resolution(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = _hass(
            entries,
            {
                "u1": types.SimpleNamespace(id="u1", is_admin=False),
                "u2": types.SimpleNamespace(id="u2", is_admin=False),
            },
        )

        coordinator = await self._coordinator(hass, _call({"account": "ana"}, user_id="u1"))

        self.assertEqual(coordinator.entry_id, "e1")
        with self.assertRaises(self.exceptions.Unauthorized):
            await self._coordinator(hass, _call({"account": "Ana"}, user_id="u2"))

    async def test_automation_can_target_any_account(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = _hass(entries)

        coordinator = await self._coordinator(
            hass, _call({"config_entry_id": "e2"})
        )

        self.assertEqual(coordinator.entry_id, "e2")

    async def test_admin_can_target_other_account(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = _hass(
            entries,
            {"admin": types.SimpleNamespace(id="admin", is_admin=True)},
        )

        coordinator = await self._coordinator(
            hass, _call({"config_entry_id": "e2"}, user_id="admin")
        )

        self.assertEqual(coordinator.entry_id, "e2")

    async def test_legacy_single_account_keeps_working(self) -> None:
        hass = _hass([_entry("e1", "old@example.test")])

        coordinator = await self._coordinator(hass, _call())

        self.assertEqual(coordinator.entry_id, "e1")

    async def test_multiple_unowned_accounts_still_need_selection(self) -> None:
        hass = _hass([_entry("e1", "Ana"), _entry("e2", "Jan")])

        with self.assertRaises(self.exceptions.HomeAssistantError):
            await self._coordinator(hass, _call())

    async def test_unknown_account_is_rejected(self) -> None:
        hass = _hass([_entry("e1", "Ana", "u1")])

        with self.assertRaises(self.exceptions.HomeAssistantError):
            await self._coordinator(hass, _call({"account": "Nobody"}))


class AccountHelperTest(unittest.TestCase):
    """Cover label and owner fallbacks for entries created before labels existed."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.integration, _, _, _ = _load_modules()

    def test_label_uses_options_then_data_then_title(self) -> None:
        label = self.integration.account_label
        self.assertEqual(label(_entry("e", "opt", "u")), "opt")
        entry = types.SimpleNamespace(
            title="legacy@example.test", data={}, options={"account_label": "Eva"}
        )
        self.assertEqual(label(entry), "Eva")
        entry = types.SimpleNamespace(title="legacy@example.test", data={}, options={})
        self.assertEqual(label(entry), "legacy@example.test")

    def test_owner_defaults_to_none(self) -> None:
        self.assertIsNone(self.integration.owner_user_id(_entry("e", "Ana")))
        self.assertEqual(
            self.integration.owner_user_id(_entry("e", "Ana", "u2")), "u2"
        )

    def test_owner_or_admin(self) -> None:
        check = self.integration.is_owner_or_admin
        owned = _entry("e", "Ana", "u1")
        self.assertTrue(check(types.SimpleNamespace(id="u1", is_admin=False), owned))
        self.assertTrue(check(types.SimpleNamespace(id="admin", is_admin=True), owned))
        self.assertFalse(check(types.SimpleNamespace(id="u2", is_admin=False), owned))
        self.assertTrue(
            check(
                types.SimpleNamespace(id="u2", is_admin=False),
                _entry("e", "legacy@example.test"),
            )
        )

    def test_default_label_from_email(self) -> None:
        account = sys.modules["custom_components.kaloricke_tabulky.account"]
        self.assertEqual(account.default_label_for_email("ANA@example.test"), "ANA")
        self.assertEqual(account.default_label_for_email("@example.test"), "Account")


class ButtonOwnerTest(unittest.IsolatedAsyncioTestCase):
    """Cover the defense-in-depth check on quick food buttons."""

    @classmethod
    def setUpClass(cls) -> None:
        _, cls.button, cls.exceptions, _ = _load_modules()

    async def test_wrong_user_cannot_press_another_users_button(self) -> None:
        entry = _entry("e1", "Ana", "u1")
        hass = _hass([], {"u2": types.SimpleNamespace(id="u2", is_admin=False)})
        fake = types.SimpleNamespace(
            _entry=entry, hass=hass, _context=types.SimpleNamespace(user_id="u2")
        )

        with self.assertRaises(self.exceptions.Unauthorized):
            await self.button.QuickFoodButton._async_assert_allowed_user(fake)

    async def test_owner_and_automation_can_press(self) -> None:
        entry = _entry("e1", "Ana", "u1")
        hass = _hass([], {"u1": types.SimpleNamespace(id="u1", is_admin=False)})
        method = self.button.QuickFoodButton._async_assert_allowed_user

        await method(
            types.SimpleNamespace(
                _entry=entry, hass=hass, _context=types.SimpleNamespace(user_id="u1")
            )
        )
        await method(
            types.SimpleNamespace(_entry=entry, hass=hass, _context=None)
        )


class GetSummaryServiceTest(unittest.IsolatedAsyncioTestCase):
    """Cover the owner-aware read service used by display integrations."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.integration, _, cls.exceptions, _ = _load_modules()

    def _hass_with_data(self, entries, users=None):
        hass = _hass(entries, users)
        for entry in entries:
            entry.runtime_data.data = types.SimpleNamespace(
                metrics={
                    "energy": types.SimpleNamespace(
                        key="energy", value=1500.0, unit="kcal",
                        goal=2000, percent=75,
                    )
                },
                weight_records=[types.SimpleNamespace(weight=72.5)],
            )
        return hass

    async def _handler(self, hass):
        await self.integration.async_setup(hass, {})
        handler, kwargs = hass.registered[("kaloricke_tabulky", "get_summary")]
        self.assertEqual(kwargs["supports_response"], "only")
        return handler

    async def test_user_gets_own_summary(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = self._hass_with_data(
            entries,
            {
                "u1": types.SimpleNamespace(id="u1", is_admin=False),
                "u2": types.SimpleNamespace(id="u2", is_admin=False),
            },
        )
        handler = await self._handler(hass)

        result = await handler(_call(user_id="u2"))

        self.assertEqual(result["account"], "Jan")
        self.assertEqual(result["metrics"]["energy"]["value"], 1500.0)
        self.assertEqual(result["weight"], 72.5)

    async def test_user_cannot_read_another_account(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = self._hass_with_data(
            entries,
            {"u1": types.SimpleNamespace(id="u1", is_admin=False)},
        )
        handler = await self._handler(hass)

        with self.assertRaises(self.exceptions.Unauthorized):
            await handler(_call({"account": "Jan"}, user_id="u1"))

    async def test_automation_can_read_with_explicit_account(self) -> None:
        entries = [_entry("e1", "Ana", "u1"), _entry("e2", "Jan", "u2")]
        hass = self._hass_with_data(entries)
        handler = await self._handler(hass)

        result = await handler(_call({"config_entry_id": "e2"}))

        self.assertEqual(result["account"], "Jan")


if __name__ == "__main__":
    unittest.main()
