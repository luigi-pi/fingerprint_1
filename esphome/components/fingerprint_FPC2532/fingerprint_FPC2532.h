#pragma once

#include "esphome/core/component.h"
#include "esphome/core/automation.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/binary_sensor/binary_sensor.h"
#include "esphome/components/uart/uart.h"

#include <cstddef>
#include <limits>
#include <vector>
#include "fpc_api.h"

namespace esphome {
namespace fingerprint_FPC2532 {
// using fpc::fpc_result_t; /* to avoid errors due to namespaces */
class FingerprintFPC2532Component : public PollingComponent, public uart::UARTDevice {
 public:
  void update() override;
  void setup() override;
  void dump_config() override;

  void set_sensing_pin(GPIOPin *sensing_pin) { this->sensing_pin_ = sensing_pin; }
  void set_sensor_power_pin(GPIOPin *sensor_power_pin) { this->sensor_power_pin_ = sensor_power_pin; }
  void set_status_sensor(sensor::Sensor *status_sensor) { this->status_sensor_ = status_sensor; }

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

 protected:
  uint32_t start_{0};  // per debug
  bool get_parameters_();
  void sensor_wakeup_();
  void sensor_sleep_();

  GPIOPin *sensing_pin_{nullptr};
  GPIOPin *sensor_power_pin_{nullptr};
  uint32_t last_transfer_ms_ = 0;
  sensor::Sensor *status_sensor_{nullptr};
  //--- HOST functions ---
  /**
   * @brief Callback functions for command responses (optional).
   */
  // send
  fpc::fpc_result_t fpc_send_request(fpc::fpc_cmd_hdr_t *cmd, size_t size);
  fpc::fpc_result_t fpc_cmd_status_request(void);

  // receive
  fpc::fpc_result_t fpc_host_sample_handle_rx_data(void);
  fpc::fpc_result_t parse_cmd(uint8_t *frame_payload, std::size_t size);
  fpc::fpc_result_t parse_cmd_status(fpc::fpc_cmd_hdr_t *cmd_hdr, std::size_t size);

  //--- HAL functions ---
  fpc::fpc_result_t fpc_hal_init(void);
  fpc::fpc_result_t fpc_hal_tx(uint8_t *data, std::size_t len);
  fpc::fpc_result_t fpc_hal_rx(uint8_t *data, std::size_t len);
  void fpc_hal_delay_ms(uint32_t ms);
};

}  // namespace fingerprint_FPC2532
}  // namespace esphome
