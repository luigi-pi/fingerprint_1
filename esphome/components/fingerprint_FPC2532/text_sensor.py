import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

# CONF_STATUS_TEXT = "text_status"
# CONF_UNIQUE_ID = "unique_id"
# CONF_VERSION = "version"
# ICON_CONFIG = "mdi:settings"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = text_sensor.text_sensor_schema().extend(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sens = await text_sensor.new_text_sensor(config)
    cg.add(getattr(hub, f"set_{config['id']}_sensor")(sens))
