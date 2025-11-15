import esphome.codegen as cg
from esphome.components import binary_sensor
import esphome.config_validation as cv
from esphome.const import CONF_ICON, ICON_KEY_PLUS

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_SET_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
ICON_CONFIG = "mdi:settings"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = binary_sensor.binary_sensor_schema().extend(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_ICON, default=ICON_KEY_PLUS): cv.icon,
        cv.Optional(CONF_SET_STATUS_AT_BOOT, default=True): cv.boolean,
        cv.Optional(CONF_STOP_MODE_UART, default=False): cv.boolean,
        cv.Optional(CONF_UART_IRQ_BEFORE_TX, default=True): cv.boolean,
    },
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    # This is the user-defined binary sensor from YAML
    main_sensor = await binary_sensor.new_binary_sensor(config)
    cg.add(hub.set_enrolling_binary_sensor(main_sensor))

    # ---- Internal config-related binary sensors ----
    # These are NOT in YAML -> must use BinarySensor.new()

    set_status_sensor = binary_sensor.BinarySensor.new()
    cg.add(set_status_sensor.set_icon(ICON_CONFIG))
    cg.add(hub.set_status_at_boot_sensor(set_status_sensor))

    stop_mode_sensor = binary_sensor.BinarySensor.new()
    cg.add(stop_mode_sensor.set_icon(ICON_CONFIG))
    cg.add(hub.set_stop_mode_uart_sensor(stop_mode_sensor))

    uart_irq_sensor = binary_sensor.BinarySensor.new()
    cg.add(uart_irq_sensor.set_icon(ICON_CONFIG))
    cg.add(hub.set_uart_irq_before_tx_sensor(uart_irq_sensor))
