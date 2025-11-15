#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/uart/uart.h"
#include "esphome/components/light/light_state.h"
#include "esphome/components/light/automation.h"
#include "esphome/components/monochromatic/monochromatic_light_output.h"

#include <cstddef>
#include <limits>
#include <vector>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {
// using fpc::fpc_result_t; /* to avoid errors due to namespaces */
const uint8_t MAX_NUMBER_OF_TEMPLATES = 30;
static const uint32_t DEFAULT_ENROLL_TIMEOUT_MS = 5000;
typedef enum {
  APP_STATE_WAIT_READY = 0,
  APP_STATE_WAIT_VERSION,
  APP_STATE_WAIT_LIST_TEMPLATES,
  APP_STATE_WAIT_ENROLL,
  APP_STATE_WAIT_IDENTIFY,
  APP_STATE_WAIT_ABORT,
  APP_STATE_WAIT_DELETE_TEMPLATES
} app_state_t;

class FingerprintFPC2532Component : public PollingComponent, public uart::UARTDevice {
 public:
  //--- State Machine Functions/declarations ---
  app_state_t app_state;
  fpc::fpc_id_type_t id_type_enroll_request{0, 0};
  fpc::fpc_id_type_t id_type_delete_request{0, 0};
  bool enroll_request = false;
  bool delete_request = false;

  void update() override;
  void setup() override;
  void dump_config() override;
  void set_sensing_pin(GPIOPin *sensing_pin) { this->sensing_pin_ = sensing_pin; }
  void set_sensor_power_pin(GPIOPin *sensor_power_pin) { this->sensor_power_pin_ = sensor_power_pin; }
  void set_enroll_timeout_ms(uint32_t period_ms) { this->enroll_timeout_ms_ = period_ms; }
  void set_status_sensor(sensor::Sensor *status_sensor) { this->status_sensor_ = status_sensor; }
  void set_text_status_sensor(text_sensor::TextSensor *text_status_sensor) {
    this->text_status_sensor_ = text_status_sensor;
  }
  void set_fingerprint_count_sensor(sensor::Sensor *fingerprint_count_sensor) {
    this->fingerprint_count_sensor_ = fingerprint_count_sensor;
  }
  void set_enrollment_feedback_sensor(sensor::Sensor *enrollment_feedback) {
    this->enrollment_feedback_ = enrollment_feedback;
  }
  void set_num_scans_sensor(sensor::Sensor *num_scans) { this->num_scans_ = num_scans; }
  void set_last_finger_id_sensor(sensor::Sensor *last_finger_id_sensor) {
    this->last_finger_id_sensor_ = last_finger_id_sensor;
  }
  void set_enrolling_binary_sensor(binary_sensor::BinarySensor *enrolling_binary_sensor) {
    this->enrolling_binary_sensor_ = enrolling_binary_sensor;
  }

  void set_status_at_boot_sensor(binary_sensor::BinarySensor *status_at_boot_sensor) {
    this->status_at_boot_sensor_ = status_at_boot_sensor;
  }

  void set_stop_mode_uart_sensor(binary_sensor::BinarySensor *stop_mode_uart_sensor) {
    this->stop_mode_uart_sensor_ = stop_mode_uart_sensor;
  }

  void set_uart_irq_before_tx_sensor(binary_sensor::BinarySensor *uart_irq_before_tx_sensor) {
    this->uart_irq_before_tx_sensor_ = uart_irq_before_tx_sensor;
  }

  void set_scan_interval_ms_sensor(sensor::Sensor *scan_interval_ms_sensor) {
    this->scan_interval_ms_sensor_ = scan_interval_ms_sensor;
  }

  void set_uart_dly_before_tx_ms_sensor(sensor::Sensor *uart_dly_before_tx_ms_sensor) {
    this->uart_dly_before_tx_ms_sensor_ = uart_dly_before_tx_ms_sensor;
  }

  void set_idle_time_before_sleep_ms_sensor(sensor::Sensor *idle_time_before_sleep_ms_sensor) {
    this->idle_time_before_sleep_ms_sensor_ = idle_time_before_sleep_ms_sensor;
  }

