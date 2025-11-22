from esphome import automation, pins
import esphome.codegen as cg
from esphome.components import uart
import esphome.config_validation as cv
from esphome.const import (
    CONF_COLOR,
    CONF_COUNT,
    CONF_FINGER_ID,
    CONF_ID,
    CONF_NEW_PASSWORD,
    CONF_ON_ENROLLMENT_DONE,
    CONF_ON_ENROLLMENT_FAILED,
    CONF_ON_ENROLLMENT_SCAN,
    CONF_ON_FINGER_SCAN_INVALID,
    CONF_ON_FINGER_SCAN_MATCHED,
    CONF_ON_FINGER_SCAN_MISPLACED,
    CONF_ON_FINGER_SCAN_START,
    CONF_ON_FINGER_SCAN_UNMATCHED,
    CONF_PASSWORD,
    CONF_SENSING_PIN,
    CONF_SPEED,
    CONF_STATE,
    CONF_TRIGGER_ID,
)

CODEOWNERS = ["@luigi-pi"]
DEPENDENCIES = ["uart"]
AUTO_LOAD = ["binary_sensor", "sensor", "text_sensor", "switch"]
MULTI_CONF = True

CONF_FINGERPRINT_FPC2532_ID = "fingerprint_FPC2532_id"
CONF_SENSOR_POWER_PIN = "sensor_power_pin"
CONF_IDLE_PERIOD_TO_SLEEP = "idle_period_to_sleep"
CONF_ENROLL_TIMEOUT = "enroll_timeout"
CONF_LOCKOUT_TIME = "lockout_time_s"
CONF_UART_IRQ_BEFORE_TX = "uart_irq_before_tx"
CONF_STATUS_AT_BOOT = "status_at_boot"
CONF_STOP_MODE_UART = "stop_mode_uart"
CONF_UART_BAUDRATE = "uart_baudrate"
CONF_MAX_CONSECUTIVE_FAILS = "max_consecutive_fails"
CONF_TIME_BEFORE_SLEEP = "time_before_sleep_ms"
CONF_DELAY_BEFORE_IRQ = "delay_before_irq_ms"
CONF_FINGER_SCAN_INTERVAL = "finger_scan_interval_ms"
CFG_UART_BAUDRATE_9600 = 1
CFG_UART_BAUDRATE_19200 = 2
CFG_UART_BAUDRATE_57600 = 3
CFG_UART_BAUDRATE_115200 = 4
CFG_UART_BAUDRATE_921600 = 5

UART_BAUDRATE_OPTIONS = {
    "9600": CFG_UART_BAUDRATE_9600,
    "19200": CFG_UART_BAUDRATE_19200,
    "57600": CFG_UART_BAUDRATE_57600,
    "115200": CFG_UART_BAUDRATE_115200,
    "921600": CFG_UART_BAUDRATE_921600,
}


fingerprint_FPC2532_ns = cg.esphome_ns.namespace("fingerprint_FPC2532")
FingerprintFPC2532Component = fingerprint_FPC2532_ns.class_(
    "FingerprintFPC2532Component", cg.PollingComponent, uart.UARTDevice
)

FingerScanStartTrigger = fingerprint_FPC2532_ns.class_(
    "FingerScanStartTrigger", automation.Trigger.template()
)

FingerScanMatchedTrigger = fingerprint_FPC2532_ns.class_(
    "FingerScanMatchedTrigger", automation.Trigger.template(cg.uint16, cg.uint16)
)

FingerScanUnmatchedTrigger = fingerprint_FPC2532_ns.class_(
    "FingerScanUnmatchedTrigger", automation.Trigger.template()
)

FingerScanMisplacedTrigger = fingerprint_FPC2532_ns.class_(
    "FingerScanMisplacedTrigger", automation.Trigger.template()
)

FingerScanInvalidTrigger = fingerprint_FPC2532_ns.class_(
    "FingerScanInvalidTrigger", automation.Trigger.template()
)

EnrollmentScanTrigger = fingerprint_FPC2532_ns.class_(
    "EnrollmentScanTrigger", automation.Trigger.template(cg.uint8, cg.uint16)
)

