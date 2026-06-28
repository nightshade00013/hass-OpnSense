"""Converted sensors for OpnSense."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, STATE_UNKNOWN, __version__
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import slugify
from homeassistant.util.dt import utc_from_timestamp

from . import CoordinatorEntityManager, OpnSenseEntity, dict_get
from .const import (
    COORDINATOR,
    COUNT,
    DATA_PACKETS,
    DATA_RATE_PACKETS_PER_SECOND,
    DOMAIN,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: entity_platform.AddEntitiesCallback,
):
    """Set up the OpnSense sensors."""

    @callback
    def process_entities_callback(hass, config_entry):
        data = hass.data[DOMAIN][config_entry.entry_id]
        coordinator = data[COORDINATOR]
        state = coordinator.data
        resources = [sensor_id for sensor_id in SENSOR_TYPES]

        entities = []

        for sensor_type in resources:
            enabled_default = False
            if sensor_type in [
                "telemetry.pfstate.used_percent",
                "telemetry.mbuf.used_percent",
                "telemetry.memory.swap_used_percent",
                "telemetry.memory.used_percent",
                "telemetry.cpu.used_percent",
                "telemetry.cpu.frequency.current",
                "telemetry.system.load_average.one_minute",
                "telemetry.system.load_average.five_minute",
                "telemetry.system.load_average.fifteen_minute",
                "telemetry.system.temp",
                "telemetry.system.boottime",
                "dhcp_stats.leases.online",
            ]:
                enabled_default = True

            entity = OpnSenseStaticKeySensor(
                config_entry,
                coordinator,
                SENSOR_TYPES[sensor_type],
                enabled_default,
            )
            entities.append(entity)

        # filesystems
        for filesystem in dict_get(state, "telemetry.filesystems", []):
            device_clean = normalize_filesystem_device_name(filesystem["device"])
            mountpoint_clean = normalize_filesystem_device_name(
                filesystem["mountpoint"]
            )
            entity = OpnSenseFilesystemSensor(
                config_entry,
                coordinator,
                SensorEntityDescription(
                    key=f"telemetry.filesystems.{device_clean}",
                    name="Filesystem Used Percentage {}".format(mountpoint_clean),
                    native_unit_of_measurement=PERCENTAGE,
                    icon="mdi:harddisk",
                    state_class=SensorStateClass.MEASUREMENT,
                ),
                True,
            )
            entities.append(entity)

        # carp interfaces
        for interface in state["carp_interfaces"]:
            uniqid = interface["uniqid"]
            state_class = None
            native_unit_of_measurement = None
            icon = "mdi:check-network-outline"
            enabled_default = True

            entity = OpnSenseCarpInterfaceSensor(
                config_entry,
                coordinator,
                SensorEntityDescription(
                    key=f"carp.interface.{uniqid}",
                    name="CARP Interface Status {} ({})".format(
                        uniqid, interface["descr"]
                    ),
                    native_unit_of_measurement=native_unit_of_measurement,
                    icon=icon,
                    state_class=state_class,
                ),
                True,
            )
            entities.append(entity)

        # interfaces
        for interface_name in dict_get(state, "telemetry.interfaces", {}).keys():
            interface = state["telemetry"]["interfaces"][interface_name]
            for property in [
                "status",
                "inerrs",
                "outerrs",
                "collisions",
                "inbytespass",
                "inbytespass_kilobytes_per_second",
                "outbytespass",
                "outbytespass_kilobytes_per_second",
                "inpktspass",
                "inpktspass_packets_per_second",
                "outpktspass",
                "outpktspass_packets_per_second",
                "inbytesblock",
                "inbytesblock_kilobytes_per_second",
                "outbytesblock",
                "outbytesblock_kilobytes_per_second",
                "inpktsblock",
                "inpktsblock_packets_per_second",
                "outpktsblock",
                "outpktsblock_packets_per_second",
                "inbytes",
                "inbytes_kilobytes_per_second",
                "outbytes",
                "outbytes_kilobytes_per_second",
                "inpkts",
                "inpkts_packets_per_second",
                "outpkts",
                "outpkts_packets_per_second",
            ]:
                state_class = None
                native_unit_of_measurement = None
                icon = None
                enabled_default = False

                if property in [
                    "status",
                    "inbytes_kilobytes_per_second",
                    "outbytes_kilobytes_per_second",
                    "inpkts_packets_per_second",
                    "outpkts_packets_per_second",
                ]:
                    enabled_default = True

                if (
                    "_packets_per_second" in property
                    or "_kilobytes_per_second" in property
                ):
                    state_class = SensorStateClass.MEASUREMENT

                if "_packets_per_second" in property:
                    native_unit_of_measurement = DATA_RATE_PACKETS_PER_SECOND

                if "_kilobytes_per_second" in property:
                    native_unit_of_measurement = UnitOfDataRate.KILOBYTES_PER_SECOND

                if native_unit_of_measurement is None:
                    if "bytes" in property:
                        native_unit_of_measurement = UnitOfInformation.BYTES
                        state_class = SensorStateClass.TOTAL_INCREASING
                    if "pkts" in property:
                        native_unit_of_measurement = DATA_PACKETS
                        state_class = SensorStateClass.TOTAL_INCREASING

                if property in ["inerrs", "outerrs", "collisions"]:
                    native_unit_of_measurement = COUNT

                if "pkts" in property or "bytes" in property:
                    icon = "mdi:server-network"

                if property == "status":
                    icon = "mdi:check-network-outline"

                if icon is None:
                    icon = "mdi:gauge"

                entity = OpnSenseInterfaceSensor(
                    config_entry,
                    coordinator,
                    SensorEntityDescription(
                        key="telemetry.interface.{}.{}".format(
                            interface["ifname"], property
                        ),
                        name="Interface {} {}".format(interface["descr"], property),
                        native_unit_of_measurement=native_unit_of_measurement,
                        icon=icon,
                        state_class=state_class,
                    ),
                    enabled_default,
                )
                entities.append(entity)

        # gateways
        for gateway_name in dict_get(state, "telemetry.gateways", {}).keys():
            gateway = state["telemetry"]["gateways"][gateway_name]
            for property in ["status", "delay", "stddev", "loss"]:
                state_class = None
                native_unit_of_measurement = None
                icon = "mdi:router-network"
                enabled_default = True

                if property == "loss":
                    native_unit_of_measurement = PERCENTAGE

                if property in ["delay", "stddev"]:
                    native_unit_of_measurement = UnitOfTime.MILLISECONDS

                if property == "status":
                    icon = "mdi:check-network-outline"

                entity = OpnSenseGatewaySensor(
                    config_entry,
                    coordinator,
                    SensorEntityDescription(
                        key="telemetry.gateway.{}.{}".format(gateway["name"], property),
                        name="Gateway {} {}".format(gateway["name"], property),
                        native_unit_of_measurement=native_unit_of_measurement,
                        icon=icon,
                        state_class=state_class,
                    ),
                    enabled_default,
                )
                entities.append(entity)

        # openvpn servers
        for vpnid in dict_get(state, "telemetry.openvpn.servers", {}).keys():
            servers = dict_get(state, "telemetry.openvpn.servers", {})
            server = servers[vpnid]
            for property in [
                "connected_client_count",
                "total_bytes_recv",
                "total_bytes_sent",
                "total_bytes_recv_kilobytes_per_second",
                "total_bytes_sent_kilobytes_per_second",
            ]:
                state_class = None
                native_unit_of_measurement = None
                icon = None
                enabled_default = False

                if "_kilobytes_per_second" in property:
                    state_class = SensorStateClass.MEASUREMENT

                if property == "connected_client_count":
                    state_class = SensorStateClass.MEASUREMENT

                if "_kilobytes_per_second" in property:
                    native_unit_of_measurement = UnitOfDataRate.KILOBYTES_PER_SECOND

                if native_unit_of_measurement is None:
                    if "bytes" in property:
                        native_unit_of_measurement = UnitOfInformation.BYTES

                if property in ["connected_client_count"]:
                    native_unit_of_measurement = "clients"

                if "bytes" in property:
                    icon = "mdi:server-network"

{