  void set_lockout_after_nr_of_fails_sensor(sensor::Sensor *lockout_after_nr_of_fails_sensor) {
    this->lockout_after_nr_of_fails_sensor_ = lockout_after_nr_of_fails_sensor;
  }

  void set_lockout_time_s_sensor(sensor::Sensor *lockout_time_s_sensor) {
    this->lockout_time_s_sensor_ = lockout_time_s_sensor;
  }

  void set_baud_rate_sensor(sensor::Sensor *baud_rate_sensor) { this->baud_rate_sensor_ = baud_rate_sensor; }

  bool delay_elapsed(uint32_t duration_ms);
  // request public functions
  fpc::fpc_result_t fpc_cmd_abort(void);
  // fpc::fpc_result_t fpc_cmd_enroll_request(fpc::fpc_id_type_t *id);
  //  Callbacks
  typedef struct {
    void (*on_error)(uint16_t error);
    void (*on_status)(uint16_t event, uint16_t state);
    void (*on_version)(char *version);
    void (*on_enroll)(uint8_t feedback, uint8_t samples_remaining);
    void (*on_identify)(int is_match, uint16_t id);
    void (*on_list_templates)(int num_templates, uint16_t *template_ids);
    void (*on_navigation)(int gesture);
    void (*on_gpio_control)(uint8_t state);
    void (*on_system_config_get)(fpc::fpc_system_config_t *cfg);
    void (*on_bist_done)(uint16_t test_verdict);
  } fpc_cmd_callbacks_t;

  void on_list_templates(int num_templates, uint16_t *template_ids);
  void on_identify(int is_match, uint16_t id);
  void on_enroll(uint8_t feedback, uint8_t samples_remaining);
  void on_version(char *version);
  void on_status(uint16_t event, uint16_t state);
  void on_error(uint16_t error);

  void add_on_finger_scan_matched_callback(std::function<void(uint16_t, uint16_t)> callback) {
    this->finger_scan_matched_callback_.add(std::move(callback));
  }
  void add_on_finger_scan_unmatched_callback(std::function<void()> callback) {
    this->finger_scan_unmatched_callback_.add(std::move(callback));
  }
  void add_on_finger_scan_start_callback(std::function<void()> callback) {
    this->finger_scan_start_callback_.add(std::move(callback));
  }
  /*
  //void add_on_finger_scan_misplaced_callback(std::function<void()> callback) {
    this->finger_scan_misplaced_callback_.add(std::move(callback));
  }
  */
  void add_on_finger_scan_invalid_callback(std::function<void(uint16_t)> callback) {
    this->finger_scan_invalid_callback_.add(std::move(callback));
  }
  void add_on_enrollment_scan_callback(std::function<void(uint16_t)> callback) {
    this->enrollment_scan_callback_.add(std::move(callback));
  }
  void add_on_enrollment_done_callback(std::function<void(uint16_t)> callback) {
    this->enrollment_done_callback_.add(std::move(callback));
  }
  void add_on_enrollment_failed_callback(std::function<void(uint16_t)> callback) {
    this->enrollment_failed_callback_.add(std::move(callback));
  }

 protected:
  uint32_t start_{0};         // per debug
  uint32_t delay_until_ = 0;  // for non-blocking delays
  uint16_t enroll_id;
  uint32_t enroll_idle_time_{0};
  uint32_t enroll_timeout_ms_ = UINT32_MAX;
  const uint8_t RST_PIN_ =
      26;  // RST_N pin -evaluate if add it on init_py to set via yaml like sensing_pin and sensor_power_pin
  GPIOPin *sensing_pin_{nullptr};
  GPIOPin *sensor_power_pin_{nullptr};
  sensor::Sensor *status_sensor_{nullptr};
  text_sensor::TextSensor *text_status_sensor_{nullptr};
  text_sensor::TextSensor *unique_id_sensor_{nullptr};
  text_sensor::TextSensor *version_sensor_{nullptr};
  sensor::Sensor *fingerprint_count_sensor_{nullptr};
  sensor::Sensor *enrollment_feedback_{nullptr};
  sensor::Sensor *num_scans_{nullptr};

