from esphome import automation
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import CONF_COMPONENTS, CONF_ID, CONF_NAME

CODEOWNERS = ["@esphome/tests"]

loop_test_component_ns = cg.esphome_ns.namespace("loop_test_component")
LoopTestComponent = loop_test_component_ns.class_("LoopTestComponent", cg.Component)
LoopTestISRComponent = loop_test_component_ns.class_(
    "LoopTestISRComponent", cg.Component
)

CONF_DISABLE_AFTER = "disable_after"
CONF_TEST_REDUNDANT_OPERATIONS = "test_redundant_operations"
CONF_ISR_COMPONENTS = "isr_components"

COMPONENT_CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(LoopTestComponent),
        cv.Required(CONF_NAME): cv.string,
        cv.Optional(CONF_DISABLE_AFTER, default=0): cv.int_,
        cv.Optional(CONF_TEST_REDUNDANT_OPERATIONS, default=False): cv.boolean,
    }
)

ISR_COMPONENT_CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(LoopTestISRComponent),
        cv.Required(CONF_NAME): cv.string,
    }
)

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(LoopTestComponent),
        cv.Required(CONF_COMPONENTS): cv.ensure_list(COMPONENT_CONFIG_SCHEMA),
        cv.Optional(CONF_ISR_COMPONENTS): cv.ensure_list(ISR_COMPONENT_CONFIG_SCHEMA),
    }
).extend(cv.COMPONENT_SCHEMA)

# Define actions
EnableAction = loop_test_component_ns.class_("EnableAction", automation.Action)
DisableAction = loop_test_component_ns.class_("DisableAction", automation.Action)


@automation.register_action(
    "loop_test_component.enable",
    EnableAction,
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.use_id(LoopTestComponent),
        }
    ),
)
async def enable_to_code(config, action_id, template_arg, args):
    parent = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_arg, parent)
    return var


@automation.register_action(
    "loop_test_component.disable",
    DisableAction,
    cv.Schema(
        {
            cv.Required(CONF_ID): cv.use_id(LoopTestComponent),
        }
    ),
)
async def disable_to_code(config, action_id, template_arg, args):
    parent = await cg.get_variable(config[CONF_ID])
    var = cg.new_Pvariable(action_id, template_arg, parent)
    return var


async def to_code(config):
    # The parent config doesn't actually create a component
    # We just create each sub-component
    for comp_config in config[CONF_COMPONENTS]:
        var = cg.new_Pvariable(comp_config[CONF_ID])
        await cg.register_component(var, comp_config)

        cg.add(var.set_name(comp_config[CONF_NAME]))
        cg.add(var.set_disable_after(comp_config[CONF_DISABLE_AFTER]))
        cg.add(
            var.set_test_redundant_operations(
                comp_config[CONF_TEST_REDUNDANT_OPERATIONS]
            )
        )

    # Create ISR test components
    for isr_config in config.get(CONF_ISR_COMPONENTS, []):
        var = cg.new_Pvariable(isr_config[CONF_ID])
        await cg.register_component(var, isr_config)
        cg.add(var.set_name(isr_config[CONF_NAME]))
