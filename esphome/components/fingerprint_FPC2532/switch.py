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


# Optional icon logic
ICON_CONFIG = "mdi:cog"


def validate_icons(config):
    sensor_id = str(config[CONF_ID])
    config_icon_group = {
        CONF_SET_STATUS_AT_BOOT,
        CONF_STOP_MODE_UART,
        CONF_UART_IRQ_BEFORE_TX,
    }
    if sensor_id in config_icon_group:
        return ICON_CONFIG
    return "mdi:checkbox-blank-outline"


# Validator for stop_mode_uart switch
def validate_stop_mode_uart(config):
    """Ensure 'stop_mode_uart' switch is allowed only if 'sensor_power_pin' exists."""

    # Only validate stop_mode_uart switch
    if config.get(CONF_ID) != CONF_SET_STATUS_AT_BOOT:
        return config

    # Load the full ESPHome configuration tree
    full_yaml = cg.get_config()

    # Check if fingerprint_FPC2532 component exists
    if "fingerprint_FPC2532" not in full_yaml:
        raise cv.Invalid(
            "The switch 'stop_mode_uart' requires the fingerprint_FPC2532 component "
            "to be defined in the YAML."
        )

    # fingerprint_FPC2532 is a list of component configs
    fp_configs = full_yaml["fingerprint_FPC2532"]

    # Search for sensor_power_pin in any fingerprint_FPC2532 component
    found = False
    for comp in fp_configs:
        if isinstance(comp, dict) and CONF_SENSOR_POWER_PIN in comp:
            found = True
            break

    if not found:
        raise cv.Invalid(
            "The switch 'stop_mode_uart' requires 'sensor_power_pin' to be defined "
            "inside the fingerprint_FPC2532 component."
        )

    return config


# Reference the embedded C++ switch class
FingerprintSwitch = (
    cg.global_ns.namespace("esphome")
    .namespace("fingerprint_FPC2532")
    .class_("FingerprintSwitch", switch.Switch)
)


# Configuration schema for the switch
CONFIG_SCHEMA = cv.All(
    switch.switch_schema(FingerprintSwitch).extend(
        {
            cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
                FingerprintFPC2532Component
            ),
        }
    ),
    validate_stop_mode_uart,
)


# Generate the C++ code
async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)

    # Optional: set icon
    if "icon" not in config:
        cg.add(sw.set_icon(validate_icons(config)))

    # Link switch to the hub
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
