#include "fingerprint_FPC2532.h"
#include "esphome/core/log.h"
//#include "esphome.h"
#include <cinttypes>
#include <vector>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {

static const char *const TAG = "fingerprint_FPC2532";

void FingerprintFPC2532Component::update() {
  digitalWrite(2, LED_state_ ? HIGH : LOW);
  if (millis() - start_ > 1000) {
    ESP_LOGI(TAG, "manda il comando status");
    fpc_cmd_status_request();
    start_ = millis();
    LED_state_ = !LED_state_;
  }
  fpc::fpc_result_t result;
  size_t n = this->available();
  if (n) {
    ESP_LOGI(TAG, "number of bytes available to read: %d", n);
    result = fpc_host_sample_handle_rx_data();
    if (result != FPC_RESULT_OK) {
      ESP_LOGE(TAG, "Failed to handle RX data, error %d", result);
      fpc_hal_delay_ms(10);
    }
  } else {
    ESP_LOGI(TAG, "No data available");
  }
}

void FingerprintFPC2532Component::setup() {
  this->fpc_hal_init();
  fpc_cmd_status_request();
  start_ = millis();
  LED_state_ = true;
  pinMode(2, OUTPUT);  // blue builtin LED
}

/*
------------------------
HOST FUNCTIONS DEFINITONS
------------------------
*/
/** Optional command callback functions. */
FingerprintFPC2532Component::fpc_cmd_callbacks_t cmd_callbacks;
/*Helper functions*/

const char *get_id_type_str_(uint16_t id_type) {
  switch (id_type) {
    case ID_TYPE_NONE:
      return "ID.None";
    case ID_TYPE_ALL:
      return "ID.All";
    case ID_TYPE_SPECIFIED:
      return "ID.Specified";
    case ID_TYPE_GENERATE_NEW:
      return "ID.Generate";
  }
  return "ID.Unknown";
}

const char *get_event_str_(uint16_t evt) {
  switch (evt) {
    case EVENT_NONE:
      return "Evt.None";
    case EVENT_IDLE:
      return "Evt.Idle";
    case EVENT_ARMED:
      return "Evt.Armed";
    case EVENT_FINGER_DETECT:
      return "Evt.FingerDetect";
    case EVENT_FINGER_LOST:
      return "Evt.FingerLost";
    case EVENT_IMAGE_READY:
      return "Evt.ImageCaptured";
    case EVENT_CMD_FAILED:
      return "Evt.Failure";
  }
  return "Evt.Unknown";
}

const char *get_enroll_feedback_str_(uint8_t feedback) {
  switch (feedback) {
    case ENROLL_FEEDBACK_DONE:
      return "Done";
    case ENROLL_FEEDBACK_PROGRESS:
      return "Progress";
    case ENROLL_FEEDBACK_REJECT_LOW_QUALITY:
      return "Reject.LowQuality";
    case ENROLL_FEEDBACK_REJECT_LOW_COVERAGE:
      return "Reject.LowCoverage";
    case ENROLL_FEEDBACK_REJECT_LOW_MOBILITY:
      return "Reject.LowMobility";
    case ENROLL_FEEDBACK_REJECT_OTHER:
      return "Reject.Other";
    case ENROLL_FEEDBACK_PROGRESS_IMMOBILE:
      return "Progress.Immobile";
    default:
      break;
  }
  return "Unknown";
}

const char *get_gesture_str_(uint8_t gesture) {
  switch (gesture) {
    case CMD_NAV_EVENT_NONE:
      return "None";
    case CMD_NAV_EVENT_UP:
      return "Gesture.Up";
    case CMD_NAV_EVENT_DOWN:
      return "Gesture.Down";
    case CMD_NAV_EVENT_RIGHT:
      return "Gesture.Right";
    case CMD_NAV_EVENT_LEFT:
      return "Gesture.Left";
    case CMD_NAV_EVENT_PRESS:
      return "Gesture.Press";
    case CMD_NAV_EVENT_LONG_PRESS:
      return "Gesture.LongPress";
    default:
      break;
  }
  return "Unknown";
}

