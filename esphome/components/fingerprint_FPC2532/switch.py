import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_CONFIG

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = switch.switch_schema().extend(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    # SWITCH: Set Status at Boot
    conf = {
        cv.GenerateID(): cv.declare_id(switch.Switch),  # ESPHome expects this
        "name": "Set Status At Boot",
    }
    sw = await switch.new_switch(conf)
    cg.add(sw.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw.set_icon(ICON_CONFIG))
    cg.add(hub.set_status_at_boot_switch(sw))

    # SWITCH2: Stop Mode UART
    sw2 = await switch.new_switch(
        {
            "name": "Stop Mode UART",
            "id": CONF_STOP_MODE_UART,
        }
    )
    cg.add(sw2.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw2.set_icon(ICON_CONFIG))
    cg.add(hub.set_stop_mode_uart_switch(sw2))

    # SWITCH3: uart_irq_before_tx
    sw3 = await switch.new_switch(
        {
            "name": "uart irq before tx",
            "id": CONF_UART_IRQ_BEFORE_TX,
        }
    )
    cg.add(sw3.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(sw3.set_icon(ICON_CONFIG))
    cg.add(hub.set_uart_irq_before_tx_switch(sw3))