EnrollmentDoneTrigger = fingerprint_FPC2532_ns.class_(
    "EnrollmentDoneTrigger", automation.Trigger.template(cg.uint16)
)

EnrollmentFailedTrigger = fingerprint_FPC2532_ns.class_(
    "EnrollmentFailedTrigger", automation.Trigger.template(cg.uint16)
)

EnrollmentAction = fingerprint_FPC2532_ns.class_("EnrollmentAction", automation.Action)
CancelEnrollmentAction = fingerprint_FPC2532_ns.class_(
    "CancelEnrollmentAction", automation.Action
)
DeleteAction = fingerprint_FPC2532_ns.class_("DeleteAction", automation.Action)
DeleteAllAction = fingerprint_FPC2532_ns.class_("DeleteAllAction", automation.Action)
LEDControlAction = fingerprint_FPC2532_ns.class_("LEDControlAction", automation.Action)
AuraLEDControlAction = fingerprint_FPC2532_ns.class_(
    "AuraLEDControlAction", automation.Action
)

AuraLEDState = fingerprint_FPC2532_ns.enum("AuraLEDState", True)
AURA_LED_STATES = {
    "BREATHING": AuraLEDState.BREATHING,
    "FLASHING": AuraLEDState.FLASHING,
    "ALWAYS_ON": AuraLEDState.ALWAYS_ON,
    "ALWAYS_OFF": AuraLEDState.ALWAYS_OFF,
    "GRADUAL_ON": AuraLEDState.GRADUAL_ON,
    "GRADUAL_OFF": AuraLEDState.GRADUAL_OFF,
}
validate_aura_led_states = cv.enum(AURA_LED_STATES, upper=True)
AuraLEDColor = fingerprint_FPC2532_ns.enum("AuraLEDColor", True)
AURA_LED_COLORS = {
    "RED": AuraLEDColor.RED,
    "BLUE": AuraLEDColor.BLUE,
    "PURPLE": AuraLEDColor.PURPLE,
    "GREEN": AuraLEDColor.GREEN,
    "YELLOW": AuraLEDColor.YELLOW,
    "CYAN": AuraLEDColor.CYAN,
    "WHITE": AuraLEDColor.WHITE,
}
validate_aura_led_colors = cv.enum(AURA_LED_COLORS, upper=True)