const char *fpc_result_to_string(fpc::fpc_result_t result) {
  switch (result) {
    // Information / Success
    case FPC_RESULT_OK:
      return "OK";
    case FPC_PENDING_OPERATION:
      return "Pending Operation";
    case FPC_RESULT_DATA_NOT_SET:
      return "Data Not Set";
    case FPC_RESULT_CMD_ID_NOT_SUPPORTED:
      return "Command ID Not Supported";

    // General Errors
    case FPC_RESULT_FAILURE:
      return "Failure";
    case FPC_RESULT_INVALID_PARAM:
      return "Invalid Parameter";
    case FPC_RESULT_WRONG_STATE:
      return "Wrong State";
    case FPC_RESULT_OUT_OF_MEMORY:
      return "Out of Memory";
    case FPC_RESULT_TIMEOUT:
      return "Timeout";
    case FPC_RESULT_NOT_SUPPORTED:
      return "Not Supported";

    // Template / User ID Errors
    case FPC_RESULT_USER_ID_EXISTS:
      return "User ID Exists";
    case FPC_RESULT_USER_ID_NOT_FOUND:
      return "User ID Not Found";
    case FPC_RESULT_STORAGE_IS_FULL:
      return "Storage Is Full";
    case FPC_RESULT_FLASH_ERROR:
      return "Flash Error";
    case FPC_RESULT_IDENTIFY_LOCKOUT:
      return "Identify Lockout";
    case FPC_RESULT_STORAGE_IS_EMPTY:
      return "Storage Is Empty";

    // IO Errors
    case FPC_RESULT_IO_BUSY:
      return "IO Busy";
    case FPC_RESULT_IO_RUNTIME_FAILURE:
      return "IO Runtime Failure";
    case FPC_RESULT_IO_BAD_DATA:
      return "IO Bad Data";
    case FPC_RESULT_IO_NOT_SUPPORTED:
      return "IO Not Supported";
    case FPC_RESULT_IO_NO_DATA:
      return "IO No Data";

    // Image Capture Errors
    case FPC_RESULT_COULD_NOT_ARM:
      return "Could Not Arm";
    case FPC_RESULT_CAPTURE_FAILED:
      return "Capture Failed";
    case FPC_RESULT_BAD_IMAGE_QUALITY:
      return "Bad Image Quality";
    case FPC_RESULT_NO_IMAGE:
      return "No Image";

    // Other Errors
    case FPC_RESULT_SENSOR_ERROR:
      return "Sensor Error";
    case FPC_RESULT_PROTOCOL_VERSION_ERROR:
      return "Protocol Version Error";
    case FPC_STARTUP_FAILURE:
      return "Startup Failure";

    default:
      return "Unknown Error";
  }
}

/* Command Requests */
fpc::fpc_result_t FingerprintFPC2532Component::fpc_send_request(fpc::fpc_cmd_hdr_t *cmd, size_t size) {
  fpc::fpc_result_t result = FPC_RESULT_OK;
  fpc::fpc_frame_hdr_t frame = {0};

  if (!cmd) {
    ESP_LOGE(TAG, "Invalid command");
    result = FPC_RESULT_INVALID_PARAM;
  }

  if (result == FPC_RESULT_OK) {
    frame.version = FPC_FRAME_PROTOCOL_VERSION;
    frame.type = FPC_FRAME_TYPE_CMD_REQUEST;
    frame.flags = FPC_FRAME_FLAG_SENDER_HOST;
    frame.payload_size = (uint16_t) size;

    /* Send frame header. */
    result = this->fpc_hal_tx((uint8_t *) &frame, sizeof(fpc::fpc_frame_hdr_t));
    ESP_LOGI(TAG, "frame header sent: version=%02X, flags=%02X, type=%02X, payload_size=%" PRIu32, frame.version,
             frame.flags, frame.type, frame.payload_size);
  }

  if (result == FPC_RESULT_OK) {
    /* Send payload. */
    result = this->fpc_hal_tx((uint8_t *) cmd, size);
    ESP_LOGI(TAG, "command payload sent");
  }

  // Wait for response using cached loop start time
  // const uint32_t start = App.get_loop_component_start_time();
  const uint32_t start = millis();
  const uint32_t timeout_ms = 100;
  if (result == FPC_RESULT_OK) {
    while (!available()) {
      // if (App.get_loop_component_start_time() - start > timeout_ms) {
      if (millis() - start > timeout_ms) {
        ESP_LOGE(TAG, "full packet added in buffer but no answer from sensor available (timeout)");
        return FPC_RESULT_TIMEOUT;
      }
      delay(1);
    }
    ESP_LOGI(TAG, "full packet sent and answer from sensor available");
    result = FPC_RESULT_OK;
  }
  return result;
}

