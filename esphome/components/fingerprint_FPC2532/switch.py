import esphome.codegen as cg
from esphome.components import switch
import esphome.config_validation as cv
from esphome.const import CONF_ID

from . import CONF_FINGERPRINT_FPC2532_ID, FingerprintFPC2532Component

CONF_ENROLLING_SWITCH = "enrolling_switch"
ICON_CONFIG = "mdi:cog"

DEPENDENCIES = ["fingerprint_FPC2532"]

# ------------------------------------------
# Schema: only ensure hub ID is provided
# ------------------------------------------
CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_FINGERPRINT_FPC2532_ID): cv.use_id(
            FingerprintFPC2532Component
        ),
        cv.Required(CONF_ID): cv.declare_id(),
    }
)


# ------------------------------------------
# to_code: create the switch and attach it to the hub
# ------------------------------------------
async def to_code(config):
    hub = await cg.get_variable(config[CONF_FINGERPRINT_FPC2532_ID])
    sw = await switch.new_switch(config)  # create the switch object
    # Attach switch to hub via setter
    cg.add(getattr(hub, f"set_{config[CONF_ID]}_switch")(sw))
