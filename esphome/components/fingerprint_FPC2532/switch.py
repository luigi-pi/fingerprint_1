import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_CONFIG

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = cv.Schema(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    #
    # SWITCH 1
    #
    sw1 = await switch.new_switch(
        {
            cg.CONF_ID: cg.declare_id(switch.Switch),
            "name": "Set Status At Boot",
        }
    )
    await cg.register_component(sw1, {})  # <-- REQUIRED
    cg.add(sw1.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(hub.set_status_at_boot_switch(sw1))

    #
    # SWITCH 2
    #
    sw2 = await switch.new_switch(
        {
            cg.CONF_ID: cg.declare_id(switch.Switch),
            "name": "Stop Mode UART",
        }
    )
    await cg.register_component(sw2, {})  # <-- REQUIRED
    cg.add(sw2.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(hub.set_stop_mode_uart_switch(sw2))

    #
    # SWITCH 3
    #
    sw3 = await switch.new_switch(
        {
            cg.CONF_ID: cg.declare_id(switch.Switch),
            "name": "UART IRQ Before TX",
        }
    )
    await cg.register_component(sw3, {})  # <-- REQUIRED
    cg.add(sw3.set_entity_category(ENTITY_CATEGORY_CONFIG))
    cg.add(hub.set_uart_irq_before_tx_switch(sw3))
