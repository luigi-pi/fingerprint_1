import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_SET_STATUS_AT_BOOT): switch.switch_schema(),
        cv.Optional(CONF_STOP_MODE_UART): switch.switch_schema(),
        cv.Optional(CONF_UART_IRQ_BEFORE_TX): switch.switch_schema(),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    if CONF_SET_STATUS_AT_BOOT in config:
        sw1 = await switch.new_switch(config[CONF_SET_STATUS_AT_BOOT])
        cg.add(hub.set_status_at_boot_switch(sw1))

    if CONF_STOP_MODE_UART in config:
        sw2 = await switch.new_switch(config[CONF_STOP_MODE_UART])
        cg.add(hub.set_stop_mode_uart_switch(sw2))

    if CONF_UART_IRQ_BEFORE_TX in config:
        sw3 = await switch.new_switch(config[CONF_UART_IRQ_BEFORE_TX])
        cg.add(hub.set_uart_irq_before_tx_switch(sw3))
