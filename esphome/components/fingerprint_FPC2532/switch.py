import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_ENROLLING_SWITCH = "enrolling_switch"
DEPENDENCIES = ["fingerprint_FPC2532"]

CONFIG_SCHEMA = switch.switch_schema(FingerprintFPC2532Component).extend(
    {cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(FingerprintFPC2532Component)}
)


async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
