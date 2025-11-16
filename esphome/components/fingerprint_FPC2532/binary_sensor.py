import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# CONF_SET_STATUS_AT_BOOT = "status_at_boot"
# CONF_STOP_MODE_UART = "stop_mode_uart"
# CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
CONF_ENROLLING = "enrolling_binary"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]

"""
def validate_icons(config):
    sensor_id = str(config[CONF_ID])
    config_icon_group = {
        CONF_SET_STATUS_AT_BOOT,
        CONF_STOP_MODE_UART,
        CONF_UART_IRQ_BEFORE_TX,
    }
    if sensor_id in config_icon_group:
        icon = ICON_CONFIG
    elif sensor_id == CONF_ENROLLING:
        icon = ICON_KEY_PLUS
    else:
        icon = "mdi:checkbox-blank-outline"
    return icon
"""

CONFIG_SCHEMA = binary_sensor.binary_sensor_schema().extend(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sens = await binary_sensor.new_binary_sensor(config)
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_sensor")(sens))


"""
    if CONF_ICON not in config:
        icon = validate_icons(config)
        cg.add(sens.set_icon(icon))
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_sensor")(sens))
"""
