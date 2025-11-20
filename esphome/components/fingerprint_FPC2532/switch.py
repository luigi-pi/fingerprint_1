import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_ENROLLING_SWITCH = "enrolling_switch"
ICON_CONFIG = "mdi:cog"
# CONF_SET_STATUS_AT_BOOT = "status_at_boot"
# CONF_STOP_MODE_UART = "stop_mode_uart"
# CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"

DEPENDENCIES = ["fingerprint_FPC2532"]


CONFIG_SCHEMA = switch.switch_schema().extend(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)
    # Dynamically call: hub.set_<id>_switch(sw)
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
