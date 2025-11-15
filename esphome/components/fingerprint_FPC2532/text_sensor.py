import esphome.codegen as cg
from esphome.components import text_sensor
import esphome.config_validation as cv
from esphome.const import ENTITY_CATEGORY_DIAGNOSTIC

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_STATUS_TEXT = "text_status"
CONF_UNIQUE_ID = "unique_id"
CONF_VERSION = "version"
ICON_CONFIG = "mdi:settings"

DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Optional(CONF_STATUS_TEXT): text_sensor.text_sensor_schema(
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_UNIQUE_ID): text_sensor.text_sensor_schema(
            # entity_category=ENTITY_CATEGORY_CONFIG,
        ),
        cv.Optional(CONF_VERSION): text_sensor.text_sensor_schema(
            # entity_category=ENTITY_CATEGORY_CONFIG,
        ),
    }
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])

    for key in [CONF_STATUS_TEXT, CONF_VERSION, CONF_UNIQUE_ID]:
        if key not in config:
            continue
        conf = config[key]
        sens = await text_sensor.new_text_sensor(conf)
        cg.add(getattr(hub, f"set_{key}_sensor")(sens))
