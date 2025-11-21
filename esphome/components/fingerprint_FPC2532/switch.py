import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# Configuration keys
CONF_SENSOR_POWER_PIN = "sensor_power_pin"
CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"

DEPENDENCIES = ["fingerprint_FPC2532"]

# Optional icon
ICON_CONFIG = "mdi:cog"


def validate_icons(config):
    """Return icon for certain switches, default otherwise."""
    sensor_id = str(config[CONF_ID])
    if sensor_id in {
        CONF_SET_STATUS_AT_BOOT,
        CONF_STOP_MODE_UART,
        CONF_UART_IRQ_BEFORE_TX,
    }:
        return ICON_CONFIG
    return "mdi:checkbox-blank-outline"


def final_validate_stop_mode_uart(config, full_config):
    """Ensure 'status_at_boot' or 'stop_mode_uart' switches are only allowed
    if any fingerprint_FPC2532 component has a sensor_power_pin.
    """
    # Look for all switches in the full YAML
    switches = full_config.get("switch", [])
    for sw in switches:
        if sw.get(CONF_ID) in {CONF_SET_STATUS_AT_BOOT, CONF_STOP_MODE_UART}:
            # Check if any fingerprint component defines sensor_power_pin
            found = False
            for fp in full_config.get("fingerprint_FPC2532", []):
                if isinstance(fp, dict) and CONF_SENSOR_POWER_PIN in fp:
                    found = True
                    break
            if not found:
                raise cv.Invalid(
                    f"The switch '{sw[CONF_ID]}' requires 'sensor_power_pin' "
                    "to be defined in a fingerprint_FPC2532 component."
                )
    return config


# Reference the embedded C++ switch class
FingerprintSwitch = (
    cg.global_ns.namespace("esphome")
    .namespace("fingerprint_FPC2532")
    .class_("FingerprintSwitch", switch.Switch)
)

# Configuration schema
CONFIG_SCHEMA = cv.All(
    switch.switch_schema(FingerprintSwitch).extend(
        {
            cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
                FingerprintFPC2532Component
            ),
        }
    ),
    cv.final_validate(final_validate_stop_mode_uart),
)


# Generate C++ code
async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)

    # Set icon
    if "icon" not in config:
        cg.add(sw.set_icon(validate_icons(config)))

    # Link switch to hub
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
