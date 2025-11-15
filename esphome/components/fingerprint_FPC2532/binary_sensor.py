import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import ICON_KEY_PLUS

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
CONF_ENROLLING = "enrolling_binary"
ICON_CONFIG = "mdi:settings"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_ENROLLING): binary_sensor.binary_sensor_schema(
            icon=ICON_KEY_PLUS,
        ),
        cv.Optional(CONF_STOP_MODE_UART): binary_sensor.binary_sensor_schema(
            icon=ICON_CONFIG,
        ),
        cv.Optional(CONF_SET_STATUS_AT_BOOT): binary_sensor.binary_sensor_schema(
            icon=ICON_CONFIG,
        ),
        cv.Optional(CONF_UART_IRQ_BEFORE_TX): binary_sensor.binary_sensor_schema(
            icon=ICON_CONFIG,
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    for key in [
        CONF_ENROLLING,
        CONF_SET_STATUS_AT_BOOT,
        CONF_STOP_MODE_UART,
        CONF_UART_IRQ_BEFORE_TX,
    ]:
        if key not in config:
            continue
        conf = config[key]
        sens = await binary_sensor.new_binary_sensor(conf)
        cg.add(getattr(hub, f"set_{key}_sensor")(sens))
