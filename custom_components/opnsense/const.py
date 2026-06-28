"""The OpnSense component."""

from __future__ import annotations

from typing import Final

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfTemperature,
    UnitOfTime,
)

DEFAULT_USERNAME = "admin"
DOMAIN = "opnsense"

UNDO_UPDATE_LISTENER = "undo_update_listener"

PLATFORMS = ["sensor", "switch", "device_tracker", "binary_sensor", "update"]
LOADED_PLATFORMS = "loaded_platforms"

OPNSENSE_CLIENT = "opnsense_client"
COORDINATOR = "coordinator"
DEVICE_TRACKER_COORDINATOR = "device_tracker_coordinator"
SHOULD_RELOAD = "should_reload"
TRACKED_MACS = "tracked_macs"
DEFAULT_SCAN_INTERVAL = 30
CONF_TLS_INSECURE = "tls_insecure"
DEFAULT_TLS_INSECURE = False
DEFAULT_VERIFY_SSL = True

CONF_DEVICE_TRACKER_ENABLED = "device_tracker_enabled"
DEFAULT_DEVICE_TRACKER_ENABLED = False

CONF_DEVICE_TRACKER_SCAN_INTERVAL = "device_tracker_scan_interval"
DEFAULT_DEVICE_TRACKER_SCAN_INTERVAL = 150

CONF_DEVICE_TRACKER_CONSIDER_HOME = "device_tracker_consider_home"
DEFAULT_DEVICE_TRACKER_CONSIDER_HOME = 0

CONF_DEVICES = "devices"

COUNT = "count"

# pulled from upnp component
BYTES_RECEIVED = "bytes_received"
BYTES_SENT = "bytes_sent"
PACKETS_RECEIVED = "packets_received"
PACKETS_SENT = "packets_sent"
DATA_PACKETS = "packets"
DATA_RATE_PACKETS_PER_SECOND = f"{DATA_PACKETS}/{UnitOfTime.SECONDS}"

ICON_MEMORY = "mdi:memory"

SENSOR_TYPES: Final[dict[str, SensorEntityDescription]] = {
    # pfstate (kept name for compatibility with metrics)
    "telemetry.pfstate.used": SensorEntityDescription(
        key="telemetry.pfstate.used",
        name="pf State Table Used",
        native_unit_of_measurement=COUNT,
        icon="mdi:table-network",
        state_class=SensorStateClass.MEASUREMENT,
    ),
}