fpc::fpc_result_t FingerprintFPC2532Component::fpc_cmd_status_request(void) {
  fpc::fpc_result_t result = FPC_RESULT_OK;
  fpc::fpc_cmd_hdr_t cmd;

  /* Status Command Request has no payload */
  cmd.cmd_id = CMD_STATUS;
  cmd.type = FPC_FRAME_TYPE_CMD_REQUEST;

  ESP_LOGI(TAG, ">>> CMD_STATUS");
  result = this->FingerprintFPC2532Component::fpc_send_request(&cmd, sizeof(fpc::fpc_cmd_hdr_t));

  return result;
}

/* Command Responses / Events */
fpc::fpc_result_t FingerprintFPC2532Component::fpc_host_sample_handle_rx_data(void) {
  fpc::fpc_result_t result;
  fpc::fpc_frame_hdr_t frame_hdr;
  // std::vector<uint8_t> frame_payload;
  uint8_t *frame_payload = NULL;

  /* Step 1: Read Frame Header */
  result = this->fpc_hal_rx((uint8_t *) &frame_hdr, sizeof(fpc::fpc_frame_hdr_t));

  if (result == FPC_RESULT_OK) {
    ESP_LOGE(TAG, "Sanity check started");
    /* Sanity Check */
    if (frame_hdr.version != FPC_FRAME_PROTOCOL_VERSION || ((frame_hdr.flags & FPC_FRAME_FLAG_SENDER_FW_APP) == 0) ||
        (frame_hdr.type != FPC_FRAME_TYPE_CMD_RESPONSE && frame_hdr.type != FPC_FRAME_TYPE_CMD_EVENT)) {
      ESP_LOGE(TAG, "Sanity check of rx data failed");
      result = FPC_RESULT_IO_BAD_DATA;
    } else {
      ESP_LOGI(TAG, "Received Header frame: version=%02X, flags=%02X, type=%02X, payload_size=%" PRIu32,
               frame_hdr.version, frame_hdr.flags, frame_hdr.type, frame_hdr.payload_size);
    }
  }

  if (result == FPC_RESULT_OK) {
    frame_payload = static_cast<uint8_t *>(malloc(frame_hdr.payload_size));
    if (!frame_payload) {
      ESP_LOGE(TAG, "Failed to malloc");
      result = FPC_RESULT_OUT_OF_MEMORY;
    }
  }

  if (result == FPC_RESULT_OK) {
    /* Step 2: Read Frame Payload (Command) */
    result = this->fpc_hal_rx(frame_payload, frame_hdr.payload_size);
  }

  if (result == FPC_RESULT_OK) {
    result = parse_cmd(frame_payload, frame_hdr.payload_size);
  }

  if (frame_payload) {
    free(frame_payload);
  }

  if (result != FPC_RESULT_OK) {
    ESP_LOGE(TAG, "Failed to handle RX data, error %d", result);
  }

  return result;
}

fpc::fpc_result_t FingerprintFPC2532Component::parse_cmd(uint8_t *frame_payload, std::size_t size) {
  fpc::fpc_result_t result = FPC_RESULT_OK;
  fpc::fpc_cmd_hdr_t *cmd_hdr;

  cmd_hdr = (fpc::fpc_cmd_hdr_t *) frame_payload;

  if (!cmd_hdr) {
    ESP_LOGE(TAG, "Parse Cmd: Invalid parameter");
    result = FPC_RESULT_INVALID_PARAM;
  }

  if (result == FPC_RESULT_OK) {
    if (cmd_hdr->type != FPC_FRAME_TYPE_CMD_EVENT && cmd_hdr->type != FPC_FRAME_TYPE_CMD_RESPONSE) {
      ESP_LOGE(TAG, "Parse Cmd: Invalid parameter (type)");
      result = FPC_RESULT_INVALID_PARAM;
    }
  }

  if (result == FPC_RESULT_OK) {
    switch (cmd_hdr->cmd_id) {
      case CMD_STATUS:
        return parse_cmd_status(cmd_hdr, size);
        break;
      /*
      case CMD_VERSION:
        return parse_cmd_version(cmd_hdr, size);
        break;
      case CMD_ENROLL:
        return parse_cmd_enroll_status(cmd_hdr, size);
        break;
      case CMD_IDENTIFY:
        return parse_cmd_identify(cmd_hdr, size);
        break;
      case CMD_LIST_TEMPLATES:
        return parse_cmd_list_templates(cmd_hdr, size);
        break;
      case CMD_NAVIGATION:
        return parse_cmd_navigation_event(cmd_hdr, size);
        break;
      case CMD_GPIO_CONTROL:
        return parse_cmd_gpio_control(cmd_hdr, size);
        break;
      case CMD_GET_SYSTEM_CONFIG:
        return parse_cmd_get_system_config(cmd_hdr, size);
        break;
      case CMD_BIST:
        return parse_cmd_bist(cmd_hdr, size);
        break;
       */
      default:
        ESP_LOGE(TAG, "Parse Cmd: Unexpected Command ID");
        break;
    };
  }

  return result;
}

