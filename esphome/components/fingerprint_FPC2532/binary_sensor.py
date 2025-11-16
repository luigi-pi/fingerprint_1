import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ICON, CONF_ID, ICON_KEY_PLUS

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# CONF_SET_STATUS_AT_BOOT = "status_at_boot"
# CONF_STOP_MODE_UART = "stop_mode_uart"
# CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
# CONF_ENROLLING = "enrolling_binary"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]


def validate_icons(config):
    sensor_id = config[CONF_ID]
    config_icon_group = {
        "status_at_boot",
        "stop_mode_uart",
        "uart_irq_before_tx",
    }
    if sensor_id in config_icon_group:
        config.setdefault(CONF_ICON, ICON_CONFIG)
    elif sensor_id == "enrolling_binary":
        config.setdefault(CONF_ICON, ICON_KEY_PLUS)

    return config


CONFIG_SCHEMA = cv.All(
    binary_sensor.binary_sensor_schema().extend(
        {
            cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
                FingerprintFPC2532Component
            ),
        }
    ),
    validate_icons,
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sens = await binary_sensor.new_binary_sensor(config)
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_sensor")(sens))