def validate(config):
    if CONF_SENSOR_POWER_PIN in config and CONF_SENSING_PIN not in config:
        raise cv.Invalid("You cannot use the Sensor Power Pin without a Sensing Pin")
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(FingerprintFPC2532Component),
            cv.Optional(CONF_SENSING_PIN): pins.gpio_input_pin_schema,
            cv.Optional(CONF_SENSOR_POWER_PIN): pins.gpio_output_pin_schema,
            cv.Optional(
                CONF_IDLE_PERIOD_TO_SLEEP
            ): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_ENROLL_TIMEOUT): cv.positive_time_period_seconds,
            cv.Optional(CONF_LOCKOUT_TIME, default=15): cv.uint8_t,
            cv.Optional(CONF_UART_IRQ_BEFORE_TX, default=True): cv.boolean,
            cv.Optional(CONF_STATUS_AT_BOOT, default=True): cv.boolean,
            cv.Optional(CONF_STOP_MODE_UART, default=False): cv.boolean,
            cv.Optional(CONF_UART_BAUDRATE, default="921600"): cv.enum(
                UART_BAUDRATE_OPTIONS
            ),
            cv.Optional(CONF_MAX_CONSECUTIVE_FAILS, default=5): cv.uint8_t,
            cv.Optional(
                CONF_TIME_BEFORE_SLEEP, default="0ms"
            ): cv.positive_time_period_milliseconds,
            cv.Optional(
                CONF_DELAY_BEFORE_IRQ, default="1ms"
            ): cv.positive_time_period_milliseconds,
            cv.Optional(
                CONF_FINGER_SCAN_INTERVAL, default="34ms"
            ): cv.positive_time_period_milliseconds,
            cv.Optional(CONF_PASSWORD): cv.uint32_t,
            cv.Optional(CONF_NEW_PASSWORD): cv.uint32_t,
            cv.Optional(CONF_ON_FINGER_SCAN_START): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        FingerScanStartTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_FINGER_SCAN_MATCHED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        FingerScanMatchedTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_FINGER_SCAN_UNMATCHED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        FingerScanUnmatchedTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_FINGER_SCAN_MISPLACED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        FingerScanMisplacedTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_FINGER_SCAN_INVALID): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        FingerScanInvalidTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_ENROLLMENT_SCAN): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        EnrollmentScanTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_ENROLLMENT_DONE): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        EnrollmentDoneTrigger
                    ),
                }
            ),
            cv.Optional(CONF_ON_ENROLLMENT_FAILED): automation.validate_automation(
                {
                    cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(
                        EnrollmentFailedTrigger
                    ),
                }
            ),
        }
    )
    .extend(cv.polling_component_schema("500ms"))
    .extend(uart.UART_DEVICE_SCHEMA),
    validate,
)


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    if CONF_PASSWORD in config:
        password = config[CONF_PASSWORD]
        cg.add(var.set_password(password))
    await uart.register_uart_device(var, config)

    if CONF_NEW_PASSWORD in config:
        new_password = config[CONF_NEW_PASSWORD]
        cg.add(var.set_new_password(new_password))

    if CONF_LOCKOUT_TIME in config:
        lockout_time_s = config[CONF_LOCKOUT_TIME]
        cg.add(var.set_lockout_time_s(lockout_time_s))

    if CONF_FINGER_SCAN_INTERVAL in config:
        finger_scan_interval_ms = config[CONF_FINGER_SCAN_INTERVAL]
        cg.add(var.set_finger_scan_interval_ms(finger_scan_interval_ms))

    if CONF_DELAY_BEFORE_IRQ in config:
        delay_before_irq_ms = config[CONF_DELAY_BEFORE_IRQ]
        cg.add(var.set_delay_before_irq_ms(delay_before_irq_ms))

    if CONF_TIME_BEFORE_SLEEP in config:
        time_before_sleep_ms = config[CONF_TIME_BEFORE_SLEEP]
        cg.add(var.set_time_before_sleep_ms(time_before_sleep_ms))

    if CONF_MAX_CONSECUTIVE_FAILS in config:
        max_consecutive_fails = config[CONF_MAX_CONSECUTIVE_FAILS]
        cg.add(var.set_max_consecutive_fails(max_consecutive_fails))

    if CONF_UART_BAUDRATE in config:
        uart_baudrate = config[CONF_UART_BAUDRATE]
        cg.add(var.set_uart_baudrate(uart_baudrate))

    if CONF_STOP_MODE_UART in config:
        stop_mode_uart = config[CONF_STOP_MODE_UART]
        cg.add(var.set_stop_mode_uart(stop_mode_uart))

    if CONF_STATUS_AT_BOOT in config:
        status_at_boot = config[CONF_STATUS_AT_BOOT]
        cg.add(var.set_status_at_boot(status_at_boot))

    if CONF_UART_IRQ_BEFORE_TX in config:
        uart_irq_before_tx = config[CONF_UART_IRQ_BEFORE_TX]
        cg.add(var.set_uart_irq_before_tx(uart_irq_before_tx))

    if CONF_SENSING_PIN in config:
        sensing_pin = await cg.gpio_pin_expression(config[CONF_SENSING_PIN])
        cg.add(var.set_sensing_pin(sensing_pin))

    if CONF_SENSOR_POWER_PIN in config:
        sensor_power_pin = await cg.gpio_pin_expression(config[CONF_SENSOR_POWER_PIN])
        cg.add(var.set_sensor_power_pin(sensor_power_pin))

    if CONF_IDLE_PERIOD_TO_SLEEP in config:
        idle_period_to_sleep_ms = config[CONF_IDLE_PERIOD_TO_SLEEP]
        cg.add(var.set_idle_period_to_sleep_ms(idle_period_to_sleep_ms))

    if CONF_ENROLL_TIMEOUT in config:
        enroll_timeout_ms = config[CONF_ENROLL_TIMEOUT]
        cg.add(var.set_enroll_timeout_ms(enroll_timeout_ms))

    for conf in config.get(CONF_ON_FINGER_SCAN_START, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_FINGER_SCAN_MATCHED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(
            trigger, [(cg.uint16, "finger_id"), (cg.uint16, "tag")], conf
        )

    for conf in config.get(CONF_ON_FINGER_SCAN_UNMATCHED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_FINGER_SCAN_MISPLACED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [], conf)

    for conf in config.get(CONF_ON_FINGER_SCAN_INVALID, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint16, "capture_error")], conf)

    for conf in config.get(CONF_ON_ENROLLMENT_SCAN, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint16, "finger_id")], conf)

    for conf in config.get(CONF_ON_ENROLLMENT_DONE, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint16, "finger_id")], conf)

    for conf in config.get(CONF_ON_ENROLLMENT_FAILED, []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(cg.uint16, "finger_id")], conf)