  sensor::Sensor *scan_interval_ms_sensor_{nullptr};
  sensor::Sensor *uart_dly_before_tx_ms_sensor_{nullptr};
  sensor::Sensor *idle_time_before_sleep_ms_sensor_{nullptr};
  sensor::Sensor *lockout_after_nr_of_fails_sensor_{nullptr};
  sensor::Sensor *lockout_time_s_sensor_{nullptr};
  sensor::Sensor *baud_rate_sensor_{nullptr};

  binary_sensor::BinarySensor *status_at_boot_sensor_{nullptr};
  binary_sensor::BinarySensor *stop_mode_uart_sensor_{nullptr};
  binary_sensor::BinarySensor *uart_irq_before_tx_sensor_{nullptr};

  // sensor::Sensor *capacity_sensor_{nullptr};
  // sensor::Sensor *security_level_sensor_{nullptr};
  sensor::Sensor *last_finger_id_sensor_{nullptr};
  // sensor::Sensor *last_confidence_sensor_{nullptr};
  binary_sensor::BinarySensor *enrolling_binary_sensor_{nullptr};

  CallbackManager<void(uint16_t, uint16_t)> finger_scan_matched_callback_;
  CallbackManager<void()> finger_scan_unmatched_callback_;
  CallbackManager<void(uint16_t)> finger_scan_invalid_callback_;
  CallbackManager<void()> finger_scan_start_callback_;
  // CallbackManager<void()> finger_scan_misplaced_callback_;
  CallbackManager<void(uint16_t)> enrollment_scan_callback_;
  CallbackManager<void(uint16_t)> enrollment_done_callback_;
  CallbackManager<void(uint16_t)> enrollment_failed_callback_;

  //--- State Machine Functions/declarations ---
  bool device_ready_;
  bool version_read_;
  bool list_templates_done_;
  bool enroll_status_received_ = false;
  uint16_t device_state_;
  uint8_t n_templates_on_device_;
  void process_state();

  //--- HOST functions ---

  // send
  fpc::fpc_result_t fpc_send_request(fpc::fpc_cmd_hdr_t *cmd, size_t size);
  fpc::fpc_result_t fpc_cmd_status_request(void);
  fpc::fpc_result_t fpc_cmd_version_request(void);
  fpc::fpc_result_t fpc_cmd_enroll_request(fpc::fpc_id_type_t *id);
  fpc::fpc_result_t fpc_cmd_identify_request(fpc::fpc_id_type_t *id, uint16_t tag);

  fpc::fpc_result_t fpc_cmd_list_templates_request(void);
  fpc::fpc_result_t fpc_cmd_delete_template_request(fpc::fpc_id_type_t *id);
  fpc::fpc_result_t fpc_cmd_reset_request(void);
  fpc::fpc_result_t fpc_cmd_system_config_set_request(fpc::fpc_system_config_t *cfg);
  fpc::fpc_result_t fpc_cmd_system_config_get_request(uint8_t type);
  // receive
  fpc::fpc_result_t fpc_host_sample_handle_rx_data(void);
  fpc::fpc_result_t parse_cmd(uint8_t *frame_payload, std::size_t size);
  fpc::fpc_result_t parse_cmd_status(fpc::fpc_cmd_hdr_t *cmd_hdr, std::size_t size);

  fpc::fpc_result_t parse_cmd_version(fpc::fpc_cmd_hdr_t *cmd_hdr, size_t size);
  fpc::fpc_result_t parse_cmd_enroll_status(fpc::fpc_cmd_hdr_t *cmd_hdr, size_t size);
  fpc::fpc_result_t parse_cmd_identify(fpc::fpc_cmd_hdr_t *cmd_hdr, size_t size);
  fpc::fpc_result_t parse_cmd_list_templates(fpc::fpc_cmd_hdr_t *cmd_hdr, size_t size);
  fpc::fpc_result_t parse_cmd_get_system_config(fpc::fpc_cmd_hdr_t *cmd_hdr, size_t size);

  //--- HAL functions ---
  fpc::fpc_result_t fpc_hal_init(void);
  void hal_reset_device();
  fpc::fpc_result_t fpc_hal_tx(uint8_t *data, std::size_t len);
  fpc::fpc_result_t fpc_hal_rx(uint8_t *data, std::size_t len);
  void fpc_hal_delay_ms(uint32_t ms);
};

