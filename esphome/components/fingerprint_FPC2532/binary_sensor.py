import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ICON, CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# CONF_SET_STATUS_AT_BOOT = "status_at_boot"
# CONF_STOP_MODE_UART = "stop_mode_uart"
# CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
# CONF_ENROLLING = "enrolling_binary"
ICON_CONFIG = "mdi:settings"

DEPENDENCIES = ["fingerprint_FPC2532"]


def validate_icons(config):
    sensor_id = config[CONF_ID]
    if sensor_id == "status_at_boot":
        config.setdefault(CONF_ICON, ICON_CONFIG)
    return config


CONFIG_SCHEMA = binary_sensor.binary_sensor_schema().extend(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_ICON, default=ICON_CONFIG): cv.icon,
    }.add_extra(validate_icons)
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sens = await binary_sensor.new_binary_sensor(config)
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_sensor")(sens))
