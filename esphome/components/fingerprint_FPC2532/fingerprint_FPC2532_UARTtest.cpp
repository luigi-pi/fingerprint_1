#include "fingerprint_FPC2532.h"
#include "esphome/core/log.h"
#include <cinttypes>
#include <vector>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {

static const char *const TAG = "fingerprint_FPC2532";

void FingerprintFPC2532Component::update() {}

void FingerprintFPC2532Component::setup() { this->fpc_hal_init(); }

/*
------------------------
HOST FUNCTIONS DEFINITONS
------------------------
*/
/** Optional command callback functions. */
FingerprintFPC2532Component::fpc_cmd_callbacks_t cmd_callbacks;
/*Helper functions*/

char *get_id_type_str_(uint16_t id_type) {
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

char *get_event_str_(uint16_t evt) {
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

char *get_enroll_feedback_str_(uint8_t feedback) {
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

char *get_gesture_str_(uint8_t gesture) {
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
/* Command Responses / Events */
fpc::fpc_result_t FingerprintFPC2532Component::fpc_host_sample_handle_rx_data(void) {
  fpc::fpc_result_t result;
  fpc::fpc_frame_hdr_t frame_hdr;
  std::vector<uint8_t> frame_payload;

  /* Step 1: Read Frame Header */
  result = this->fpc_hal_rx((uint8_t *) &frame_hdr, sizeof(fpc::fpc_frame_hdr_t));

  if (result == FPC_RESULT_OK) {
    /* Sanity Check */
    if (frame_hdr.version != FPC_FRAME_PROTOCOL_VERSION || ((frame_hdr.flags & FPC_FRAME_FLAG_SENDER_FW_APP) == 0) ||
        (frame_hdr.type != FPC_FRAME_TYPE_CMD_RESPONSE && frame_hdr.type != FPC_FRAME_TYPE_CMD_EVENT)) {
      ESP_LOGE(TAG, "Sanity check of rx data failed");
      result = FPC_RESULT_IO_BAD_DATA;
    }
  }

  if (result == FPC_RESULT_OK) {
    try {
      frame_payload.resize(frame_hdr.payload_size);
    } catch (const std::bad_alloc &) {
      ESP_LOGE(TAG, "Failed to allocate memory for frame payload");
      result = FPC_RESULT_OUT_OF_MEMORY;
    }
  }

  if (result == FPC_RESULT_OK) {
    /* Step 2: Read Frame Payload (Command) */
    result = this->fpc_hal_rx(frame_payload.data(), frame_hdr.payload_size);
  }

  if (result == FPC_RESULT_OK) {
    result = parse_cmd(frame_payload, frame_hdr.payload_size);
  }

  if (result != FPC_RESULT_OK) {
    ESP_LOGE(TAG, "Failed to handle RX data, error %d", result);
  }

  return result;
}

static fpc::fpc_result_t parse_cmd(std::vector<uint8_t> &frame_payload, std::size_t size) {
  fpc::fpc_result_t result = FPC_RESULT_OK;
  fpc::fpc_cmd_hdr_t *cmd_hdr;

  cmd_hdr = (fpc::fpc_cmd_hdr_t *) frame_payload.data();

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

static fpc::fpc_result_t parse_cmd_status(fpc::fpc_cmd_hdr_t *cmd_hdr, std::size_t size) {
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
    ESP_LOGE(TAG, "CMD_STATUS.event = %s (%04X)", get_event_str_(status->event), status->event);
    ESP_LOGE(TAG, "CMD_STATUS.state = %04X", status->state);
    ESP_LOGE(TAG, "CMD_STATUS.error = %d", status->app_fail_code);
  }

  if ((status->app_fail_code != 0) && cmd_callbacks.on_error) {
    cmd_callbacks.on_error(status->app_fail_code);
  } else if (cmd_callbacks.on_status) {
    cmd_callbacks.on_status(status->event, status->state);
  }

  return result;
}

/*
------------------------
HAL FUNCTIONS DEFINITONS
------------------------
*/
fpc::fpc_result_t FingerprintFPC2532Component::fpc_hal_init(void) { return FPC_RESULT_OK; }
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
  return FPC_RESULT_OK;  // doesn't guarantee array was actually sent: no timeout handling here
}
fpc::fpc_result_t FingerprintFPC2532Component::fpc_hal_rx(uint8_t *data, std::size_t len) {
  return this->read_array(data, len) ? FPC_RESULT_OK : FPC_RESULT_FAILURE;
}
void FingerprintFPC2532Component::fpc_hal_delay_ms(uint32_t ms) { delay(ms); }
void FingerprintFPC2532Component::dump_config() {}

}  // namespace fingerprint_FPC2532
}  // namespace esphome