fpc::fpc_result_t FingerprintFPC2532Component::parse_cmd_status(fpc::fpc_cmd_hdr_t *cmd_hdr, std::size_t size) {
  fpc::fpc_result_t result = FPC_RESULT_OK;
  fpc::fpc_cmd_status_response_t *status;

  status = (fpc::fpc_cmd_status_response_t *) cmd_hdr;

  if (!status) {
    ESP_LOGE(TAG, "CMD_STATUS: Invalid parameter");
    result = FPC_RESULT_INVALID_PARAM;
  }

  if (result == FPC_RESULT_OK) {
    if (size != sizeof(fpc::fpc_cmd_status_response_t)) {
      ESP_LOGE(TAG, "CMD_STATUS invalid size (%d vs %d)", size, sizeof(fpc::fpc_cmd_status_response_t));
      result = FPC_RESULT_INVALID_PARAM;
    }
  }

  if (result == FPC_RESULT_OK) {
    ESP_LOGI(TAG, "CMD_STATUS.event = %s (%04X)", get_event_str_(status->event), status->event);
    ESP_LOGI(TAG, "CMD_STATUS.state = %04X", status->state);
    ESP_LOGI(TAG, "CMD_STATUS.error = %d", status->app_fail_code);
    if (this->status_sensor_ != nullptr) {
      this->status_sensor_->publish_state(((uint16_t) status->state));
    }
    // additional handling of status error or status event
  }
  // modify if callbacks are needed for these events
  /*
    if ((status->app_fail_code != 0) && cmd_callbacks.on_error) {
      cmd_callbacks.on_error(status->app_fail_code);
    } else if (cmd_callbacks.on_status) {
      cmd_callbacks.on_status(status->event, status->state);
    }
  */
  return result;
}

/*
------------------------
HAL FUNCTIONS DEFINITONS
------------------------
*/
fpc::fpc_result_t FingerprintFPC2532Component::fpc_hal_init(void) {
  pinMode(RST_PIN_, OUTPUT);  // RST_N pin
  digitalWrite(RST_PIN_, HIGH);
  return FPC_RESULT_OK;
}
void FingerprintFPC2532Component::hal_reset_device() {
  digitalWrite(RST_PIN_, LOW);
  delay(10);
  digitalWrite(RST_PIN_, HIGH);
  ESP_LOGI(TAG, "System Reset via RST_N pin");
}
fpc::fpc_result_t FingerprintFPC2532Component::fpc_hal_tx(uint8_t *data, std::size_t len) {
  if (!data || len == 0) {
    return FPC_RESULT_FAILURE;
  }
  // while (this->available()){
  //  result = this->fpc_host_sample_handle_rx_data();
  // if (result != FPC_RESULT_OK) {
  //  ESP_LOGCONFIG(TAG, " Failed to handle RX data, error %d", result);
  //  break;
  // }
  this->write_array(data, len);
  delay(1);
  return FPC_RESULT_OK;  // doesn't guarantee array was actually sent: no timeout handling here
}
fpc::fpc_result_t FingerprintFPC2532Component::fpc_hal_rx(uint8_t *data, std::size_t len) {
  return this->read_array(data, len) ? FPC_RESULT_OK : FPC_RESULT_FAILURE;
}
void FingerprintFPC2532Component::fpc_hal_delay_ms(uint32_t ms) { delay(ms); }
void FingerprintFPC2532Component::dump_config() {}

}  // namespace fingerprint_FPC2532
}  // namespace esphome