@automation.register_action(
    "fingerprint_FPC2532.enroll",
    EnrollmentAction,
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
            cv.Optional(CONF_FINGER_ID): cv.templatable(cv.uint16_t),
        },
        key=CONF_FINGER_ID,
    ),
)
async def fingerprint_FPC2532_enroll_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])

    if CONF_FINGER_ID in config:
        template_ = await cg.templatable(config[CONF_FINGER_ID], args, cg.uint16)
        cg.add(var.set_finger_id(template_))
    else:
        cg.add(var.set_finger_id(cg.uint16(0)))
    return var


@automation.register_action(
    "fingerprint_FPC2532.cancel_enroll",
    CancelEnrollmentAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
        }
    ),
)
async def fingerprint_FPC2532_cancel_enroll_to_code(
    config, action_id, template_arg, args
):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


@automation.register_action(
    "fingerprint_FPC2532.delete",
    DeleteAction,
    cv.maybe_simple_value(
        {
            cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
            cv.Required(CONF_FINGER_ID): cv.templatable(cv.uint16_t),
        },
        key=CONF_FINGER_ID,
    ),
)
async def fingerprint_FPC2532_delete_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])

    template_ = await cg.templatable(config[CONF_FINGER_ID], args, cg.uint16)
    cg.add(var.set_finger_id(template_))
    return var


@automation.register_action(
    "fingerprint_FPC2532.delete_all",
    DeleteAllAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
        }
    ),
)
async def fingerprint_FPC2532_delete_all_to_code(config, action_id, template_arg, args):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])
    return var


FINGERPRINT__LED_CONTROL_ACTION_SCHEMA = cv.maybe_simple_value(
    {
        cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
        cv.Required(CONF_STATE): cv.templatable(cv.boolean),
    },
    key=CONF_STATE,
)


@automation.register_action(
    "fingerprint_FPC2532.led_control",
    LEDControlAction,
    FINGERPRINT__LED_CONTROL_ACTION_SCHEMA,
)
async def fingerprint_FPC2532_led_control_to_code(
    config, action_id, template_arg, args
):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])

    template_ = await cg.templatable(config[CONF_STATE], args, cg.bool_)
    cg.add(var.set_state(template_))
    return var


@automation.register_action(
    "fingerprint_FPC2532.aura_led_control",
    AuraLEDControlAction,
    cv.Schema(
        {
            cv.GenerateID(): cv.use_id(FingerprintFPC2532Component),
            cv.Required(CONF_STATE): cv.templatable(validate_aura_led_states),
            cv.Required(CONF_SPEED): cv.templatable(cv.uint8_t),
            cv.Required(CONF_COLOR): cv.templatable(validate_aura_led_colors),
            cv.Required(CONF_COUNT): cv.templatable(cv.uint8_t),
        }
    ),
)
async def fingerprint_FPC2532_aura_led_control_to_code(
    config, action_id, template_arg, args
):
    var = cg.new_Pvariable(action_id, template_arg)
    await cg.register_parented(var, config[CONF_ID])

    for key in [CONF_STATE, CONF_SPEED, CONF_COLOR, CONF_COUNT]:
        template_ = await cg.templatable(config[key], args, cg.uint8)
        cg.add(getattr(var, f"set_{key}")(template_))
    return var