class FingerScanMatchedTrigger : public Trigger<uint16_t, uint16_t> {
 public:
  explicit FingerScanMatchedTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_finger_scan_matched_callback(
        [this](uint16_t finger_id, uint16_t tag) { this->trigger(finger_id, tag); });
  }
};

class FingerScanUnmatchedTrigger : public Trigger<> {
 public:
  explicit FingerScanUnmatchedTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_finger_scan_unmatched_callback([this]() { this->trigger(); });
  }
};

class FingerScanStartTrigger : public Trigger<> {
 public:
  explicit FingerScanStartTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_finger_scan_start_callback([this]() { this->trigger(); });
  }
};
/*
class FingerScanMisplacedTrigger : public Trigger<> {
 public:
  explicit FingerScanMisplacedTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_finger_scan_misplaced_callback([this]() { this->trigger(); });
  }
};
*/
class FingerScanInvalidTrigger : public Trigger<uint16_t> {
 public:
  explicit FingerScanInvalidTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_finger_scan_invalid_callback([this](uint16_t capture_error) { this->trigger(capture_error); });
  }
};

class EnrollmentScanTrigger : public Trigger<uint16_t> {
 public:
  explicit EnrollmentScanTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_enrollment_scan_callback([this](uint16_t finger_id) { this->trigger(finger_id); });
  }
};

class EnrollmentDoneTrigger : public Trigger<uint16_t> {
 public:
  explicit EnrollmentDoneTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_enrollment_done_callback([this](uint16_t enroll_id) { this->trigger(enroll_id); });
  }
};

class EnrollmentFailedTrigger : public Trigger<uint16_t> {
 public:
  explicit EnrollmentFailedTrigger(FingerprintFPC2532Component *parent) {
    parent->add_on_enrollment_failed_callback([this](uint16_t finger_id) { this->trigger(finger_id); });
  }
};

template<typename... Ts> class EnrollmentAction : public Action<Ts...>, public Parented<FingerprintFPC2532Component> {
 public:
  TEMPLATABLE_VALUE(uint16_t, finger_id)

  void play(Ts... x) override {
    auto finger_id = this->finger_id_.value(x...);
    this->parent_->enroll_request = true;
    if (finger_id) {
      this->parent_->id_type_enroll_request.type = ID_TYPE_SPECIFIED;
      this->parent_->id_type_enroll_request.id = finger_id;
    } else {
      this->parent_->id_type_enroll_request.type = ID_TYPE_GENERATE_NEW;
      this->parent_->id_type_enroll_request.id = 0;
    }
    this->parent_->fpc_cmd_abort();
    this->parent_->app_state = APP_STATE_WAIT_ABORT;
  }
};

template<typename... Ts> class DeleteAction : public Action<Ts...>, public Parented<FingerprintFPC2532Component> {
 public:
  TEMPLATABLE_VALUE(uint16_t, finger_id)

  void play(Ts... x) override {
    auto finger_id = this->finger_id_.value(x...);
    this->parent_->delete_request = true;
    this->parent_->id_type_delete_request.type = ID_TYPE_SPECIFIED;
    this->parent_->id_type_delete_request.id = finger_id;
    this->parent_->fpc_cmd_abort();
    this->parent_->app_state = APP_STATE_WAIT_ABORT;
  }
};

template<typename... Ts> class DeleteAllAction : public Action<Ts...>, public Parented<FingerprintFPC2532Component> {
 public:
  void play(Ts... x) override {
    this->parent_->delete_request = true;
    this->parent_->id_type_delete_request.type = ID_TYPE_ALL;
    this->parent_->id_type_delete_request.id = 0;
    this->parent_->fpc_cmd_abort();
    this->parent_->app_state = APP_STATE_WAIT_ABORT;
  }
};

template<typename... Ts>
class CancelEnrollmentAction : public Action<Ts...>, public Parented<FingerprintFPC2532Component> {
 public:
  void play(Ts... x) override {
    this->parent_->fpc_cmd_abort();
    this->parent_->app_state = APP_STATE_WAIT_ABORT;
  }
};
}  // namespace fingerprint_FPC2532
}  // namespace esphome
