import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import CONF_ICON, CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_SENSOR_POWER_PIN = "sensor_power_pin"
CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]


def validate_icons(config):
    sensor_id = str(config[CONF_ID])
    config_icon_group = {
        CONF_SET_STATUS_AT_BOOT,
        CONF_STOP_MODE_UART,
        CONF_UART_IRQ_BEFORE_TX,
    }
    if sensor_id in config_icon_group:
        icon = ICON_CONFIG
    else:
        icon = "mdi:checkbox-blank-outline"
    return icon


def validate_stop_mode_uart(config):
    # Load full YAML
    full_yaml = cg.get_config()  # gives full config tree

    # 1. Check if stop_mode_uart switch exists
    if config.get(CONF_ID) != CONF_SET_STATUS_AT_BOOT:  # CONF_STOP_MODE_UART:
        return config

    # 2. Search for fingerprint component with sensor_power_pin
    found = False
    for key, comp in full_yaml.items():
        if (
            isinstance(comp, dict)
            and key == "fingerprint_FPC2532"
            and CONF_SENSOR_POWER_PIN in comp
        ):
            found = True
            break

    if not found:
        raise cv.Invalid(
            "The switch 'stop_mode_uart' requires 'sensor_power_pin' to be defined "
            "under a fingerprint_FPC2532 component."
        )

    return config


# Reference the embedded C++ class
FingerprintSwitch = (
    cg.global_ns.namespace("esphome")
    .namespace("fingerprint_FPC2532")
    .class_("FingerprintSwitch", switch.Switch)
)

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


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)
    if CONF_ICON not in config:
        icon = validate_icons(config)
        cg.add(sw.set_icon(icon))
    # cg.add(sw.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
