import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_CONFIG

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# Icons
ICON_CONFIG = "mdi:cog"

# Switch identifiers
CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"

DEPENDENCIES = ["fingerprint_FPC2532"]

# -------------------------
# Configuration schema
# -------------------------
CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_SET_STATUS_AT_BOOT): switch.switch_schema(
            icon=ICON_CONFIG,
            entity_category=ENTITY_CATEGORY_CONFIG,
            default_restore_mode="DISABLED",
        ),
        cv.Optional(CONF_STOP_MODE_UART): switch.switch_schema(
            icon=ICON_CONFIG,
            entity_category=ENTITY_CATEGORY_CONFIG,
            default_restore_mode="DISABLED",
        ),
        cv.Optional(CONF_UART_IRQ_BEFORE_TX): switch.switch_schema(
            icon=ICON_CONFIG,
            entity_category=ENTITY_CATEGORY_CONFIG,
            default_restore_mode="DISABLED",
        ),
    }
)


# -------------------------
# Code generation
# -------------------------
async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    # Loop through each possible switch
    for switch_id, setter_name in [
        (CONF_SET_STATUS_AT_BOOT, "set_status_at_boot_switch"),
        (CONF_STOP_MODE_UART, "set_stop_mode_uart_switch"),
        (CONF_UART_IRQ_BEFORE_TX, "set_uart_irq_before_tx_switch"),
    ]:
        if conf := config.get(switch_id):
            sw_var = await switch.new_switch(conf)
            cg.add(getattr(hub, setter_name)(sw_var))
