import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_CONFIG

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

ICON_CONFIG = "mdi:cog"

# Switch identifiers
CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"


DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = cv.Schema(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    # Get the hub instance
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    # -------------------------------
    # SWITCH 1: Set Status At Boot
    # -------------------------------
    sw1_conf = {
        cg.GenerateID(): cg.declare_id(switch.Switch),
        "name": "Set Status At Boot",
    }
    sw1 = await switch.new_switch(sw1_conf)
    cg.add(sw1.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw1.set_icon(ICON_CONFIG))
    cg.add(hub.set_status_at_boot_switch(sw1))

    # -------------------------------
    # SWITCH 2: Stop Mode UART
    # -------------------------------
    sw2_conf = {
        cg.GenerateID(): cg.declare_id(switch.Switch),
        "name": "Stop Mode UART",
    }
    sw2 = await switch.new_switch(sw2_conf)
    cg.add(sw2.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw2.set_icon(ICON_CONFIG))
    cg.add(hub.set_stop_mode_uart_switch(sw2))

    # -------------------------------
    # SWITCH 3: UART IRQ Before TX
    # -------------------------------
    sw3_conf = {
        cg.GenerateID(): cg.declare_id(switch.Switch),
        "name": "UART IRQ Before TX",
    }
    sw3 = await switch.new_switch(sw3_conf)
    cg.add(sw3.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw3.set_icon(ICON_CONFIG))
    cg.add(hub.set_uart_irq_before_tx_switch(sw3))
